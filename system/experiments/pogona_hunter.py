import experiment as exp
import mqtt
from data_log import QueuedDataLogger
import video_system
import schedule

# ToDo:
# - use event log (for climbing for ex.)


class PogonaHunter(exp.Experiment):
    default_params = {
        "start_delay": 0.5,  # must be non-zero otherwise a block will start before the previous finishes.
        "record_video": False,
        # pogona hunter params
        "numOfBugs": 1,
        # bugTypes: [] of cockroach | worm | red_beetle | black_beetle | green_beetle |
        # ant | centipede | spider | leaf
        "bugTypes": ["cockroach"],
        "rewardBugs": ["cockroach"],
        # movementType: circle | random | low_horizontal | low_horizontal_noise
        "movementType": "circle",
        "targetDrift": "leftBottom",  # leftBottom | rightBottom
        "speed": 0,  # if 0 config default for bug will be used
        "bugSize": 0,  # int, if 0 config default for bug will be used
        "bugHeight": 100,  # relevant only for horizontal movements
        "bloodDuration": 2000,
        "backgroundColor": "#e8eaf6",
        "timeBetweenBugs": 2000,
        "timeInEdge": 2000,
        "isStopOnReward": False,
        "isAntiClockWise": False,
        "isLogTrajectory": True,
        # when not None the app will playback an image or video from the supplied url.
        "media_url": None,
    }

    def setup(self):
        mqtt.client.subscribe_callback(
            "event/log/touch", mqtt.mqtt_json_callback(self.on_touch)
        )
        mqtt.client.subscribe_callback(
            "event/command/end_app_wait", mqtt.mqtt_json_callback(self.on_done_trials)
        )
        mqtt.client.subscribe_callback(
            "event/log/trajectory", mqtt.mqtt_json_callback(self.on_log_trajectory)
        )
        mqtt.client.subscribe_callback(
            "event/log/video_frames", mqtt.mqtt_json_callback(self.on_log_video_frames)
        )

        self.trajectory_logger = QueuedDataLogger(
            ["time", "x", "y", "bug_type"],
            csv_path=exp.session_state["data_dir"] / "bug_trajectory.csv",
            log_to_db=False,
        )
        self.trajectory_logger.start()

        self.video_frames_logger = QueuedDataLogger(
            ["time", "frame"],
            csv_path=exp.session_state["data_dir"] / "video_frames.csv",
            log_to_db=False,
        )

        self.video_frames_logger.start()

        self.actions["reload webapp"] = {"run": self.reload_app}

    def reload_app(self):
        mqtt.client.publish_json("event/command/reload_app", {})

    def run_trial(self):
        if exp.get_params()["record_video"]:
            video_system.start_record()

        if exp.get_params()["media_url"] is not None:
            schedule.once(
                lambda: mqtt.client.publish_json(
                    "event/command/init_media", {"url": exp.get_params()["media_url"]}
                ),
                exp.get_params()["start_delay"],
            )

        else:
            schedule.once(
                lambda: mqtt.client.publish_json(
                    "event/command/init_bugs", exp.get_params()
                ),
                exp.get_params()["start_delay"],
            )

    def end_trial(self):

        if exp.get_params()["media_url"] is not None:
            mqtt.client.publish_json("event/command/hide_media", {})
        else:
            mqtt.client.publish_json("event/command/hide_bugs", {})

        if exp.get_params()["record_video"]:
            video_system.stop_record()

    def release(self):
        mqtt.client.unsubscribe_callback("event/log/touch")
        mqtt.client.unsubscribe_callback("event/log/trajectory")
        mqtt.client.unsubscribe_callback("event/log/experiment")
        mqtt.client.unsubscribe_callback("event/command/end_app_wait")

        self.trajectory_logger.stop()

    def on_touch(self, _, payload):
        exp.session_state["last_touch"] = payload
        exp.event_logger.log("screen_touch", payload)

    def on_done_trials(self, _, payload):
        exp.next_block()

    def on_log_trajectory(self, _, payload):
        if len(payload) == 0:
            return

        for row in payload[1:]:
            self.trajectory_logger.log(list(row.values()))

    def on_log_video_frames(self, _, payload):
        if len(payload) == 0:
            return

        for row in payload[1:]:
            self.video_frames_logger.log(list(row.values()))
