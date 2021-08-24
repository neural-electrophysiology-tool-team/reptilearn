import experiment as exp


def _private_fn(log):
    log.info("private")


def empty_task():
    pass


def test_task(log):
    log.info("running test_task")


def run_experiment(log):
    log.info("running experiment")
    exp.run_experiment()
