"""
Learning experiment procedure as part of Tal's experiment system:
The experiment procedure is capable of running an experiment with a given stimulus type and reward successful experiments.
Author: Or Pardilov, 2021
"""
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
import os

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
        "radius": 200,
        "monitor_color": "yellow",
        "monitor_duration": 60,
        "stimulus": "led",
        "continuous": False,
        "consecutive": True,
        "num_trials": 7,
    }

    def setup(self):
        #initializing needed class variables
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
        self.data_dir=None

    def run(self, params):
        #resetting init values
        self.in_trial = False
        self.got_detection = False
        self.time = 0.0
        self.cancel_trials = None
        self.cancel_logic_trial = None
        self.prev_det = None
        self.prev_trial_detection = False
        self.stim_cancel = None
        self.consq_end = False



        self.data_dir = exp.exp_state["data_dir"]
        self.cur_trial = params["num_trials"]
        self.consecutive = params["consecutive"]
        #determining the experiment type
        self.ex_type = (
            "consecutive"
            if self.consecutive
            else ("continuous" if params["continuous"] else "regular")
        )
        #logging yolo detections
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

        if params["record_all"]:  # record start at init
            video_record.start_record()

        if not self.consecutive:  # no need to schedule next trials if consecutive
            self.cancel_trials = schedule.repeat(
                self.period_call,
                params.get("exp_interval", 100),
                params.get("num_of_exp", 1) - 1,
            )  # schedule the next trials

        #starting image observers
        yolo = exp.image_observers["head_bbox"]
        yolo.on_detection = self.on_yolo_detection
        yolo.start_observing()
        self.log.info("Start Observing")

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
        #presenting chosen stimulus
        params = exp.get_merged_params()
        if params["stimulus"].lower() == "led":
            self.led_stimulus()
        else:
            self.monitor_stimulus()

    def on_yolo_detection(self, payload):
        params = exp.get_merged_params()
        det = payload["detection"]
        if det is not None and len(det) != 0:
            self.yolo_log.log((payload["image_timestamp"], *det))
        else:
            self.yolo_log.log((payload["image_timestamp"], *((None,) * 5)))
        if (
            det is not None
            and self.prev_det is not None
            and len(det) != 0
            and len(self.prev_det) != 0
        ):
            if self.check_detection(det):
                # detection matched criteria
                if self.in_trial and not self.prev_trial_detection:
                    if self.consecutive:
                        if not self.consq_end:
                            self.stim()
                            if (
                                params["reward_detections"]
                                and not params["bypass_detection"]
                                ):
                                self.dispatch_reward()
                            exp.event_logger.log("learn_exp/consecutive_trial_in_radius",None)
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
                            exp.event_logger.log("learn_exp/consecutive_trial_out_radius",params.get("time_diff", 10)) #the remaining time
                        elif time.time() > self.time + params.get("time_diff", 10):
                            #exp.event_logger.log("learn_exp/trial",{"status": "consecutive: out of radius, ended trial"})
                            self.consq_end = False
                            self.end_logic_trial()
                        else:
                            pass

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
        if exp.state["arena", "signal_led"]:
            arena.signal_led(False)
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
        #logging trial data
        if self.in_trial and not self.got_detection:
            self.log.info("Logic trial ended, failure")
            exp.event_logger.log("learn_exp/logical_trial_ended", {"type": self.ex_type,"success": False})
        elif self.in_trial and self.got_detection:
            self.log.info("Logic trial ended, success")
            exp.event_logger.log("learn_exp/logical_trial_ended", {"type": self.ex_type,"success": True})
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
        #on end cancel all records and schedules
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

        if exp.state["arena", "signal_led"]:
            arena.signal_led(False)
        mqtt.client.unsubscribe("reptilearn/pogona_head_bbox")
        mqtt.client.unsubscribe("reptilearn/learn_exp/end")
        self.log.info("exp ended")

    def period_call(self):
        exp.next_trial()


    def detectAruco(self):
        # detecting aruco marker
        params = exp.get_merged_params()
        test_image, _ = exp.image_sources["top"].get_image()
        #currently using 4x4 arucos
        arucoDict = cv.aruco.Dictionary_get(cv.aruco.DICT_4X4_50)
        arucoParams = cv.aruco.DetectorParameters_create()
        (corners, ids, rejected) = cv.aruco.detectMarkers(
            test_image, arucoDict, parameters=arucoParams
        )
        img_w_markers= cv.cvtColor(test_image, cv.COLOR_GRAY2BGR)
        if corners != None and len(corners) > 0:
            detection = corners[0][0]
            mean_xy = np.mean(detection, axis=0)
            self.end_point = (mean_xy[0], mean_xy[1])
            self.log.info("End point is " + str(self.end_point))
            img_w_markers= cv.aruco.drawDetectedMarkers( img_w_markers,corners)
        else:
            self.log.info("Did not detect any aruco markers!")
            self.end_point = params["default_end"]
        #saving annotated frame
        img_w_circle = cv.circle(img_w_markers, self.end_point, radius=params["radius"], color=(0, 255, 0), thickness=5)
        cv.imwrite(os.path.join(self.data_dir,
                                "arena_reinforced_area_"+ datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".jpg"), img_w_circle)
