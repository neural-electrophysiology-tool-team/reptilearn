import experiment as exp
import arena
import schedule


class TestExperiment(exp.Experiment):
    default_params = {
        "run_msg": "TestExperiment is running",
        "end_msg": "TestExperiment has ended",
        "blink_dur": 1.0
    }

    default_blocks = [
        {"run_msg": f"block {i}", "end_msg": f"end block {i}"} for i in range(5)
    ]

    def run_trial(self, params):
        self.log.info("new trial")
        
    def run_block(self, params):
        self.log.info(params["run_msg"])
        arena.signal_led(True)
        if "blink_dur" in params:
            schedule.once(lambda: arena.signal_led(False), params["blink_dur"])

    def run(self, params):
        self.log.info(params["run_msg"])

        exp.state_dispatcher.add_callback(
            "sensors",
            lambda o, n: self.log.info(f"Sensors update: {o} -> {n}")
        )

        #arena.day_lights(True)

    def end_block(self, params):
        self.log.info(params["end_msg"])

    def end(self, params):
        self.log.info(params["end_msg"])
        exp.state_dispatcher.remove_callback("sensors")
        #arena.day_lights(False)
