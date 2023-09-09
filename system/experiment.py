"""
Session and experiment management
Author: Tal Eisenberg, 2021

Responsible for creating/continuing/deleting sessions and loading, running, and managing the
lifecycle of experiment modules.
"""
from datetime import datetime
import inspect
import re
import json
import shutil
import pandas as pd
from pathlib import Path
import threading
import asyncio
import signal
import platform

from configure import get_config
from json_convert import json_convert
from dynamic_loading import load_modules, find_subclass, reload_module
import event_log
from rl_logging import get_main_logger
import schedule
import managed_state


class ExperimentException(Exception):
    pass


log = None

# Latest list of experiment modules
experiment_specs = None

# Reference to the session Experiment class or None if there is no current session.
cur_experiment = None

# Reference to the session event_log.EventDataLogger or None if there is no session.
event_logger = None

# State cursors
state: managed_state.Cursor = None
session_state: managed_state.Cursor = None
params: managed_state.Cursor = None
blocks: managed_state.Cursor = None
actions: managed_state.Cursor = None

event_loop_thread: threading.Thread = None
event_loop: asyncio.AbstractEventLoop = None

_on_loop_shutdown = None


def _run_coroutine(cor):
    asyncio.run_coroutine_threadsafe(cor, event_loop)


def init(state_obj, on_loop_shutdown=None):
    """
    Initialize module.

    Args:
    - state_obj: A managed_state.Cursor pointing to the state store root
    - on_loop_shutdown: A function that will be called once the asyncio eventloop stops
    """
    global event_loop_thread, event_loop, run_future, log, session_state, params, blocks, actions, state, _on_loop_shutdown

    state = state_obj
    session_state = state.get_cursor("session")
    params = session_state.get_cursor("params")
    blocks = session_state.get_cursor("blocks")
    actions = session_state.get_cursor("actions")

    log = get_main_logger()
    _on_loop_shutdown = on_loop_shutdown
    load_experiment_specs()

    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)

    if platform.system() != "Windows":
        event_loop.add_signal_handler(signal.SIGINT, shutdown)

    def run_thread(event_loop: asyncio.AbstractEventLoop):
        asyncio.set_event_loop(event_loop)
        try:
            event_loop.run_forever()
        except Exception:
            log.exception("Exception while running event loop:")

    event_loop_thread = threading.Thread(target=run_thread, args=(event_loop,))
    event_loop_thread.start()


def shutdown():
    """
    Shutdown module. Stop experiment and close session if necessary. Stop the event loop and
    then call on_loop_shutdown callback to continue terminating the whole system.

    NOTE: This is called when the event loop receives a SIGINT signal (i.e. Ctrl-C). It
    """

    async def async_shutdown():
        if session_state.exists(()):
            if session_state["is_running"]:
                await _async_stop_experiment()

            await _async_close_session(cur_experiment)

        if _on_loop_shutdown is not None:
            _on_loop_shutdown()

        event_loop.stop()

    asyncio.run_coroutine_threadsafe(async_shutdown(), loop=event_loop)


def _update_state_file():
    with open(Path(session_state["data_dir"]) / "session_state.json", "w") as f:
        json.dump(session_state.get_self(), f, default=json_convert)


def _split_name_datetime(s):
    """
    Split a string with format {name}_%Y%m%d_%H%M%S into name and a datetime64 objects.

    Return name (string), dt (np.datetime64)
    """
    match = re.search("(.*)_([0-9]*)[-_]([0-9]*)", s)
    dt = pd.to_datetime(match.group(2) + " " + match.group(3), format="%Y%m%d %H%M%S")
    name = match.group(1)
    return name, dt


def get_session_list():
    """
    Return a list of sessions stored under the `config.session_data_root` path.
    Each list element is a tuple of (id, dt, fn) where id is the session id,
    dt is a np.datetime64 object of the session creation datetime encoded in
    the directory name, and fn is the full session directory name.
    """
    paths = list(
        filter(
            lambda p: (p / "session_state.json").exists(),
            get_config().session_data_root.glob("*"),
        )
    )
    nds = [_split_name_datetime(p.stem) for p in paths]
    sl = [(nd[0], nd[1], p.name) for nd, p in zip(nds, paths)]
    sl.sort(key=lambda s: s[1])
    return sl


