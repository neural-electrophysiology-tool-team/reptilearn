from datetime import datetime
import re
import json
import shutil
import pandas as pd
from pathlib import Path
import threading

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

experiment_specs = None
cur_experiment = None
event_logger = None

# Cursors
state: managed_state.Cursor = None
session_state: managed_state.Cursor = None
params: managed_state.Cursor = None
blocks: managed_state.Cursor = None
actions: managed_state.Cursor = None


def init(state_obj):
    global log, session_state, params, blocks, actions, state

    state = state_obj
    session_state = state.get_cursor("session")
    params = session_state.get_cursor("params")
    blocks = session_state.get_cursor("blocks")
    actions = session_state.get_cursor("actions")

    log = get_main_logger()
    load_experiment_specs()


def shutdown():
    if session_state.exists(()):
        if session_state["is_running"]:
            stop_experiment()
        close_session()


def _update_state_file():
    with open(Path(session_state["data_dir"]) / "session_state.json", "w") as f:
        json.dump(session_state.get_self(), f, default=json_convert)


def split_name_datetime(s):
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
    nds = [split_name_datetime(p.stem) for p in paths]
    sl = [(nd[0], nd[1], p.name) for nd, p in zip(nds, paths)]
    sl.sort(key=lambda s: s[1])
    return sl


def create_session(session_id, experiment):
    """
    Create and activate a new session.

    session_id: String used as the base of the session directory name.
    experiment: An experiment module name

    Creates a session directory, loads the experiment, updates session state,
    and calls init_session().

    """
    if session_state.exists(()) and session_state["is_running"] is True:
        raise ExperimentException(
            "Can't start new session while an experiment is running."
        )

    if session_state.exists(()):
        close_session()

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

    load_experiment(experiment)

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

    init_session()


def continue_session(session_name):
    """
    Continue a session stored under the directory
    `config.session_data_root / session_name`

    Load the session experiment module, load latest session state from the session_state.json file,
    and call init_session().
    """
    if session_state.exists(()):
        close_session()

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

    load_experiment(session["experiment"])

    if session["is_running"]:
        log.warning(
            "The current session was running when last closed, or it wasn't closed properly. It's state might not be consistent."
        )
        session["is_running"] = False

    session_state.set_self(session)

    init_session(continue_session=True)


def init_session(continue_session=False):
    """
    Initialize the session event logger (stored as a global event_logger object),
    calls the experiment class setup() hook, and creates session_state.json file.
    """
    global event_logger

    event_log_config = get_config().event_log
    data_dir = Path(session_state["data_dir"])
    csv_path = data_dir / "events.csv" if event_log_config["log_to_csv"] else None

    event_logger = event_log.EventDataLogger(
        config=get_config(),
        csv_path=csv_path,
        db_table_name=event_log_config["table_name"] if event_log_config["log_to_db"] else None,
    )
    if not event_logger.start(wait=5):
        raise ExperimentException("Event logger can't connect. Timeout elapsed.")

    for src, key in event_log_config["default_events"]:
        event_logger.add_event(src, key)

    cur_experiment.setup()
    refresh_actions()

    event_logger.log(
        f"session/{'continue' if continue_session else 'create'}",
        session_state.get_self(),
    )
    _update_state_file()


def refresh_actions():
    actions.set_self(cur_experiment.actions.keys())


def close_session():
    """
    Close the current session. Updates the session state file,
    calls the experiment class release() hook, shutdowns the event logger,
    removes session state from the global state.
    """
    global cur_experiment

    if not session_state.exists(()):
        raise ExperimentException("There is no started session.")

    if session_state["is_running"] is True:
        raise ExperimentException("Can't close session while experiment is running.")

    _update_state_file()

    if cur_experiment is not None:
        try:
            cur_experiment.release()
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

    if state.exists(("video", "record")):
        state["video", "record", "filename_prefix"] = ""

    session_state.delete(())
    log.info("Closed session.")


def archive_sessions(sessions, archives, move=False):
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


def delete_sessions(sessions):
    if session_state.exists(()) and session_state["is_running"] is True:
        raise ExperimentException(
            "Can't delete session while an experiment is running."
        )

    data_dirs = [get_config().session_data_root / s[2] for s in sessions]

    if session_state.exists(()) and session_state["data_dir"] in data_dirs:
        log.warning("Closing and deleting current session.")
        close_session()

    def delete_fn():
        for dir in data_dirs:
            shutil.rmtree(dir)
            log.info(f"Deleted session data directory: {dir}")

    threading.Thread(target=delete_fn).start()


