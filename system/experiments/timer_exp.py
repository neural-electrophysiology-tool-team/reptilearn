import experiment as exp
import schedule
import mqtt


class TimerExperiment(exp.Experiment):
    default_params = {
        "interval": 1,
        "num_trials": 5,
    }

    default_blocks = [
        {"num_trials": 2},
        {"num_trials": 3, "interval": 2},
        {"num_trials": 6, "interval": 0.5},
    ]

    def setup(self):
        self.cancel_timer = None
        
    def run_block(self, params):
        self.log.info(f"new block: {exp.exp_state.get_path('cur_block')} {params}")
        interval = params["interval"]
        self.log.info(f"Set timer every {interval} sec.")
        self.cancel_timer = schedule.repeat(self.timer_fn, interval)

    def run_trial(self, params):
        self.log.info(f"new trial: {exp.exp_state.get_path('cur_trial')}")

    def timer_fn(self):
        mqtt.client.publish("reptilearn/timer", "tick")
        # self.log.info("Tick")
        exp.next_trial()

    def end_block(self, params):
        if self.cancel_timer is not None:
            self.cancel_timer()

    def end(self, params):
        self.log.info("Stopped timer")

