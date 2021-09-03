import experiment as exp
from experiment import session_state
from video_system import image_sources, image_observers
from state import state
import arena
import schedule
import video_record
import cv2 as cv
import datetime
import numpy as np
import time
import data_log
import bbox

# TODO:
# - video recording (with overhead?)
# - event_log
# - display cue


def detect_aruco(src_id):
    test_image, _ = image_sources[src_id].get_image()
    # currently using 4x4 arucos
    arucoDict = cv.aruco.Dictionary_get(cv.aruco.DICT_4X4_50)
    arucoParams = cv.aruco.DetectorParameters_create()
    corners, ids, rejected = cv.aruco.detectMarkers(
        test_image, arucoDict, parameters=arucoParams
    )
    img_w_markers = cv.cvtColor(test_image, cv.COLOR_GRAY2BGR)

    if corners is not None and len(corners) > 0:
        detection = corners[0][0]
        mean_xy = np.mean(detection, axis=0)
        aruco_center = (mean_xy[0], mean_xy[1])
        img_w_markers = cv.aruco.drawDetectedMarkers(img_w_markers, corners)
        return aruco_center, corners, img_w_markers
    else:
        return None, corners, None


def led_blink(num_blinks, led_duration):
    interval = led_duration / num_blinks / 2

    def toggle_led():
        arena.signal_led(not state["arena", "signal_led"])

    arena.signal_led(False)

    return schedule.repeat(toggle_led, interval, repeats=num_blinks * 2)


class BBoxDataCollector:
    def __init__(self, logger):
        self.log = logger

    def run(self, callback):
        self.callback = callback

        self.bbox_log = data_log.QueuedDataLogger(
            columns=[
                ("time", "timestamptz not null"),
                ("x1", "double precision"),
                ("y1", "double precision"),
                ("x2", "double precision"),
                ("y2", "double precision"),
                ("confidence", "double precision"),
            ],
            csv_path=session_state["data_dir"] / "head_bbox.csv",
            table_name="bbox_position",
        )
        self.bbox_log.start()
        self.obs = image_observers["head_bbox"]
        self.obs.on_detection = self.on_detection
        self.obs.start_observing()

    def end(self):
        self.obs.stop_observing()
        self.bbox_log.stop()

    def on_detection(self, payload):
        det = payload["detection"]
        if det is not None and len(det) != 0:
            self.bbox_log.log((payload["image_timestamp"], *det))
        else:
            self.bbox_log.log((payload["image_timestamp"], *((None,) * 5)))

        self.callback(payload)


