import experiment as exp
import threading
import state


class TimerExperiment(exp.Experiment):
    def setup(self):
        self.log.info("Hi setting up!")
        
    def timer_fn(self):
        exp.mqttc.publish("reptilearn/timer", "tick")
        if self.running:
            interval = state.get_state_path(("experiment", "params", "interval"), 1)
            threading.Timer(interval, self.timer_fn).start()
        
    def run(self):
        interval = state.get_state_path(("experiment", "params", "interval"), 1)
        self.log.info(f"Set timer every {interval} sec.")
        self.running = True
        threading.Timer(interval, self.timer_fn).start()

    def end(self):
        self.log.info("Stopped timer")
        self.running = False
