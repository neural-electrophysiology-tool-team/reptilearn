import config
import state
import sys
from dynamic_loading import load_module, find_subclass, reload_module


class ExperimentException(Exception):
    pass


state.update("experiment", {})
exp_state = state.Cursor("experiment")
exp_state.update((), {"is_running": False})
params = exp_state.get_cursor("params")
blocks = exp_state.get_cursor("blocks")

cur_experiment = None
cur_experiment_name = None
state_dispatcher = state.Dispatcher()


# experiment can be running or not. stop either because it ended or because we asked it to.
# should have cur block, trial and num_blocks num_trials
# the experiment should have a params dict that's overriden by block params.
# should have cur params with the right params for block (assoc cur block params into global params and put here)
# make it easy to make the flow time based.
def run(exp_params, exp_blocks=[]):
    if is_running() is True:
        raise ExperimentException("Experiment is already running.")

    if cur_experiment is None:
        raise ExperimentException("Can't run experiment. No experiment was set.")

    log.info("")
    log.info(f"Running experiment {cur_experiment_name}")
    log.info("========================================")
    
    params.set(exp_params)
    blocks.set(exp_blocks)

    exp_state.assoc(
        (),
        {"is_running": True},
    )

    try:
        cur_experiment.run()
        set_phase(0, 0)
    except Exception:
        log.exception("Exception while running experiment:")


def end():
    if is_running() is False:
        raise ExperimentException("Experiment is not running.")

    cur_experiment.end()
    exp_state.update("is_running", False)
    log.info(f"Experiment {cur_experiment_name} has ended.")


def set_phase(block, trial):
    if blocks.exists():
        if len(blocks.get()) <= block and block != 0:
            raise ExperimentException(f"Block {block} is not defined.")
    elif block != 0:
        raise ExperimentException("Experiment doesn't have block definitions.")

    is_new_block = exp_state.get_path("cur_block") != block
    is_new_trial = is_new_block or exp_state.get_path("cur_trial") != trial

    num_trials = merged_params().get("num_trials", None)
    if num_trials is not None and trial >= num_trials:
        raise ExperimentException(f"Trial {trial} is out of range for block {block}.")

    exp_state.assoc((), {"cur_block": block, "cur_trial": trial})

    if cur_experiment is not None:
        if is_new_block:
            cur_experiment.new_block()

        if is_new_trial:
            cur_experiment.new_trial()


def next_trial():
    cur_trial = exp_state.get_path("cur_trial", None)
    cur_block = exp_state.get_path("cur_block", None)

    num_trials = merged_params().get("num_trials", None)

    if num_trials is not None and cur_trial + 1 >= num_trials:
        # next block
        if num_blocks() is not None and cur_block + 1 < num_blocks():
            set_phase(cur_block + 1, 0)
        else:
            end()
    else:
        # next trial
        set_phase(cur_block, cur_trial + 1)


def next_block():
    num_blocks = (
        len(exp_state.get_path("blocks")) if exp_state.contains((), "blocks") else None
    )
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
    global cur_experiment, cur_experiment_name

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
        cur_experiment_name = name
        log.info(f"Loaded experiment {name}.")
    else:
        cur_experiment = None
        log.info("Unloaded experiment.")

    state.update(("experiment", "cur_experiment"), name)


class Experiment:
    default_params = {}
    default_blocks = []

    def __init__(self, logger):
        self.log = logger
        self.setup()

    def run(self):
        pass

    def new_block(self):
        pass

    def new_trial(self):
        pass

    def end(self):
        pass

    def setup(self):
        pass

    def release(self):
        pass


# Convenience functions


def is_running():
    return exp_state.get_path("is_running", False)


def merged_params():
    block_params = cur_block_params().get()
    params_dict = params.get()
    params_dict.update(block_params)
    return params_dict


def cur_block_params():
    if blocks.exists() and exp_state.contains((), "cur_block"):
        cur_block = exp_state.get_path("cur_block")
        return exp_state.get_cursor(("blocks", cur_block))
    else:
        return exp_state.get_cursor("params")


def num_blocks():
    blocks = exp_state.get_path("blocks")
    if blocks is not state.path_not_found:
        return len(blocks)
    else:
        return 0


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
