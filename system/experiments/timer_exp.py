import experiment as exp
import threading
import state
import mqtt


class TimerExperiment(exp.Experiment):
    default_params = {
        "interval": 1,
    }
    
    def timer_fn(self):
        mqtt.client.publish("reptilearn/timer", "tick")
        self.log.info("Tick")
        exp.next_trial()
        
        if exp.is_running():
            threading.Timer(exp.params.get_path("interval"), self.timer_fn).start()
        
    def run(self):
        interval = exp.params.get_path("interval")
        self.log.info(f"Set timer every {interval} sec.")
        threading.Timer(interval, self.timer_fn).start()

    def end(self):
        self.log.info("Stopped timer")
