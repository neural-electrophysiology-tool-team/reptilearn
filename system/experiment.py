from datetime import datetime
import re

from state import state
from json_convert import json_convert
from dynamic_loading import load_modules, find_subclass, reload_module
import video_system
import event_log
import schedule

import json
import shutil
import pandas as pd
from pathlib import Path


class ExperimentException(Exception):
    pass


config = None
log = None

experiment_specs = None
cur_experiment = None
event_logger = None

# Cursors
session_state = None
params = None
blocks = None
actions = None


def init(logger, config_module):
    global log, config, session_state, params, blocks, actions

    session_state = state.get_cursor("session")
    params = session_state.get_cursor("params")
    blocks = session_state.get_cursor("blocks")
    actions = session_state.get_cursor("actions")

    config = config_module
    log = logger
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
            config.session_data_root.glob("*"),
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
    data_path = config.session_data_root / session_dir

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
    # add session vars for local stuff
    # if is running delete session vars and change to not running

    if session_state.exists(()):
        close_session()

    log.info("")
    log.info(f"Continuing session {session_name}")
    log.info("=================================================")

    data_path = config.session_data_root / session_name
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
    data_dir = Path(session_state["data_dir"])
    state["video", "record", "write_dir"] = data_dir

    csv_path = data_dir / "events.csv" if config.event_log["log_to_csv"] else None

    global event_logger
    event_logger = event_log.EventDataLogger(
        csv_path=csv_path,
        log_to_db=config.event_log["log_to_db"],
        table_name=config.event_log["table_name"],
    )
    if not event_logger.start(wait=5):
        raise ExperimentException("Event logger can't connect. Timeout elapsed.")

    for src, key in config.event_log["default_events"]:
        event_logger.add_event(src, key)

    cur_experiment.setup()
    actions.set_self(cur_experiment.actions.keys())

    event_logger.log(
        f"session/{'continue' if continue_session else 'create'}",
        session_state.get_self(),
    )
    _update_state_file()


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
            schedule.cancel_all(pool="experiment")
        except ValueError:
            pass
        except Exception:
            log.exception("While cancelling experiment schedules:")

    cur_experiment = None

    if event_logger is not None:
        event_logger.log("session/close", session_state.get_self())
        event_logger.stop()

    video_system.restore_after_experiment_session()
    session_state.delete(())
    log.info("Closed session.")


def delete_session():
    """
    Close the current session and delete its data directory.
    """
    if not session_state.exists(()):
        raise ExperimentException("Can't delete session. No session is open currently.")

    if session_state["is_running"] is True:
        raise ExperimentException("Can't delete session while experiment is running.")

    data_dir = session_state["data_dir"]
    close_session()
    shutil.rmtree(data_dir)
    log.info(f"Deleted session data at {data_dir}")


def run_experiment():
    """
    Run the experiment of the current session. Calls the experiment class run(params) hook, and starts
    trial 0 of block 0. Updates the session state file.
    """
    if session_state["is_running"] is True:
        raise ExperimentException("Experiment is already running.")

    if not session_state.exists(()):
        raise ExperimentException("Can't run experiment. No experiment was set.")

    session_state["is_running"] = True

    log.info(f"Running experiment {session_state['experiment']}.")

    event_logger.log("session/run", session_state.get_self())

    try:
        cur_experiment.run(params.get_self())
        st = session_state.get_self()
        set_phase(st["cur_block"], st["cur_trial"], force_run=True)
        _update_state_file()
    except Exception:
        log.exception("Exception while running experiment:")
        session_state["is_running"] = False

    _update_state_file()


def stop_experiment():
    """
    Stop the currently running experiment.
    """
    if session_state["is_running"] is False:
        raise ExperimentException("Session is not running.")

    try:
        phase_params = get_phase_params()
        cur_experiment.end_trial(phase_params)
        cur_experiment.end_block(phase_params)
        cur_experiment.end(params.get_self())
    except Exception:
        log.exception("Exception while ending session:")
    finally:
        session_state["is_running"] = False

        event_logger.log("session/stop", session_state.get_self())

        set_phase(session_state.get("cur_block", 0), session_state.get("cur_trial", 0))
        _update_state_file()

    log.info(f"Experiment {session_state['experiment']} has ended.")


def set_phase(block, trial, force_run=False):
    """
    Set the current block and trial numbers.
    Calls the run_block(params) and run_trial(params) experiment class hooks.

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

        prev_phase_params = get_phase_params()

        if cur_trial != trial or cur_block != block:
            cur_experiment.end_trial(prev_phase_params)

        if cur_block != block:
            cur_experiment.end_block(prev_phase_params)

        session_state.update((), {"cur_block": block, "cur_trial": trial})

        next_phase_params = get_phase_params()

        num_trials = next_phase_params.get("num_trials", None)
        if num_trials is not None and trial >= num_trials:
            raise ExperimentException(
                f"Trial {trial} is out of range for block {block}."
            )

        if cur_block != block or force_run:
            cur_experiment.run_block(next_phase_params)

        if cur_trial != trial or cur_block != block or force_run:
            cur_experiment.run_trial(next_phase_params)


def next_trial():
    """
    Move to the next trial. The next block will start if the number of trials
    in the current block have reached the value of the num_trials session parameter.
    """
    cur_trial = session_state["cur_trial"]
    cur_block = session_state["cur_block"]

    num_trials = get_phase_params().get("num_trials", None)

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
            load_modules(config.experiment_modules_dir, log).items(),
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


def get_phase_params():
    """
    Return the parameters of the current block. These are determined by the
    session parameters overriden by values in the current block parameters.
    """
    if (
        blocks.exists(())
        and len(blocks.get_self()) > 0
        and "cur_block" in session_state
    ):
        block_params = session_state[("blocks", session_state["cur_block"])]
    else:
        block_params = session_state["params"]

    params_dict = params.get_self()
    params_dict.update(block_params)
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

    Provides various experiment lifecycle methods. Some methods accept a
    params argument. This is a dictionary (not a cursor) of the current
    parameters according to the current block number.
    """

    def __init__(self, logger):
        self.log = logger
        self.actions = {}
        self.default_params = {}
        self.default_blocks = [{}]

    def run(self, params):
        """Called by run_experiment()"""
        pass

    def run_block(self, params):
        """Called by set_phase()"""
        pass

    def run_trial(self, params):
        """Called by set_phase()"""
        pass

    def end(self, params):
        """Called by stop_experiment()"""
        pass

    def end_block(self, params):
        """Called by set_phase() and stop_experiment()"""
        pass

    def end_trial(self, params):
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
