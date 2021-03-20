import experiment as exp
import arena


class TestExperiment(exp.Experiment):
    default_params = {
        "run_msg": "TestExperiment is running",
        "end_msg": "TestExperiment has ended",
    }

    default_blocks = [
        {"run_msg": f"block {i}", "end_msg": f"end block {i}"} for i in range(5)
    ]
    
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
