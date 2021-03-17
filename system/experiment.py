import config
import state
import sys
from dynamic_loading import load_module, find_subclass, reload_module


class ExperimentException(Exception):
    pass


state.update("experiment", {})
exp_state = state.Cursor("experiment")
exp_state.update((), {"is_running": False})

cur_experiment = None
state_dispatcher = state.Dispatcher()


# experiment can be running or not. stop either because it ended or because we asked it to.
# should have cur block, trial and num_blocks num_trials
# the experiment should have a params dict that's overriden by block params.
# should have cur params with the right params for block (assoc cur block params into global params and put here)
# make it easy to make the flow time based.
def run(exp_params):
    if is_running() is True:
        raise ExperimentException("Experiment is already running.")

    if cur_experiment is None:
        raise ExperimentException("Can't run experiment. No experiment was set.")

    params.set(exp_params)
    exp_state.assoc(
        (),
        {
            "is_running": True,
            "cur_block": 0,
            "cur_trial": 0,
        },
    )

    try:
        cur_experiment.run()
    except Exception:
        log.critical(
            "Exception while calling running experiment:", exc_info=sys.exc_info()
        )
        end()


def end():
    if is_running() is False:
        raise ExperimentException("Experiment is not running.")

    cur_experiment.end()
    exp_state.update("is_running", False)
    exp_state.remove("params")
    exp_state.remove("cur_trial")
    exp_state.remove("cur_block")


def set_phase(block, trial):
    blocks = exp_state.get_path("blocks")

    if blocks != state.path_not_found:
        if len(blocks) <= block:
            raise ExperimentException(f"Block {block} is not defined.")
    elif block != 0:
        raise ExperimentException("Experiment doesn't have block definitions.")    

    if "num_trials" in blocks[block] and trial >= blocks[block]["num_trials"]:
        raise ExperimentException(f"Trial {trial} is out of range for block {block}.")

    exp_state.assoc((), {"cur_block": block, "cur_trial": trial})


def next_trial():
    cur_trial = exp_state.get_path("cur_trial", None)
    num_trials = exp_state.get_path("num_trials", None)
    cur_block = exp_state.get_path("cur_block", None)
    num_blocks = len(exp_state.get_path("blocks")) if exp_state.contains((), "blocks") else None

    if num_trials is not None and cur_trial + 1 >= num_trials:
        # next block
        if num_blocks is not None and cur_block + 1 < num_blocks:
            set_phase(cur_block + 1, 0)
        else:
            end()
    else:
        # next trial
        set_phase(cur_block, cur_trial + 1)


def next_block():
    num_blocks = len(exp_state.get_path("blocks")) if exp_state.contains((), "blocks") else None
    cur_block = exp_state.get_path("cur_block")
    if num_blocks is not None and cur_block + 1 >= num_blocks:
        end()
    else:
        set_phase(cur_block + 1, 0)


def load_experiments(experiments_dir=config.experiments_dir):
    experiment_specs = {}
    experiment_pys = experiments_dir.glob("*.py")

    for py in experiment_pys:
        module, spec = load_module(py)
        cls = find_subclass(module, Experiment)
        if cls is not None:
            experiment_specs[py.stem] = spec

    return experiment_specs


def refresh_experiment_list():
    global experiment_specs
    experiment_specs = load_experiments()
    log.info(
        f"Loaded {len(experiment_specs)} experiment(s): {', '.join(experiment_specs.keys())}"
    )


def set_experiment(name):
    global cur_experiment

    if is_running() is True:
        raise ExperimentException(
            "Can't set experiment while an experiment is running."
        )

    if name not in experiment_specs.keys() and name is not None:
        raise ExperimentException(f"Unknown experiment name: {name}")

    if cur_experiment is not None:
        cur_experiment.release()

    if name is not None:
        spec = experiment_specs[name]
        module = reload_module(spec)
        cls = find_subclass(module, Experiment)
        cur_experiment = cls(log)

        log.info(f"Loaded experiment {name}.")
    else:
        cur_experiment = None
        log.info("Unloaded experiment.")

    state.update(("experiment", "cur_experiment"), name)


class Experiment:
    default_params = {}

    def __init__(self, logger):
        self.log = logger
        self.setup()

    def run(self):
        pass

    def end(self):
        pass

    def setup(self):
        pass

    def release(self):
        pass


# Convenience functions


def is_running():
    return state.get_path(("experiment", "is_running"), False)

params = state.Cursor(("experiment", "params"))


########################


def init(logger):
    global log

    log = logger
    refresh_experiment_list()


def shutdown():
    if cur_experiment is not None:
        if is_running():
            end()
        set_experiment(None)

    state_dispatcher.stop()
