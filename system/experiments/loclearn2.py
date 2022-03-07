import experiment as exp
from experiment import session_state
from video_system import image_sources, image_observers
import arena
import schedule
import video_system
import cv2 as cv
import numpy as np
import time
import data_log
import datetime
import bbox
import random


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


def stop_blink(interface):
    arena.run_command("periodic", interface, [0], True)


def start_blink(interface, period_time=None):
    arena.run_command("periodic", interface, [1, int(period_time)], False)


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
        self.remove_listener = self.obs.add_listener(self.on_detection)
        self.obs.start_observing()

    def end(self):
        self.remove_listener()
        self.obs.stop_observing()
        self.bbox_log.stop()

    def on_detection(self, det, timestamp):
        self.bbox_log.log((timestamp, *det))
        self.callback(det, timestamp)


class LocationExperiment(exp.Experiment):
    default_params = {
        "reinforced_area": {
            "location": [0, 0],  # or
            # "aruco_id": 0,
            "radius": 200,
        },
        "area_stay_duration": 2,  # seconds
        "cooldown_duration": 20,  # seconds
        "cooldown_radius": 300,
        "cue": {
            "type": "led",  # "led" | "led_blink" | "display"
            "interface": "Cue LED",
            "num_blinks": 4,  # for type = "led_blink"
            "led_duration": 5,
            "display_color": "yellow",
            "display_duration": 10,
        },
        "reward": {
            "delay": 5,  # seconds
            "stochastic_delay": 15,  # seconds, use this delay on some trials
            "stochastic_delay_prob": 0.0,  # probability of delaying reward by "stochastic delay"
            "dispense_prob": 1.0,  # probability of actually dispensing reward
            "feeders": {  # a dict with entries of 'feeder interface': 'number of rewards'
                "Feeder 1": 15,
                "Feeder 2": 15,
            },
        },
        "image_source_id": "top",
    }

    def find_aruco(self):
        aruco_markers, self.aruco_img = detect_aruco(
            session_state["params", "image_source_id"]
        )

        if aruco_markers is not None:
            self.log.info(
                "Found {len(aruco_markers)} aruco markers (see state.session.aruco)."
            )
            session_state["aruco"] = aruco_markers
        else:
            self.log.info("No aruco markers found.")

    def log_next_detection(self):
        self.print_next_detection = True

    def simulate_enter_area(self):
        self.in_out_time = time.time()
        session_state["is_in_area"] = True

    def simulate_leave_area(self):
        self.in_out_time = time.time()
        session_state.update(
            (),
            {
                "is_in_area": False,
                "cooldown_dist": False,
            },
        )

    def reset_rewards_count(self):
        session_state.update(
            (),
            {
                "rewards_count": 0,
                "out_of_rewards": False,
            },
        )

    def on_day_start(self):
        self.bbox_collector.run(self.on_bbox_detection)
        arena.start_trigger()
        video_system.start_record()
        arena.run_command("set", "AC Line 2", [1])
        arena.run_command("set", "AC Line 1", [1])

    def on_day_end(self):
        arena.run_command("set", "AC Line 2", [0])
        arena.run_command("set", "AC Line 1", [0])
        video_system.stop_record()
        arena.stop_trigger()
        self.bbox_collector.end()

    def setup(self):
        self.actions["Find aruco markers"] = {"run": self.find_aruco}
        self.actions["Log next detection"] = {"run": self.log_next_detection}
        self.actions["Simulate enter area"] = {"run": self.simulate_enter_area}
        self.actions["Simulate leave area"] = {"run": self.simulate_leave_area}
        self.actions["Simulate day start"] = {"run": self.on_day_start}
        self.actions["Simulate day end"] = {"run": self.on_day_end}
        self.actions["Reset available rewards"] = {"run": self.reset_rewards_count}

        self.cancel_day_start_sched = schedule.timeofday(
            self.on_day_start, [7, 0], repeats=True
        )
        self.cancel_day_end_sched = schedule.timeofday(
            self.on_day_end, [19, 0], repeats=True
        )

        self.find_aruco()
        self.bbox_collector = BBoxDataCollector(self.log)
        self.print_next_detection = False

        self.reset_rewards_count()

    def release(self):
        #self.cancel_day_end_sched()
        #self.cancel_day_start_sched()
        pass

    def run(self):
        session_state["is_in_area"] = False
        session_state.add_callback("is_in_area", self.is_in_area_changed)

    def run_block(self):
        self.find_reinforced_location()
        self.in_out_time = None
        session_state.update(
            (),
            {
                "cooldown_time": False,
                "cooldown_dist": False,
                "reward_scheduled": False,
            },
        )

        self.cancel_cooldown_time = None
        self.cancel_reward_delay = None
        self.using_stochastic_delay = None

        rl = session_state["reinforced_location"]
        r = exp.get_params()["reinforced_area"]["radius"]
        self.log.info(
            f"Experiment started. Reinforced area at ({rl[0]}, {rl[1]}), radius: {r}."
        )

    def end(self):
        session_state.remove_callback("is_in_area")

    def find_reinforced_location(self):
        params = exp.get_params()
        ra = params["reinforced_area"]
        if "aruco_id" in ra:
            if "aruco" in session_state:
                id = ra["aruco_id"]
                ms = filter(lambda m: m["id"] == id, session_state["aruco"])
                if len(ms) == 1:
                    session_state["reinforced_location"] = ms[0].center
                else:
                    raise Exception(f"Aruco with id {id} was not found.")
            else:
                raise Exception("Can't find aruco markers in session state.")
        elif "location" in ra:
            session_state["reinforced_location"] = ra["location"]
        else:
            raise Exception(
                "Expecting either 'aruco_id' or 'location' params in 'reinforced_location'"
            )

        if self.aruco_img is not None:
            img = np.copy(self.aruco_img)
        else:
            img, _ = image_sources[params["image_source_id"]].get_image()
            img = np.stack((img,) * 3, axis=-1)

        loc = tuple(session_state["reinforced_location"])
        r1 = params["reinforced_area"]["radius"]
        r2 = params["cooldown_radius"]
        img = cv.circle(
            img,
            loc,
            radius=r1,
            color=(0, 255, 0),
            thickness=5,
        )

        img = cv.circle(
            img,
            loc,
            radius=r2,
            color=(255, 0, 0),
            thickness=5,
        )

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        area_image_path = session_state["data_dir"] / f"area_{now_str}.jpg"
        self.log.info(f"Saving area image to {area_image_path}")
        cv.imwrite(str(area_image_path), img)

    def on_bbox_detection(self, det, timestamp):
        if self.print_next_detection:
            self.log.info(f"Head bbox: {det}")
            self.print_next_detection = False

        self.update_is_in_area(det)

    def update_is_in_area(self, det):
        if det is None:
            # later might take part in logic
            return

        centroid = bbox.xyxy_to_centroid(np.array(det))
        was_in_area = session_state["is_in_area"]

        loc = session_state["reinforced_location"]
        dist_to_location = (centroid[0] - loc[0]) ** 2 + (centroid[1] - loc[1]) ** 2
        if session_state["cooldown_dist"] is True:
            if dist_to_location >= exp.get_params()["cooldown_radius"] ** 2:
                self.log.info(
                    "Distance cooldown off. Animal is far enough from reinforced area."
                )
                session_state["cooldown_dist"] = False

        is_in_area = (
            dist_to_location <= exp.get_params()["reinforced_area"]["radius"] ** 2
        )
        if was_in_area != is_in_area:
            self.in_out_time = time.time()
            session_state["is_in_area"] = is_in_area

        return dist_to_location

    def maybe_end_trial(self):
        params = exp.get_params()
        if (
            session_state["is_in_area"]
            and self.in_out_time is not None
            and time.time() - self.in_out_time > params["area_stay_duration"]
        ):
            self.log.info("Trial successful!")
            session_state.update(
                (),
                {
                    "reward_scheduled": True,
                    "cooldown_time": True,
                    "cooldown_dist": True,
                },
            )

            self.cancel_cooldown = schedule.once(
                self.end_time_cooldown, exp.get_params()["cooldown_duration"]
            )

            if session_state["out_of_rewards"] is True:
                self.log.warning("Out of rewards. Can't reward successful trial.")
                return

            interface = params["cue"]["interface"]
            led_dur = params["cue"]["led_duration"]
            num_blinks = params["cue"]["num_blinks"]
            period_time = 1000 * led_dur / num_blinks // 2
            self.log.info(
                f"Starting blinking {interface}. {num_blinks} blinks in {led_dur}s (period {period_time}ms)"
            )
            start_blink(
                interface,
                period_time,
            )

            def stop():
                stop_blink(interface)
                self.log.info("Stopped blinking.")

            schedule.once(stop, led_dur)

            if random.random() <= params["reward"]["stochastic_delay_prob"]:
                delay = params["reward"]["stochastic_delay"]
                self.using_stochastic_delay = True
            else:
                delay = params["reward"]["delay"]
                self.using_stochastic_delay = False

            self.cancel_reward_delay = schedule.once(self.dispense_reward, delay)

    def end_time_cooldown(self):
        session_state["cooldown_time"] = False

    def is_in_area_changed(self, old, new):
        # TODO: make sure area changed continuously
        if not old and new:
            exp.event_logger.log(
                "loclearn/entered_area",
                {
                    "cooldown_time": session_state["cooldown_time"],
                    "cooldown_dist": session_state["cooldown_dist"],
                },
            )
            if session_state["cooldown_time"] or session_state["cooldown_dist"]:
                self.log.info("Animal entered the reinforced area during cooldown.")
            else:
                self.log.info("Animal entered the reinforced area.")
                schedule.once(
                    self.maybe_end_trial, exp.get_params()["area_stay_duration"]
                )

        elif old and not new:
            exp.event_logger.log("loclearn/left_area", None)
            self.log.info("Animal left the reinforced area.")

    def dispense_reward(self):
        if random.random() <= exp.get_params()["reward"]["dispense_prob"]:
            self.log.info("Trial ended. Dispensing reward.")
        else:
            self.log.info("Trial ended. NOT dispensing reward (stochastic reward).")
            exp.next_trial()
            return

        rewards_count = session_state["rewards_count"] + 1

        session_state["reward_scheduled"] = False

        feeders = exp.get_params()["reward"]["feeders"]
        max_reward = sum(feeders.values())
        rewards_sum = 0

        for interface, rewards in feeders.items():
            rewards_sum += rewards

            if rewards_count <= rewards_sum:
                exp.event_logger.log(
                    "dispensing_reward",
                    {
                        "num": rewards_count,
                        "stochastic_delay": self.using_stochastic_delay,
                    },
                )

                self.log.info(
                    f"Dispensing reward #{rewards_count} from feeder {interface} (stochastic_delay={self.using_stochastic_delay})"
                )
                arena.run_command("dispense", interface, None, False)
                break

        if rewards_count >= max_reward:
            session_state["out_of_rewards"] = True
            self.log.info("Out of rewards!")

        session_state["rewards_count"] = rewards_count
        exp.next_trial()


# TODO:
# - better events for the log
