import experiment as exp
import mqtt
import data_log
import arena
import schedule
import video_record
import numpy as np
import cv2 as cv
import monitor
import math
import datetime

class SimpleLearnExp(exp.Experiment):
    default_params = {
        "exp_interval": 500,
        "record_exp": True,
        "led_duration": 2,
        "led_blinks": 4,
        "monitor_color": "yellow",
        "monitor_duration": 20,
        "stimulus": "led",
        "num_trials": 7,
    }

    def setup(self):
        self.cur_trial = None
        self.cancel_trials=None
        self.reward_delay=0
        self.stim_cancel=None
        pass

    def run(self, params):
        self.cur_trial = params["num_trials"]
        arena.day_lights(True)
        if params["record_exp"]:  # record start at init
            video_record.start_record()


    def run_trial(self, params):
        self.log.info(
            "Trial "
            + str(params["num_trials"] - self.cur_trial)
            + " started "
            + str(datetime.datetime.now())
        )
        exp.event_logger.log("simple_exp/trial_start", {"Trial": str(params["num_trials"] - self.cur_trial)})
        self.stim()
        self.dispatch_reward()
        self.log.info("run trial procedure finished")

    def stim(self):
        params = exp.get_merged_params()
        if params["stimulus"].lower() == "led":
            self.led_stimulus()
        else:
            self.monitor_stimulus()


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
                topic="monitor/color", payload="black"
            ),
            params.get("monitor_duration", 60),
        )

    def end_trial(self, params):
        self.cur_trial = self.cur_trial - 1
        self.log.info("trial ended")

    def dispatch_reward(self):
        params = exp.get_merged_params()
        if params["stimulus"].lower() == "led":
            self.reward_delay = params["led_duration"] * params["led_blinks"]
        else:
            self.reward_delay= params.get("monitor_duration", 60)
        schedule.once(self.dispatch_reward_actual, self.reward_delay)

    def dispatch_reward_actual(self):
        self.log.info("REWARD SENT")
        arena.dispense_reward()

    def end(self, params):
        if params.get("record_exp", True):
            video_record.stop_record()
        if self.cancel_trials != None:
            self.cancel_trials()

        schedule.cancel_all()
        mqtt.client.publish(topic="monitor/color", payload="black")

        self.log.info("exp ended")

    def period_call(self):
        exp.next_trial()

