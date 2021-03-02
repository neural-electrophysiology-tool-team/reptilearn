import state


class ExperimentException(Exception):
    pass


state.update_state(["experiment"], {
    "running": False
})


# experiment can be running or not. stop either because it ended or because we asked it to.
# should have cur block, trial and num_blocks num_trials
# the experiment should have a params dict that's overriden by block params.
# should have cur params with the right params for block (assoc cur block params into global params and put here)
# make it easy to make the flow time based.
def run(**description):
    state.update_state(["experiment"], description)
    state.assoc_state(["experiment"], {
        "running": True,
        "cur_block": 0,
        "cur_trial": 0,
    })
    # send messages


def end_experiment():
    state.update_state(["experiment", "running"], False)
    # send messages


def set_phase(block, trial):
    # basically only works after running experiment because run resets cur phase.
    blocks = state.get_path(["experiment", "blocks"])
    if blocks == state.path_not_found:
        raise ExperimentException("Bad experiment description. Blocks definition not found.")
    if len(blocks) <= block:
        raise ExperimentException(f"Block {block} is not defined.")

    if "num_trials" in blocks[block] and trial >= blocks[block]["num_trials"]:
        raise ExperimentException(f"Trial {trial} is out of range for block {block}.")

    state.assoc_state(["experiment"], {
        "cur_block": block,
        "cur_trial": trial
    })


def next_trial():
    cur_state = state.get_path(["experiment"])
    if "blocks" not in cur_state:
        raise ExperimentException("Bad experiment description. Blocks definition not found.")

    cur_block_num = cur_state["cur_block"]
    cur_block = cur_state["blocks"][cur_block_num]
    
    cur_trial = cur_state["cur_trial"]
    
    num_trials = cur_block.get("num_trials")
    num_blocks = len(cur_state["blocks"])
    
    if num_trials is not None and cur_trial + 1 >= num_trials:
        # next block
        if cur_block_num + 1 < num_blocks:
            set_phase(cur_block_num + 1, 0)
        else:
            end_experiment()
    else:
        # next trial
        set_phase(cur_block_num, cur_trial + 1)
    
