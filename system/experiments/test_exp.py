import state
import mqtt
import experiment as exp
import arena


class TestExperiment(exp.Experiment):
    default_params = {
        "run_msg": "TestExperiment is running",
        "end_msg": "TestExperiment has ended",
    }
    
    def setup(self):
        exp.state_dispatcher.add_callback(("experiment", "cur_trial"), lambda o, n: print("cur_trial:", n))

    def run(self):
        self.log.info(exp.params.get_path("run_msg"))
        arena.signal_led(True)
        
    def end(self):
        self.log.info(exp.params.get_path("end_msg"))
        mqtt.client.publish("reptilearn/testexp/ended")
        arena.signal_led(False)

    def release(self):
        exp.state_dispatcher.remove_callback(("experiment", "cur_trial"))