def create_session(session_id, experiment):
    """
    Create and activate a new session.

    session_id: String used as the base of the session directory name.
    experiment: An experiment module name string.

    Creates a session directory, loads the experiment, updates session state,
    and calls init_session().

    """
    if session_state.exists(()):
        raise ExperimentException(
            "Can't start new session while a session is open."
        )

    log.info("")
    log.info(f"Starting session {session_id}")
    log.info("=================================================")

    if experiment not in experiment_specs.keys():
        raise ExperimentException(f"Unknown experiment: {experiment}.")

    if (
        len(session_id.strip()) == 0
        or len(re.findall(r"[^A-Za-z0-9_]", session_id)) != 0
    ):
        raise ExperimentException(f"Invalid session id: '{session_id}'")

    start_time = datetime.now()
    session_dir = session_id + "_" + start_time.strftime("%Y%m%d_%H%M%S")
    data_path = get_config().session_data_root / session_dir

    try:
        data_path.mkdir()
    except FileExistsError:
        raise ExperimentException("Session data directory already exists!")

    log.info(f"Data directory: {str(data_path)}")

    _load_experiment(experiment)
    _init_event_logger(data_path)

    session_state.set_self(
        {
            "is_running": False,
            "experiment": experiment,
            "data_dir": data_path,
            "id": session_id,
            "start_time": start_time,
            "params": cur_experiment.get_default_params(),
            "blocks": cur_experiment.get_default_blocks(),
            "cur_block": 0,
            "cur_trial": 0,
        }
    )

    _init_session()


async def _async_continue_session(session_name):
    if session_state.exists(()):
        await _async_close_session(cur_experiment)

    log.info("")
    log.info(f"Continuing session {session_name}")
    log.info("=================================================")

    data_path = get_config().session_data_root / session_name
    if not data_path.exists():
        raise ExperimentException(
            f"Session data directory {str(data_path)} doesn't exist!"
        )

    state_path = data_path / "session_state.json"
    if not state_path.exists():
        raise ExperimentException(f"Can't find session state file: {str(state_path)}")

    with open(state_path, "r") as f:
        session = json.load(f)
        session["data_dir"] = data_path
    if session["experiment"] not in experiment_specs.keys():
        raise ExperimentException(f"Unknown experiment: {session['experiment']}.")

    log.info(f"Data directory: {str(data_path)}")

    _load_experiment(session["experiment"])

    if session["is_running"]:
        log.warning(
            "The current session was running when last closed, or it wasn't closed properly. It's state might not be consistent."
        )
        session["is_running"] = False

    _init_event_logger(data_path)
    session_state.set_self(session)

    await _async_init_session(continue_session=True)


def continue_session(session_name):
    """
    Continue a session stored under the directory
    `config.session_data_root / session_name`

    Load the session experiment module, load latest session state from the session_state.json file,
    and call init_session().
    """

    _run_coroutine(_async_continue_session(session_name))


def _init_event_logger(data_dir):
    global event_logger

    event_log_config = get_config().event_log
    csv_path = data_dir / "events.csv" if event_log_config["log_to_csv"] else None

    event_logger = event_log.EventDataLogger(
        config=get_config(),
        csv_path=csv_path,
        db_table_name=event_log_config["table_name"]
        if event_log_config["log_to_db"]
        else None,
    )
    if not event_logger.start(wait=5):
        raise ExperimentException("Event logger can't connect. Timeout elapsed.")

    for src, key in event_log_config["default_events"]:
        event_logger.add_event(src, key)


async def _async_init_session(continue_session):
    await await_maybe(cur_experiment.setup)
    refresh_actions()

    event_logger.log(
        f"session/{'continue' if continue_session else 'create'}",
        session_state.get_self(),
    )
    _update_state_file()


def _init_session(continue_session=False):
    """
    Initialize the session. Calls the experiment class setup() hook,
    and creates session_state.json file.

    Args:
    - continue_session: Whether the loaded session is a continued session that was created previously.
    """
    _run_coroutine(_async_init_session(continue_session))


def refresh_actions():
    """
    Refresh the list of available actions according to the current
    value of the actions dict of the session experiment object.
    """
    actions.set_self(cur_experiment.actions.keys())


