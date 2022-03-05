import experiment as exp


class TestPhasesExperiment(exp.Experiment):
    default_params = {
        "run_msg": "TestExperiment is running",
        "end_msg": "TestExperiment has ended",
    }

    def setup(self):
        pass

    def run_trial(self):
        self.log.info(f"new trial {exp.session_state['cur_trial']}")

    def run_block(self):
        self.log.info(f"run block: {exp.get_params()['run_msg']}")

    def run(self):
        self.log.info(f"run: {exp.get_params()['run_msg']}")

    def end(self):
        self.log.info(f"end: {exp.get_params()['end_msg']}")

    def end_block(self):
        self.log.info(f"end block: {exp.get_params()['end_msg']}")

    def end_trial(self):
        self.log.info(f"trial {exp.session_state['cur_trial']} ended")

    def release(self):
        pass
