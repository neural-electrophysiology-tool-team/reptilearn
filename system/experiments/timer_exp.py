import experiment as exp
import schedule
import time
import arena


class TimerExperiment(exp.Experiment):
    default_params = {
        "interval": 1,
    }

    default_blocks = [
        {"num_trials": 2},
        {"num_trials": 3, "interval": 2},
        {"num_trials": 6, "interval": 0.5},
        {"interval": 2},
    ]

    def setup(self):
        self.cancel_timer = None
        
    def run_block(self, params):
        interval = params["interval"]

        self.cancel_timer = schedule.repeat(
            self.timer_fn, interval, params.get("num_trials", True)
        )

    def run_trial(self, params):
        self.log.info(f"{exp.exp_state['cur_trial']}: {time.time()}")
        arena.signal_led(True)
        schedule.once(lambda: arena.signal_led(False), params["interval"] / 2)


    def timer_fn(self):
        exp.next_trial()

    def end_block(self, params):
        pass

    def end(self, params):
        if self.cancel_timer is not None:
            self.cancel_timer()

        self.log.info("Stopped timer")
