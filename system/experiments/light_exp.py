import experiment as exp
import mqtt
import data_log
import video_record
import random
import schedule
import arena
from state import state


class LightTest(exp.Experiment):
    default_params = {"trial_len_mins": 10, "num_trials": 3}

    def run(self, params):
        self.yolo_log = data_log.QueuedDataLogger(
            columns=[
                ("time", "timestamptz not null"),
                ("x1", "double precision"),
                ("y1", "double precision"),
                ("x2", "double precision"),
                ("y2", "double precision"),
                ("confidence", "double precision"),
            ],
            csv_path=exp.exp_state["data_dir"] / "head_bbox.csv",
            log_to_db=True,
            table_name="bbox_position",
        )
        self.yolo_log.start()

        mqtt.client.subscribe_callback(
            "reptilearn/pogona_head_bbox",
            mqtt.mqtt_json_callback(self.on_yolo_detection),
        )

        exp.image_observers["head_bbox"].start_observing()
        video_record.start_record()

    def run_trial(self, params):
        interval = 60 * random.uniform(
            params["trial_len_mins"] / 10, params["trial_len_mins"] / 2
        )
        self.log.info(f"Dispense reward in {interval} seconds.")
        self.cancel_reward = schedule.once(arena.dispense_reward, interval)
        schedule.once(exp.next_trial, params["trial_len_mins"] * 60)
        self.log.info(f"Next trial in {params['trial_len_mins'] * 60} seconds")

    def end_trial(self, params):
        arena.day_lights(not state["arena", "day_lights"])
        self.cancel_reward()
        pass

    def end(self, params):
        mqtt.client.unsubscribe_callback("reptilearn/pogona_head_bbox")
        video_record.stop_record()
        exp.image_observers["head_bbox"].stop_observing()
        arena.day_lights(False)
        self.yolo_log.stop()
        # schedule.cancel_all()
        pass

    def on_yolo_detection(self, topic, payload):
        det = payload["detection"]
        if det is not None and len(det) != 0:
            self.yolo_log.log((payload["image_timestamp"] / 1e9, *det))
        else:
            self.yolo_log.log((payload["image_timestamp"] / 1e9, *((None,) * 5)))
