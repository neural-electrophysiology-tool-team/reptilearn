import experiment as exp
from experiment import session_state
from video_system import image_sources, capture_images
import arena
import schedule
import video_system
import cv2 as cv
import numpy as np
import time
import datetime
import bbox
import random
from image_observers.yolo_bbox_detector import BBoxDataCollector


class OneDoor(exp.Experiment):
    default_params = {
        "$num_trials": 4,
        "doors": {
            "Door1",
        },
        "image_source_id": "top",
    }

    def switch_ssr(self):
        arena.run_command("toggle", "SSR", None, False)

    def open_doors(self):
        doors = exp.get_params()["doors"]
        for door_interface in doors:
            arena.run_command("open", door_interface, None, False)

    def close_doors(self):
        doors = exp.get_params()["doors"]
        for door_interface in doors:
            arena.run_command("close", "Door1", None, False)

    def setup(self):
        self.actions["Open_Doors"] = {"run": self.open_doors}
        self.actions["Close_Doors"] = {"run": self.close_doors}
        self.actions["Toggle SSR"] = {"run": self.switch_ssr}

    def release(self):
        pass

    def run(self):
        pass

    def end(self):
        pass

    def run_block(self):
        session_state["doors"] = "closed"
        self.close_doors()
        self.log.info(
            f"Block started. Closing Doors."
        )

    def trial_finished(self):
        exp.next_trial()

    # def dispense_reward(self, data={}):
    #     rewards_count = session_state["rewards_count"] + 1
    #     feeders = exp.get_params()["reward"]["feeders"]
    #     max_reward = sum(feeders.values())
    #     rewards_sum = 0
    #
    #     for interface, rewards in feeders.items():
    #         rewards_sum += rewards
    #
    #         if rewards_count <= rewards_sum:
    #             exp.event_logger.log(
    #                 "loclearn/dispensing_reward",
    #                 {
    #                     **data,
    #                     **{
    #                         "num": rewards_count,
    #                     },
    #                 },
    #             )
    #
    #             self.log.info(f"Dispensing reward #{rewards_count} from {interface}")
    #             arena.run_command("dispense", interface, None, False)
    #             break
    #         else:
    #             exp.event_logger.log(
    #                 "loclearn/cannot_dispense_reward",
    #                 {
    #                     **data,
    #                 },
    #             )
    #
    #     if rewards_count >= max_reward:
    #         session_state["out_of_rewards"] = True
    #         self.log.info("Out of rewards!")
    #         exp.event_logger.log("loclearn/out_of_rewards", {})
    #
    #     session_state["rewards_count"] = rewards_count
