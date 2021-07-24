from datetime import datetime
import re

from state import state
from json_convert import json_convert
from dynamic_loading import load_module, find_subclass, reload_module
import video_record
import event_log
import json
import shutil


class ExperimentException(Exception):
    pass


config = None
log = None
image_observers = None

experiment_specs = None
cur_experiment = None
event_logger = None

# Cursors
session_state = None
params = None
blocks = None
actions = None


def init(img_observers, img_sources, logger, config_module):
    global log, image_observers, image_sources, config, session_state, params, blocks, actions

    session_state = state.get_cursor("session")
    params = session_state.get_cursor("params")
    blocks = session_state.get_cursor("blocks")
    actions = session_state.get_cursor("actions")

    config = config_module
    image_observers = img_observers
    image_sources = img_sources
    log = logger
    load_experiment_specs()


def shutdown():
    if session_state.exists(()):
        if session_state["is_running"]:
            stop_experiment()
        close_session()


def _update_state_file():
    with open(session_state["data_dir"] / "session_state.json", "w") as f:
        json.dump(session_state.get_self(), f, default=json_convert)


def create_session(session):
    global cur_experiment

    if session_state.exists(()) and session_state["is_running"] is True:
        raise ExperimentException(
            "Can't start new session while an experiment is running."
        )

    if session_state.exists(()):
        close_session()

    log.info(f"Starting session {session['id']}")
    log.info("=================================================")

    if session["experiment"] not in experiment_specs.keys():
        raise ExperimentException(f"Unknown experiment: {session['experiment']}.")

    if (
        len(session["id"].strip()) == 0
        or len(re.findall(r"[^A-Za-z0-9_]", session["id"])) != 0
    ):
        raise ExperimentException(f"Invalid experiment id: '{session['id']}'")

    start_time = datetime.now()
    session_dir = session["id"] + "_" + start_time.strftime("%Y%m%d_%H%M%S")
    data_path = config.experiment_data_root / session_dir

    try:
        data_path.mkdir()
    except FileExistsError:
        raise ExperimentException("Experiment data directory already exists!")

    log.info(f"Data directory: {str(data_path)}")

    spec = experiment_specs[session["experiment"]]
    module = reload_module(spec)
    cls = find_subclass(module, Experiment)
    cur_experiment = cls(log)

    session_state.set_self(
        {
            "is_running": False,
            "experiment": session["experiment"],
            "data_dir": data_path,
            "id": session["id"],
            "start_time": start_time,
            "params": cur_experiment.get_default_params(),
            "blocks": cur_experiment.get_default_blocks(),
        }
    )

    state["video_record", "write_dir"] = data_path

    csv_path = data_path / "events.csv" if config.event_log["log_to_csv"] else None

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

    event_logger.log("session/create", session_state.get_self())
    _update_state_file()


def close_session():
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

    cur_experiment = None

    if event_logger is not None:
        event_logger.log("session/close", session_state.get_self())
        event_logger.stop()

    video_record.restore_after_experiment_session()
    session_state.delete(())
    log.info("Closed session.")


def delete_session():
    if not session_state.exists(()):
        raise ExperimentException("There is no started session.")

    if session_state["is_running"] is True:
        raise ExperimentException("Can't delete session while experiment is running.")

    data_dir = session_state["data_dir"]
    close_session()
    shutil.rmtree(data_dir)
    log.info(f"Deleted session data at {data_dir}")


def run_experiment():
    """
    Run the experiment of the current session. Calls the `run` function, and starts
    trial 0 of block 0
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
        set_phase(0, 0)
        _update_state_file()
    except Exception:
        log.exception("Exception while running experiment:")
        session_state["is_running"] = False

    _update_state_file()


def stop_experiment():
    """
    Stop a currently running experiment.
    """
    global event_logger

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

        session_state.delete("cur_trial")
        session_state.delete("cur_block")

        _update_state_file()

    log.info(f"Experiment {session_state['experiment']} has ended.")


def set_phase(block, trial):
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

        if cur_block != block:
            cur_experiment.run_block(next_phase_params)

        if cur_trial != trial or cur_block != block:
            cur_experiment.run_trial(next_phase_params)


def next_trial():
    """
    Move to the next trial. The next block will start if the number of trials in the current block
    have reached the value of the num_trials session parameter.
    """
    if not session_state["is_running"]:
        log.warning(
            "experiment.py: Attempted to run next_trial() while experiment is not running"
        )
        return

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
    Move to the next block. The experiment will stop if the current block is the last one.
    """
    if not session_state["is_running"]:
        log.warning(
            "experiment.py: Attempted to run next_block() while experiment is not running"
        )
        return

    cur_block = session_state["cur_block"]
    if cur_block + 1 < get_num_blocks():
        set_phase(cur_block + 1, 0)
    else:
        stop_experiment()


def load_experiments(experiments_dir=None):
    if experiments_dir is None:
        experiments_dir = config.experiment_modules_dir

    experiment_specs = {}
    experiment_pys = experiments_dir.glob("*.py")

    for py in experiment_pys:
        try:
            module, spec = load_module(py, package="experiments")
            cls = find_subclass(module, Experiment)
            if cls is not None:
                experiment_specs[py.stem] = spec

        except Exception:
            log.exception("While loading experiments:")

    return experiment_specs


def load_experiment_specs():
    global experiment_specs
    experiment_specs = load_experiments()
    return experiment_specs


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
    session parameters overriden by values in the block parameters.
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
    An abstract class representing an experiment. This is the entry point for running
    experiment modules. An experiment module must contain a class inheriting from the 
    Experiment class.

    self.log - A logging.Logger for logging.

    ...
    """
    def __init__(self, logger):
        self.log = logger
        self.actions = {}
        self.default_params = {}
        self.default_blocks = [{}]

    def run(self, params):
        pass

    def run_block(self, params):
        pass

    def run_trial(self, params):
        pass

    def end(self, params):
        pass

    def end_block(self, params):
        pass

    def end_trial(self, params):
        pass

    def setup(self):
        pass

    def release(self):
        pass

    def get_default_params(self):
        try:
            return type(self).default_params
        except AttributeError:
            return self.default_params

    def get_default_blocks(self):
        try:
            return type(self).default_blocks
        except AttributeError:
            return self.default_blocks
