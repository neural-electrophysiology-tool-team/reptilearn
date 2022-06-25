import cv2 as cv
import numpy as np
import datetime

import experiment as exp
from experiment import session_state
from video_system import image_sources, image_observers
import schedule
import arena
import data_log
import video_system


def detect_aruco(src_id):
    test_image, _ = image_sources[src_id].get_image(scale_to_8bit=True)
    # currently using 4x4 arucos
    arucoDict = cv.aruco.Dictionary_get(cv.aruco.DICT_4X4_50)
    arucoParams = cv.aruco.DetectorParameters_create()
    corners, ids, rejected = cv.aruco.detectMarkers(
        test_image, arucoDict, parameters=arucoParams
    )
    img_w_markers = cv.cvtColor(test_image, cv.COLOR_GRAY2BGR)

    if corners is not None and len(corners) > 0:
        markers = []

        for marker_corners, marker_id in zip(corners, ids):
            cs = marker_corners[0]
            mean_xy = np.mean(cs, axis=0)
            aruco_center = (mean_xy[0], mean_xy[1])
            markers.append(
                {
                    "center": aruco_center,
                    "corners": cs,
                    "id": marker_id[0],
                }
            )

        img_w_markers = cv.aruco.drawDetectedMarkers(img_w_markers, corners)
        return markers, img_w_markers
    else:
        return None, None


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


class DiscriminationExperiment(exp.Experiment):
    default_params = {
        "image_source_id": "top",
        "blink_dur_left": 1000,  # ms
        "blink_dur_right": 200,  # ms
        "light": "Signal LED",
        "left_feeder": "Bottom feeder",
        "right_feeder": "Top feeder",
        "left_aruco_id": 3,
        "right_aruco_id": 1,
        "feeding_radius": 200,
        "cue_duration": 10,  # seconds
        "record_video": True,
        "shaping_mode": True,
        "min_idle_time": 30,  # seconds
        "max_idle_time": 180,  # seconds
        "$num_trials": 15,
    }

    def find_aruco(self):
        self.aruco_markers, self.aruco_img = detect_aruco(
            session_state["params", "image_source_id"]
        )
        if self.aruco_markers is not None:
            self.log.info(f"Found {len(self.aruco_markers)} aruco markers.")
        else:
            self.log.warning("Did not find any aruco markers.")

    def log_next_detection(self):
        self.print_next_detection = True

    def setup(self):
        self.actions["Find aruco markers"] = {"run": self.find_aruco}
        self.actions["Log next detection"] = {"run": self.log_next_detection}
        self.find_aruco()
        self.bbox_collector = BBoxDataCollector(self.log)
        self.print_next_detection = False

    def run(self):
        self.rng = np.random.default_rng()

        self.left_feeding_pos = None
        self.right_feeding_pos = None

        params = exp.get_params()

        for a in self.aruco_markers:
            if a["id"] == params["left_aruco_id"]:
                self.left_feeding_pos = a["center"]
            elif a["id"] == params["right_aruco_id"]:
                self.right_feeding_pos = a["center"]

        if self.left_feeding_pos is None or self.right_feeding_pos is None:
            raise ValueError("Could not find left and/or right feeding positions")
        else:
            self.log.info(f"Left feeding position: {self.left_feeding_pos}")
            self.log.info(f"Right feeding position: {self.right_feeding_pos}")

        self.radius = params["feeding_radius"]

        if self.aruco_img is not None:
            img = np.copy(self.aruco_img)
        else:
            img, _ = image_sources[params["image_source_id"]].get_image()

        for a in self.aruco_markers:
            img = cv.circle(
                img,
                tuple(a["center"]),
                radius=self.radius,
                color=(0, 255, 0),
                thickness=5,
            )

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        area_image_path = session_state["data_dir"] / f"feeding_areas_{now_str}.jpg"
        self.log.info(f"Saving feeding areas image to {area_image_path}")
        cv.imwrite(str(area_image_path), img)

        if params["record_video"]:
            video_system.start_record()

        self.bbox_collector.run(self.on_bbox_detection)
        self.shaping_mode = params["shaping_mode"]
        session_state["state"] = "idle"

    def run_trial(self):
        self.left_trial = self.rng.random() > 0.5
        self.log.info(f"Starting {'left' if self.left_trial else 'right'} trial.")
        self.show_cue(self.left_trial)

    def end(self):
        self.bbox_collector.end()
        if exp.get_params()["record_video"]:
            video_system.stop_record()        

    def is_in_area(self, left, det):
        if det is None:
            return None

        x1, y1, x2, y2 = det[:4]
        centroid = [(x2 + x1) / 2, (y2 + y1) / 2]

        loc = self.left_feeding_pos if left else self.right_feeding_pos
        dist2 = (centroid[0] - loc[0]) ** 2 + (centroid[1] - loc[1]) ** 2
        return dist2 <= self.radius ** 2

    def on_bbox_detection(self, payload):
        if self.print_next_detection:
            det = payload["detection"]
            self.log.info(f"Head bbox: {det}")
            self.print_next_detection = False

        if "state" not in session_state:
            return

        if session_state["state"] == "feed":
            det = payload["detection"]
            if det is None:
                return

            if self.is_in_area(left=True, det=det):
                if self.left_trial:
                    self.dispense()

                self.to_idle_state()

            elif self.is_in_area(left=False, det=det):
                if not self.left_trial:
                    self.dispense()

                self.to_idle_state()

    def show_cue(self, left):
        session_state["state"] = "cue"

        params = exp.get_params()
        blink_dur = params["blink_dur_left"] if left else params["blink_dur_right"]
        arena.run_command("periodic", params["light"], [1, blink_dur], False)

        def stop_blink():
            arena.run_command("periodic", params["light"], [0], True)
            self.to_feed_state()

        self.cancel_stop_blink = schedule.once(
            stop_blink,
            params["cue_duration"],
        )

    def to_feed_state(self):
        session_state["state"] = "feed"
        if self.shaping_mode:
            self.dispense()
            self.to_idle_state()

    def to_idle_state(self):
        session_state["state"] = "idle"
        params = exp.get_params()
        min_t, max_t = params["min_idle_time"], params["max_idle_time"]
        idle_time = self.rng.random() * (max_t - min_t) + min_t
        self.log.info(f"Waiting {idle_time:.2f} seconds.")
        schedule.once(exp.next_trial, idle_time)

    def dispense(self):
        if self.left_trial:
            arena.run_command("dispense", exp.get_params()["left_feeder"], None, False)
        else:
            arena.run_command("dispense", exp.get_params()["right_feeder"], None, False)
