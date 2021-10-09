import experiment as exp
import mqtt
from data_log import QueuedDataLogger

# ToDo:
# - use event log (for climbing for ex.)
# - trialDuration doesn't seem to work. test params


class PogonaHunter(exp.Experiment):
    default_params = {
        "numOfBugs": 0,
        "numTrials": None,
        "trialDuration": 10,
        "iti": 5,
        # bugTypes: [] of cockroach | worm | red_beetle | black_beetle | green_beetle |
        # ant | centipede | spider
        "bugTypes": ["cockroach"],
        "rewardBugs": "cockroach",
        # movementType: circle | random | random_drift | low_horizontal | low_horizontal_noise
        "movementType": "circle",
        "speed": 0,
        "bugSize": 0,  # int
        "bloodDuration": 2000,
        "backgroundColor": "#e8eaf6",
        "rewardAnyTouchProb": 0,
        "holeSize": [200, 200],
        "exitHole": "bottomRight",
        "entranceHole": None,
        "timeInEdge": 2000,
        "isStopOnReward": False,
        "isAntiClockWise": False,
        "targetDrift": "leftBottom",
        "bugHeight": 100,
        "isLogTrajectory": True,
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
            "event/log/experiment", mqtt.mqtt_json_callback(self.on_experiment_log)
        )

        self.trajectory_logger = QueuedDataLogger(
            ["time", "x", "y", "bug_type"],
            csv_path=exp.session_state["data_dir"] / "bug_trajectory.csv",
            log_to_db=False,
        )
        self.trajectory_logger.start()

    def run_block(self):
        mqtt.client.publish_json("event/command/init_bugs", exp.get_params())

    def end_block(self):
        mqtt.client.publish_json("event/command/hide_bugs", {})

    def release(self):
        mqtt.client.unsubscribe_callback("event/log/touch")
        mqtt.client.unsubscribe_callback("event/log/trajectory")
        mqtt.client.unsubscribe_callback("event/log/experiment")
        mqtt.client.unsubscribe_callback("event/command/end_app_wait")

        self.trajectory_logger.stop()

    def on_touch(self, _, payload):
        exp.session_state["last_touch"] = payload
        self.log.info(
            "Screen touch detected. Touch info is stored under the session.last_touch state key."
        )

    def on_done_trials(self, _, payload):
        exp.next_block()

    def on_log_trajectory(self, _, payload):
        self.log.info(list(payload[0].values()))
        self.log.info(f"Saving bug trajectory to {self.trajectory_logger.csv_path}")
        for row in payload[1:]:
            self.trajectory_logger.log(list(row.values()))

    def on_experiment_log(self, _, payload):
        self.log.info(f"Experiment log: {payload}")