async def _async_close_session(cur_experiment):
    if not session_state.exists(()):
        raise ExperimentException("There is no current session.")

    if session_state["is_running"] is True:
        raise ExperimentException("Can't close session while experiment is running.")

    log.info(f"Closing session {session_state['id']}...")

    _update_state_file()

    if cur_experiment is not None:
        try:
            await await_maybe(cur_experiment.release)
        except Exception:
            log.exception("While releasing experiment:")

        try:
            schedule.cancel_all(pool="experiment", wait=False)
        except ValueError:
            pass
        except Exception:
            log.exception("While cancelling experiment schedules:")

    cur_experiment = None

    if event_logger is not None:
        event_logger.log("session/close", session_state.get_self())
        event_logger.stop()

    if state.exists("video") and state.exists(("video", "record")):
        state["video", "record", "filename_prefix"] = ""

    session_state.delete(())
    log.info("Closed session.")


def close_session():
    """
    Close the current session. Updates the session state file,
    calls the experiment class release() hook, shutdowns the event logger,
    removes session state from the global state.
    """
    global cur_experiment

    _run_coroutine(_async_close_session(cur_experiment))


def archive_sessions(sessions, archives, move=False):
    """
    Copy or move a list of sessions into archive directories.

    Args:
    - sessions: A list of session dicts as returned from get_session_list().
    - archives: A list of strings of archive names - keys of config.archive_dirs.
    - move: Whether to move or copy the sessions. Moving sessions is not currently supported.
    """
    sessions_fmt = ", ".join(map(lambda s: s[2], sessions))
    archives_fmt = ", ".join(archives)

    log.info(
        f"{'Moving' if move else 'Copying'} sessions: {sessions_fmt} to archives: {archives_fmt}"
    )

    def copy_fn(src, dst):
        log.info(f"- copying {src} to {dst}")
        shutil.copy2(src, dst)

    def archive_fn():
        for session in sessions:
            src = get_config().session_data_root / session[2]
            for archive in archives:
                if archive not in get_config().archive_dirs:
                    log.error(f"Unknown archive: {archive}")
                    continue

                archive_dir = get_config().archive_dirs[archive]
                if not archive_dir.exists():
                    log.error(f"Archive directory: {archive_dir} does not exist!")
                    continue

                dst = archive_dir / session[2]
                if dst.exists():
                    log.error(f"Session already exists in destination, skipping: {dst}")
                    continue

                try:
                    shutil.copytree(src, dst, copy_function=copy_fn)
                    log.info(f"Done copying {src} to {dst}")
                except Exception:
                    log.exception("Exception while copying file:")

    threading.Thread(target=archive_fn).start()


async def _async_delete_sessions(sessions):
    """
    Delete all files and directories of a list of sessions

    Args:
    - sessions: A list of session dicts as returned from get_session_list()
    """
    if session_state.exists(()) and session_state["is_running"] is True:
        raise ExperimentException(
            "Can't delete session while an experiment is running."
        )

    data_dirs = [get_config().session_data_root / s[2] for s in sessions]

    if session_state.exists(()) and session_state["data_dir"] in data_dirs:
        log.warning("Closing and deleting current session.")
        await _async_close_session(cur_experiment)

    for dir in data_dirs:
        shutil.rmtree(dir)
        log.info(f"Deleted session data directory: {dir}")


def delete_sessions(sessions):
    """
    Delete all files and directories of a list of sessions

    Args:
    - sessions: A list of session dicts as returned from get_session_list()
    """
    _run_coroutine(_async_delete_sessions(sessions))


async def await_maybe(callback):
    result = callback()
    if inspect.isawaitable(result):
        return await result
    return result


def run_experiment():
    """
    Run the experiment of the current session. Calls the experiment class run() hook, and starts
    trial 0 of block 0. Updates the session state file and log to the events log.
    """
    global cached_params, cached_params_block

    if session_state["is_running"] is True:
        raise ExperimentException("Experiment is already running.")

    if not session_state.exists(()):
        raise ExperimentException("Can't run experiment. No experiment was set.")

    session_state["is_running"] = True

    log.info(f"Running experiment {session_state['experiment']}.")

    cached_params = None
    cached_params_block = None

    async def run_async():
        try:
            await await_maybe(cur_experiment.run)
            st = session_state.get_self()
            await _set_phase(st["cur_block"], st["cur_trial"], force_run=True)
            _update_state_file()
        except Exception:
            log.exception("Exception while running experiment:")
            session_state["is_running"] = False

        event_logger.log("session/run", session_state.get_self())
        _update_state_file()

    asyncio.run_coroutine_threadsafe(run_async(), event_loop)


