import experiment as exp
import arena

class FeederTestExperiment(exp.Experiment):
    default_params = {
        "feeder_interface": "Feeder 1",
    }

    def run_trial(self):
        interface = exp.get_params()["feeder_interface"]
        arena.run_command("dispense", interface, None, False)