import experiment as exp
from rl_logging import get_main_logger

log = get_main_logger()


def run():
    log.info("Running experiment")
    exp.run_experiment()


def stop():
    log.info("Stopping experiment")
    exp.stop_experiment()


def next_block():
    log.info("Starting the next block")
    exp.next_block()


def next_trial():
    log.info("Starting the next trial")
    exp.next_trial()
