import experiment as exp
import arena


class TestPhasesExperiment(exp.Experiment):
    default_params = {
        "run_msg": "TestExperiment is running",
        "end_msg": "TestExperiment has ended",
    }

    default_blocks = [
        {"run_msg": f"block {i}", "end_msg": f"end block {i}"} for i in range(5)
    ]

    def setup(self):
        self.actions["run block 3"] = {"run": lambda: exp.set_phase(3, 0)}
        self.actions["stop experiment"] = {"run": exp.stop_experiment}

    def run_trial(self):
        self.log.info("new trial")
        arena.run_command("toggle", "Signal LED")

    def run_block(self):
        self.log.info(exp.get_params()["run_msg"])

    def run(self):
        self.log.info(exp.get_params()["run_msg"])

    def end_block(self):
        self.log.info(exp.get_params()["end_msg"])

    def end(self):
        self.log.info(exp.get_params()["end_msg"])