class LocationExperiment(exp.Experiment):
    default_params = {
        "reinforced_area": {
            "location": [0, 0],
            "radius": 200,
            "use_aruco": True,  # Bypass the location value with Aruco marker coordinates
        },
        "reward_radius": 200,
        "reward_delay": 5,  # seconds
        "dispense_reward": True,
        "area_stay_duration": 2,  # seconds
        "cooldown_duration": 10,  # seconds
        "cue": {
            "type": "led",  # "led" | "led_blink" | "display"
            "num_blinks": 4,  # for type = "led_blink"
            "led_duration": 5,
            "display_color": "yellow",
            "display_duration": 10,
        },
        "record_video": True,
        "image_source_id": "top",
    }

    def find_aruco(self):
        # we can also save the image here
        center, corners, self.aruco_img = detect_aruco(
            session_state["params", "image_source_id"]
        )

        if center is not None:
            self.log.info("Found aruco markers (see state.session.aruco).")
            session_state["aruco"] = center
        else:
            self.log.info("No aruco markers found.")

    def setup(self):
        self.actions["Find aruco markers"] = {"run": self.find_aruco}

        self.find_aruco()
        self.bbox_collector = BBoxDataCollector(self.log)

    def run(self, params):
        self.find_reinforced_location(params)
        self.bbox_collector.run(self.on_bbox_detection)
        session_state["is_in_area"] = False
        self.in_out_time = None
        session_state.add_callback("is_in_area", self.is_in_area_changed)
        session_state["cooldown"] = False
        session_state["reward_scheduled"] = False
        self.cancel_cooldown = None
        self.cancel_reward_delay = None
        self.cancel_blink = None
        if params["record_video"]:
            video_record.start_record()

    def run_trial(self, params):
        if session_state["cur_trial"] == 0:
            return

        # Success
        if params["dispense_reward"]:
            self.log.info("Trial ended. Dispensing reward.")
            arena.dispense_reward()
        else:
            self.log.info("Trial ended.")

        session_state["reward_scheduled"] = False

    def end(self, params):
        self.bbox_collector.end()
        session_state.remove_callback("is_in_area")
        if params["record_video"]:
            video_record.stop_record()

    def find_reinforced_location(self, params):
        if params["reinforced_area"]["use_aruco"] and self.aruco_img is not None:
            if "aruco" in session_state:
                session_state["reinforced_location"] = session_state["aruco"]
            else:
                session_state["reinforced_location"] = params["reinforced_area"][
                    "location"
                ]
        else:
            session_state["reinforced_location"] = params["reinforced_area"]["location"]

        if self.aruco_img is not None:
            img = np.copy(self.aruco_img)
        else:
            img, _ = image_sources[params["image_source_id"]].get_image()

        img = cv.circle(
            img,
            tuple(session_state["reinforced_location"]),
            radius=params["reinforced_area"]["radius"],
            color=(0, 255, 0),
            thickness=5,
        )
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        area_image_path = session_state["data_dir"] / f"reinforced_area_{now_str}.jpg"
        self.log.info(f"Saving area image to {area_image_path}")
        cv.imwrite(str(area_image_path), img)

    def on_bbox_detection(self, payload):
        det = payload["detection"]
        self.update_is_in_area(det)

    def update_is_in_area(self, det):
        if det is None:
            # later might take part in logic
            return

        params = exp.get_phase_params()
        centroid = bbox.xyxy_to_centroid(np.array(det))
        was_in_area = session_state["is_in_area"]

        loc = session_state["reinforced_location"]
        dist_to_location = (centroid[0] - loc[0]) ** 2 + (centroid[1] - loc[1]) ** 2
        is_in_area = dist_to_location <= params["reinforced_area"]["radius"] ** 2
        if was_in_area != is_in_area:
            self.in_out_time = time.time()
            session_state["is_in_area"] = is_in_area

        return dist_to_location

    def maybe_end_trial(self):
        params = exp.get_phase_params()
        if (
            session_state["is_in_area"]
            and time.time() - self.in_out_time > params["area_stay_duration"]
        ):
            session_state["reward_scheduled"] = True
            self.cancel_blink = led_blink(
                params["cue"]["num_blinks"], params["cue"]["led_duration"]
            )
            self.cancel_reward_delay = schedule.once(
                exp.next_trial, params["reward_delay"]
            )

    def maybe_end_cooldown(self):
        if not session_state["is_in_area"] and session_state["cooldown"]:
            session_state["cooldown"] = False

    def is_in_area_changed(self, old, new):
        # TODO: make sure area changed continuously
        params = exp.get_phase_params()

        if not old and new:
            exp.event_logger.log(
                "loclearn/entered_area", {"cooldown": session_state["cooldown"]}
            )
            if session_state["cooldown"]:
                self.log.info("Animal entered the reinforced area during cooldown.")
                self.cancel_cooldown()
                session_state["cooldown"] = False
            else:
                self.log.info("Animal entered the reinforced area.")
                schedule.once(self.maybe_end_trial, params["area_stay_duration"])

        elif old and not new:
            exp.event_logger.log("loclearn/left_area", None)
            self.log.info("Animal left the reinforced area.")
            if self.cancel_blink is not None:
                self.cancel_blink()
                arena.signal_led(False)
            if self.cancel_reward_delay is not None:
                self.cancel_reward_delay()

            if session_state["reward_scheduled"]:
                session_state["cooldown"] = True
                self.cancel_cooldown = schedule.once(
                    self.maybe_end_cooldown, params["cooldown_duration"]
                )
