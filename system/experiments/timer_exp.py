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

    # mock
    params_def = {"interval": (1, {"ui": ["input", "float"]})}
    ##

    def setup(self):
        self.cancel_timer = None

    def run_block(self):
        interval = exp.get_params()["interval"]

        self.cancel_timer = schedule.repeat(
            self.timer_fn, interval, exp.get_params().get("num_trials", True)
        )

    def run_trial(self):
        self.log.info(f"{exp.session_state['cur_trial']}: {time.time()}")
        arena.run_command("toggle", "Signal LED", update_value=True)

    def timer_fn(self):
        exp.next_trial()

    def end_block(self):
        self.cancel_timer()
        pass

    def end(self):
        self.log.info("Stopped timer")