async def _async_stop_experiment():
    if session_state["is_running"] is False:
        raise ExperimentException("Session is not running.")

    try:
        await await_maybe(cur_experiment.end_trial)
        await await_maybe(cur_experiment.end_block)
        await await_maybe(cur_experiment.end)
    except Exception:
        log.exception("Exception while ending session:")
    finally:
        try:
            schedule.cancel_all(pool="experiment_phases", wait=False)
        except ValueError:
            pass

        session_state["is_running"] = False

        event_logger.log("session/stop", session_state.get_self())
        await _set_phase(
            session_state.get("cur_block", 0), session_state.get("cur_trial", 0)
        )
        _update_state_file()

    log.info(f"Experiment {session_state['experiment']} has ended.")


def stop_experiment():
    """
    Stop the currently running experiment.
    Calls the experiment class hooks end_trial(), end_block(), end() in this order.
    Update session state file and log to the events log.
    """
    _run_coroutine(_async_stop_experiment())


async def _set_phase(block, trial, force_run=False):
    """
    Set the current block and trial numbers.
    Calls the run_block() and run_trial() experiment class hooks when applicable.

    Args:
    - block, trial: int indices (starting with 0).
    - force_run: When True, the hooks will be called even when the parameters are
                 the same as the current phase.
    """
    if blocks.exists(()):
        if len(blocks.get_self()) <= block and block != 0:
            raise ExperimentException(f"Block {block} is not defined.")
    else:
        raise ExperimentException("Session doesn't have any block definitions.")

    if not session_state["is_running"]:
        session_state.update((), {"cur_block": block, "cur_trial": trial})
        return
    else:
        cur_trial = session_state.get("cur_trial", None)
        cur_block = session_state.get("cur_block", None)

        if cur_trial != trial or cur_block != block:
            await await_maybe(cur_experiment.end_trial)

        if cur_block != block:
            await await_maybe(cur_experiment.end_block)

        num_trials = get_params().get("$num_trials", None)
        if num_trials is not None and trial >= num_trials:
            raise ExperimentException(
                f"Trial {trial} is out of range for block {block}."
            )

        try:
            schedule.cancel_all(pool="experiment_phases", wait=False)
        except ValueError:
            pass

        iti = get_params().get("$inter_trial_interval", None)
        if iti is not None and (cur_block != block or cur_trial != trial):
            await asyncio.sleep(iti)

        session_state.update((), {"cur_block": block, "cur_trial": trial})

        if cur_block != block or force_run:
            await await_maybe(cur_experiment.run_block)

        if cur_trial != trial or cur_block != block or force_run:
            await await_maybe(cur_experiment.run_trial)

        block_duration = get_params().get("$block_duration", None)
        if block_duration is not None:
            schedule.once(next_block, block_duration, pool="experiment_phases")

        trial_duration = get_params().get("$trial_duration", None)
        if trial_duration is not None:
            schedule.once(next_trial, trial_duration, pool="experiment_phases")

        _update_state_file()


def next_trial():
    """
    Move to the next trial. The next block will start if the number of trials
    in the current block have reached the value of the num_trials session parameter.
    """
    cur_trial = session_state["cur_trial"]
    cur_block = session_state["cur_block"]

    num_trials = get_params().get("$num_trials", None)

    if num_trials is not None and cur_trial + 1 >= num_trials:
        next_block()
    else:
        # next trial
        _run_coroutine(_set_phase(cur_block, cur_trial + 1))


def next_block():
    """
    Move to the next block. The experiment will stop if the current block is
    the last one.
    """
    cur_block = session_state["cur_block"]
    if cur_block + 1 < get_num_blocks():
        _run_coroutine(_set_phase(cur_block + 1, 0))
    else:
        if session_state["is_running"]:
            stop_experiment()


def reset_phase():
    """
    Go back to the first trial of the first block. Reset session block and trial to 0
    """
    _run_coroutine(_set_phase(0, 0))


def load_experiment_specs():
    """
    Load all experiment modules found in the `config.experiment_modules_dir`
    Path, and return a list of all experiment module specs.
    """
    global experiment_specs
    experiment_specs = dict(
        filter(
            lambda k_mod_spec: find_subclass(k_mod_spec[1][0], Experiment),
            load_modules(get_config().experiment_modules_dir, log).items(),
        )
    )
    return experiment_specs


def _load_experiment(experiment_name):
    """
    Load an experiment module. Reload the module and instantiate the experiment
    class.
    """
    global cur_experiment
    _, spec = experiment_specs[experiment_name]
    module = reload_module(spec)
    cls = find_subclass(module, Experiment)
    cur_experiment = cls(log)


