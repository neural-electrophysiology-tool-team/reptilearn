import random
import experiment as exp
from experiment import session_state
import arena
import schedule
import mqtt
from state import state


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

    def run_trial(self, params):
        self.log.info("new trial")

    def run_block(self, params):
        self.log.info(params["run_msg"])

    def run(self, params):
        self.log.info(params["run_msg"])

    def end_block(self, params):
        self.log.info(params["end_msg"])

    def end(self, params):
        self.log.info(params["end_msg"])