def run_experiment():
    """
    Run the experiment of the current session. Calls the experiment class run() hook, and starts
    trial 0 of block 0. Updates the session state file.
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

    try:
        cur_experiment.run()
        st = session_state.get_self()
        set_phase(st["cur_block"], st["cur_trial"], force_run=True)
        _update_state_file()
    except Exception:
        log.exception("Exception while running experiment:")
        session_state["is_running"] = False

    event_logger.log("session/run", session_state.get_self())
    _update_state_file()


def stop_experiment():
    """
    Stop the currently running experiment.
    """
    if session_state["is_running"] is False:
        raise ExperimentException("Session is not running.")

    try:
        cur_experiment.end_trial()
        cur_experiment.end_block()
        cur_experiment.end()
    except Exception:
        log.exception("Exception while ending session:")
    finally:
        try:
            schedule.cancel_all(pool="experiment_phases", wait=False)
        except ValueError:
            pass

        session_state["is_running"] = False

        event_logger.log("session/stop", session_state.get_self())
        set_phase(session_state.get("cur_block", 0), session_state.get("cur_trial", 0))
        _update_state_file()

    log.info(f"Experiment {session_state['experiment']} has ended.")


def set_phase(block, trial, force_run=False):
    """
    Set the current block and trial numbers.
    Calls the run_block() and run_trial() experiment class hooks.

    block, trial: int indices (starting with 0).
    force_run: When True, the hooks will be called even when the parameters are
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
            cur_experiment.end_trial()

        if cur_block != block:
            cur_experiment.end_block()

        num_trials = get_params().get("$num_trials", None)
        if num_trials is not None and trial >= num_trials:
            raise ExperimentException(
                f"Trial {trial} is out of range for block {block}."
            )

        def start_trial():
            session_state.update((), {"cur_block": block, "cur_trial": trial})

            if cur_block != block or force_run:
                cur_experiment.run_block()

            if cur_trial != trial or cur_block != block or force_run:
                cur_experiment.run_trial()

            block_duration = get_params().get("$block_duration", None)
            if block_duration is not None:
                schedule.once(next_block, block_duration, pool="experiment_phases")

            trial_duration = get_params().get("$trial_duration", None)
            if trial_duration is not None:
                schedule.once(next_trial, trial_duration, pool="experiment_phases")

        try:
            schedule.cancel_all(pool="experiment_phases", wait=False)
        except ValueError:
            pass

        iti = get_params().get("$inter_trial_interval", None)
        if iti is not None and cur_block != block or cur_trial != trial:
            schedule.once(start_trial, iti)
        else:
            start_trial()


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
        set_phase(cur_block, cur_trial + 1)


def next_block():
    """
    Move to the next block. The experiment will stop if the current block is
    the last one.
    """
    cur_block = session_state["cur_block"]
    if cur_block + 1 < get_num_blocks():
        set_phase(cur_block + 1, 0)
    else:
        if session_state["is_running"]:
            stop_experiment()


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


def load_experiment(experiment_name):
    """
    Load an experiment module. Reload the module and instantiate the experiment
    class.
    """
    global cur_experiment
    _, spec = experiment_specs[experiment_name]
    module = reload_module(spec)
    cls = find_subclass(module, Experiment)
    cur_experiment = cls(log)


def can_update_params():
    if not session_state.exists(()):
        raise ExperimentException("Can't update params before starting a session")

    if session_state["is_running"]:
        raise ExperimentException("Can't update params while an experiment is running.")


def update_params(new_params):
    if new_params is None:
        return update_params(cur_experiment.get_default_params())

    can_update_params()
    session_state["params"] = new_params


def update_blocks(new_blocks):
    if new_blocks is None:
        return update_blocks(cur_experiment.get_default_blocks())

    can_update_params()
    session_state["blocks"] = new_blocks


def update_block(block_idx, new_block):
    if new_block is None:
        if len(cur_experiment.default_blocks) > block_idx:
            return update_block(block_idx, cur_experiment.default_blocks[block_idx])
        else:
            can_update_params()
            return remove_block(block_idx)

    can_update_params()
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
    session_state.delete(("blocks", block_idx))


def run_action(label):
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