def _can_update_params():
    if not session_state.exists(()):
        raise ExperimentException("Can't update params before starting a session")

    if session_state["is_running"]:
        raise ExperimentException("Can't update params while an experiment is running.")


def update_params(new_params):
    """
    Update the experiment parameters of the currently loaded session (if there is one).

    - new_params: The new parameters dict or None to use the experiment default parameters.
    """
    if new_params is None:
        return update_params(cur_experiment.get_default_params())

    _can_update_params()
    session_state["params"] = new_params


def update_blocks(new_blocks):
    """
    Update the experiment block parameters of the currently loaded session (if there is one).

    - new_blocks: A list of parameter dicts for each block or None to use the experiment default
                  block parameters.
    """
    if new_blocks is None:
        return update_blocks(cur_experiment.get_default_blocks())

    _can_update_params()
    session_state["blocks"] = new_blocks


def update_block(block_idx, new_block):
    """
    Update the experiment block parameters for a single block.

    Args:
    - block_idx: The index of the updated block (int).
    - new_block: The new parameters dict for this block, or None to use the experiment default block parameters.
    """
    if new_block is None:
        if len(cur_experiment.default_blocks) > block_idx:
            return update_block(block_idx, cur_experiment.default_blocks[block_idx])
        else:
            _can_update_params()
            return remove_block(block_idx)

    _can_update_params()
    num_blocks = len(session_state["blocks"])

    if block_idx < num_blocks:
        session_state["blocks", block_idx] = new_block
    elif block_idx == num_blocks:
        session_state.append("blocks", new_block)
    else:
        raise ExperimentException(
            f"Can't update block. Invalid block index: {block_idx}"
        )


def remove_block(block_idx):
    """
    Remove the block at the supplied index.
    """
    session_state.delete(("blocks", block_idx))


def run_action(label):
    """
    Run the "run" function of an experiment action.

    - label: The action name (key of the current experiment actions dict).
    """
    cur_experiment.actions[label]["run"]()


cached_params = None
cached_params_block = None


def get_params():
    """
    Return the parameters of the current block. These are determined by the
    session parameters overriden by values in the current block parameters.
    """
    global cached_params, cached_params_block

    if (
        blocks.exists(())
        and len(blocks.get_self()) > 0
        and "cur_block" in session_state
    ):
        cur_block = session_state["cur_block"]
        if cached_params is not None and cached_params_block == cur_block:
            return cached_params

        block_params = session_state[("blocks", session_state["cur_block"])]
    else:
        cur_block = None
        if cached_params is not None and cached_params_block is None:
            log.info("cached_params")
            return cached_params

        block_params = session_state["params"]

    params_dict = params.get_self()
    params_dict.update(block_params)
    cached_params = params_dict
    cached_params_block = cur_block

    return params_dict


def get_num_blocks():
    """
    Return the number of blocks defined in the current session.
    """
    if "blocks" in session_state:
        return len(session_state["blocks"])
    else:
        return 1


class Experiment:
    """
    An abstract class representing an experiment. This is the entry point for
    running experiment modules. An experiment module must contain a class
    inheriting from the Experiment class.

    self.log - A logging.Logger for logging.

    Provides various experiment lifecycle methods.
    """

    def __init__(self, logger):
        self.log = logger
        self.actions = {}
        self.default_params = {}
        self.default_blocks = [{}]

    def run(self):
        """Called by run_experiment()"""
        pass

    def run_block(self):
        """Called by set_phase()"""
        pass

    def run_trial(self):
        """Called by set_phase()"""
        pass

    def end(self):
        """Called by stop_experiment()"""
        pass

    def end_block(self):
        """Called by set_phase() and stop_experiment()"""
        pass

    def end_trial(self):
        """Called by set_phase() and stop_experiment()"""
        pass

    def setup(self):
        """Called by init_session() after the session was created or continued."""
        pass

    def release(self):
        """Called by close_session()"""
        pass

    def get_default_params(self):
        """
        Return by default the static class attribute `default_params`.
        If the static attribute is not defined return the instance attribute
        with the same name.

        Can be overriden to define default parameters dynamically.
        """
        try:
            return type(self).default_params
        except AttributeError:
            return self.default_params

    def get_default_blocks(self):
        """
        Return by default the static class attribute `default_blocks`.
        If the static attribute is not defined return the instance attribute
        with the same name.

        Can be overriden to define default block parameters dynamically.
        """
        try:
            return type(self).default_blocks
        except AttributeError:
            return self.default_blocks
