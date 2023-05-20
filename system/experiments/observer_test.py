import experiment as exp
import video_system as vid
import numpy as np


class ObserverTest(exp.Experiment):
    """
    A simple experiment to test ImageObservers
    """
    default_params = {
        "obs_ids": None,
    }

    def run(self):
        obs_ids = exp.get_params()["obs_ids"]

        if obs_ids is None:
            for obs in vid.image_observers.values():
                obs.start_observing()
        else:
            for obs_id in obs_ids:
                if obs_id in vid.image_observers:
                    vid.image_observers[obs_id].start_observing()

    def end(self):
        obs_ids = exp.get_params()["obs_ids"]
        if obs_ids is None:
            for obs in vid.image_observers.values():
                obs.stop_observing()
        else:
            for obs_id in obs_ids:
                if obs_id in vid.image_observers:
                    vid.image_observers[obs_id].stop_observing()

    def run_trial(self):
        self.remove_listeners = []
        self.log.info("run trial")
        self.update_count = {}
        self.last_ts = {}

        obs_ids = exp.get_params().get("obs_ids", None)
        if obs_ids is not None:
            for obs_id in obs_ids:
                self.remove_listeners.append(vid.image_observers[obs_id].add_listener(
                    self.on_obs_update(obs_id), exp.state
                ))

    def end_trial(self):
        self.log.info("end trial")
        for ls in self.remove_listeners:
            ls()

    def on_obs_update(self, obs_id):
        self.update_count[obs_id] = 0
        self.last_ts[obs_id] = None
    
        def on_update(data, timestamp):
            self.update_count[obs_id] += 1
            if self.last_ts[obs_id] is None:
                ts_delta = None
            else:
                ts_delta = timestamp - self.last_ts[obs_id]
            self.last_ts[obs_id] = timestamp

            if (self.update_count[obs_id] % 100) == 0:
                cs = np.cumsum(data)
                median = cs[-1] / 2
                cs_med = np.argmax(cs > median)
                self.log.info(f"{obs_id}: {self.update_count[obs_id]} {timestamp} {ts_delta} {data.shape} {cs_med}")

        return on_update
