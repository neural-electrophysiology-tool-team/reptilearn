import experiment as exp
import mqtt
import data_log
import arena
import time
import datetime
import schedule
import video_record
import numpy as np
import cv2 as cv
import monitor
import math


class LearnExp(exp.Experiment):
    default_params = {
        "record_all": True,
        "exp_interval": 500,
        "trial_length": 150,
        "record_exp": True,
        "led_duration": 2,
        "led_blinks": 4,
        "min_confidence": 0.6,
        "bypass_detection": False,
        "reward_detections": True,
        "reward_delay": None,
        "record_overhead": 0,
        "default_end": (50, 50),
        "radius": 300,
        "monitor_color": "yellow",
        "monitor_duration": 60,
        "stimulus": "led",
        "continuous": False,
        "consecutive": True,
        "num_trials": 7,
    }

    def setup(self):
        self.in_trial = False
        self.got_detection = False
        self.cancel_trials = None
        self.cancel_logic_trial = None
        self.cur_trial = None
        self.reward_delay = None
        self.frame_count = 0
        self.prev_det = None
        self.prev_trial_detection = False
        self.stim_cancel = None
        self.consecutive = False
        self.consq_end = False
        self.ex_type = None
        self.time = 0.0

    def run(self, params):

        self.cur_trial = params["num_trials"]
        self.consecutive = params["consecutive"]
        self.ex_type = (
            "consecutive"
            if self.consecutive
            else ("continuous" if params["continuous"] else "regular")
        )
        ##logging

        self.learn_log = data_log.QueuedDataLogger(
            columns=[
                ("time", "timestamptz not null"),
                ("trial", "int"),
                ("type", "text"),
                ("status", "text"),
            ],
            csv_path=exp.exp_state["data_dir"] / "learn_data.csv",
            table_name="learn_status",
        )
        self.learn_log.start()

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
            table_name="bbox_position",
        )
        self.yolo_log.start()
        
        # detecting Aruco squares within arena
        self.detectAruco()
        arena.day_lights(True)
        if params["record_all"]:  # record start at init
            video_record.start_record()

        mqtt.client.subscribe_callback(
            "reptilearn/learn_exp/end", self.on_end
        )  # temp debug

        mqtt.client.subscribe_callback(
            "reptilearn/pogona_head_bbox",
            mqtt.mqtt_json_callback(self.on_yolo_detection),
        )  # sub to image detections
        if not self.consecutive:  # no need to schedule next trials if consecutive
            self.cancel_trials = schedule.repeat(
                self.period_call,
                params.get("exp_interval", 100),
                params.get("num_of_exp", 1) - 1,
            )  # schedule the next trials

        exp.image_observers[
            "head_bbox"
        ].start_observing()  # start image observers to detect on arena
        self.log.info("Start Oberserving")

    def run_trial(self, params):

        self.in_trial = True

        if (
            params.get("record_exp", True) and not params["record_all"]
        ):  # recording trials only
            video_record.start_record()

        self.log.info(
            "Trial "
            + str(params["num_trials"] - self.cur_trial)
            + " started "
            + str(datetime.datetime.now())
        )

        if not self.consecutive:
            self.stim()  # present stimulus at trials start
            # giving a reward if bypass_detection enabled
            if params["bypass_detection"] and params["reward_detections"]:
                self.dispatch_reward()
                self.end_logic_trial()
            else:  # scheduling the logical end of trial
                self.cancel_logic_trial = schedule.once(
                    self.end_logic_trial, params["trial_length"]
                )

        self.log.info("run trial procedure finished")

    def stim(self):
        params = exp.get_merged_params()
        if params["stimulus"].lower() == "led":
            self.led_stimulus()
        else:
            self.monitor_stimulus()

    def on_yolo_detection(self, topic, payload):
        params = exp.get_merged_params()
        det = payload["detection"]
        if (
            det is not None
            and self.prev_det is not None
            and len(det) != 0
            and len(self.prev_det) != 0
        ):
            if self.check_detection(det):
                # detection matched criteria
                # self.log.info("YOLO success at "+str(det))
                if self.in_trial and not self.prev_trial_detection:
                    if self.consecutive:
                        self.stim()
                        if (
                            params["reward_detections"]
                            and not params["bypass_detection"]
                        ):
                            self.dispatch_reward()
                        self.consq_end = True
                        self.got_detection = True
                        self.time = 0.0
                    else:
                        # during trial and object moved since last success
                        self.got_detection = True
                        if (
                            params["reward_detections"]
                            and not params["bypass_detection"]
                        ):
                            self.dispatch_reward()

                        self.cancel_logic_trial()  # got detection, canceling scheduled end
                        self.end_logic_trial()

                elif self.in_trial:
                    pass
                    # during trial, object did not move since last success
                    # self.log.info("Ignored success, location did not changed since last success")
                self.prev_trial_detection = True
            else:
                if self.prev_trial_detection:
                    # object location does not macth criteria
                    self.prev_trial_detection = False

                    if (
                        self.consq_end
                    ):  # during consecutive trial and holding to start the next
                        if self.time == 0.0:
                            self.time = time.time()
                        elif time.time() > self.time + params.get("time_diff", 10):
                            self.consq_end = False
                            self.end_logic_trial()

        if det is not None:
            if det is not None and len(det) != 0:
                self.yolo_log.log((payload["image_timestamp"], *det))
            else:
                self.yolo_log.log((payload["image_timestamp"], *((None,) * 5)))

            self.frame_count += 1
            if self.frame_count % 120 == 0:  # debug
                self.log.info("INFO: GOT " + str(det))

        self.prev_det = det

    def check_detection(self, locations):
        params = exp.get_merged_params()
        # getting the center of the detection (head), checking if its within range.
        center = ((locations[2] + locations[0]) / 2, (locations[3] + locations[1]) / 2)
        res = (
            True
            if math.sqrt(
                abs(center[0] - self.end_point[0]) ** 2
                + abs(center[1] - self.end_point[1]) ** 2
            )
            < params["radius"]
            else False
        )
        return res and (
            locations[-1] >= params["min_confidence"]
        )  # check if confidence is high enough

    def led_stimulus(self):
        params = exp.get_merged_params()
        self.stim_cancel = schedule.repeat(
            lambda: arena.signal_led(not exp.state["arena", "signal_led"]),
            params["led_duration"],
            2 * params.get("led_blinks", 1),
        )

    def monitor_stimulus(self):
        params = exp.get_merged_params()
        monitor.chnage_color(params.get("monitor_color", "random"))
        self.stim_cancel = schedule.once(
            mqtt.client.publish(
                topic="monitor/color", payload=params.get("monitor_color", "black")
            ),
            params.get("monitor_duration", 60),
        )

    def end_logic_trial(self):
        params = exp.get_merged_params()
        self.stim_cancel()  # canceling stimulus, if active.
        if params["stimulus"] == "monitor":
            monitor.chnage_color("black")
        timestap = time.time()
        if self.in_trial and not self.got_detection:
            self.log.info("Logic trial ended, failure")
            self.learn_log.log((timestap, self.cur_trial, self.ex_type, "failure"))
        elif self.in_trial and self.got_detection:
            self.log.info("Logic trial ended, success")
            self.learn_log.log((timestap, self.cur_trial, self.ex_type, "success"))
        else:
            self.log.info("Logic trial ended")

        # continuous trial: schedule the next.
        self.in_trial = False
        self.got_detection = False
        if params.get("continuous", False):
            if params["record_exp"] and not params["record_all"]:
                video_record.stop_record()
            self.cancel_trials()
            self.cancel_trials = schedule.repeat(
                self.period_call, interval, self.cur_trial - 1
            )
        elif self.consecutive:
            if params["record_exp"] and not params["record_all"]:
                schedule.once(
                    lambda: video_record.stop_record(), params.get("record_overhead", 0)
                )
            if self.cur_trial > 0:
                exp.next_trial()
        else:
            if params["record_exp"] and not params["record_all"]:
                schedule.once(
                    lambda: video_record.stop_record(), params.get("record_overhead", 0)
                )

    def end_trial(self, params):
        if self.in_trial:
            self.log.info("Logic trial wasnt finished!")
            if params.get("record_exp", True) and not params["record_all"]:
                schedule.once(
                    lambda: video_record.stop_record(), params.get("record_overhead", 0)
                )
            if params["stimulus"] == "monitor":
                monitor.chnage_color("black")
            self.in_trial = False
            self.got_detection = False

        self.cur_trial = self.cur_trial - 1

    def dispatch_reward(self):
        params = exp.get_merged_params()
        if params["reward_delay"] == None:
            self.reward_delay = params["led_duration"] * params["led_blinks"]
        else:
            self.reward_delay = params["reward_delay"]
        schedule.once(self.dispatch_reward_actual, self.reward_delay)

    def dispatch_reward_actual(self):
        self.log.info("REWARD SENT")
        arena.dispense_reward()

    def end(self, params):
        if params.get("record_exp", True) or params["record_all"]:
            video_record.stop_record()
        if self.cancel_trials != None:
            self.cancel_trials()
        if self.cancel_logic_trial != None:
            self.cancel_logic_trial()
        schedule.cancel_all()
        mqtt.client.publish(topic="monitor/color", payload="black")
        exp.image_observers["head_bbox"].stop_observing()
        self.yolo_log.stop()
        self.learn_log.stop()
        mqtt.client.unsubscribe("reptilearn/pogona_head_bbox")
        mqtt.client.unsubscribe("reptilearn/learn_exp/end")
        self.log.info("exp ended")

    def period_call(self):
        exp.next_trial()

    def on_end(self, client, userdata, message):
        # debug: imitate detection
        params = exp.get_merged_params()
        self.log.info("on_end was called")
        msg = str(message.payload.decode())
        self.log.info("got " + msg)
        if msg == "detected":
            # detection matched criteria
            self.log.info("detected")
            if self.in_trial and not self.prev_trial_detection:
                if self.consecutive:
                    self.stim()
                    if params["reward_detections"] and not params["bypass_detection"]:
                        self.dispatch_reward()
                    self.consq_end = True
                    self.got_detection = True
                else:
                    # during trial and object moved since last success
                    self.got_detection = True
                    if params["reward_detections"] and not params["bypass_detection"]:
                        self.dispatch_reward()

                    self.cancel_logic_trial()  # got detection, canceling scheduled end
                    self.end_logic_trial()

            elif self.in_trial:
                # during trial, object did not move since last success
                self.log.info(
                    "Ignored success, location did not changed since last success"
                )
            self.prev_trial_detection = True

        elif self.prev_trial_detection:
            # object location does not macth criteria
            self.prev_trial_detection = False
            if self.consq_end:  # during consecutive trial and holding to start the next
                self.consq_end = False
                self.end_logic_trial()

    def detectAruco(self):
        # detecting aruco marker
        test_image, _ = exp.image_sources["top"].get_image()
        arucoDict = cv.aruco.Dictionary_get(cv.aruco.DICT_4X4_50)
        arucoParams = cv.aruco.DetectorParameters_create()
        (corners, ids, rejected) = cv.aruco.detectMarkers(
            test_image, arucoDict, parameters=arucoParams
        )
        if corners != None and len(corners) > 0:
            detection = corners[0][0]
            mean_xy = np.mean(detection, axis=0)
            self.end_point = (mean_xy[0], mean_xy[1])
            self.log.info("End point is " + str(self.end_point))
        else:
            params = exp.get_merged_params()
            self.log.info("Did not detect any aruco markers!")
            self.end_point = params["default_end"]
