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
        
    def new_block(self):
        params = exp.merged_params()
        self.log.info(f"new block: {exp.exp_state.get_path('cur_block')} {params}")
        if self.cancel_timer is not None:
            self.cancel_timer()
            
        self.log.info(params)
        interval = params["interval"]
        self.log.info(f"Set timer every {interval} sec.")
        self.cancel_timer = schedule.repeat(self.timer_fn, interval)

    def new_trial(self):
        self.log.info(f"new trial: {exp.exp_state.get_path('cur_trial')}")

    def timer_fn(self):
        mqtt.client.publish("reptilearn/timer", "tick")
        # self.log.info("Tick")
        exp.next_trial()

    def end(self):
        if self.cancel_timer is not None:
            self.cancel_timer()
        self.log.info("Stopped timer")

