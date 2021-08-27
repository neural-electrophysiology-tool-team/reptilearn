import experiment as exp


def run(log):
    log.info("Running experiment")
    exp.run_experiment()


def stop(log):
    log.info("Stopping experiment")
    exp.stop_experiment()


def next_block(log):
    log.info("Starting the next block")
    exp.next_block()


def next_trial(log):
    log.info("Starting the next trial")
    exp.next_trial()
