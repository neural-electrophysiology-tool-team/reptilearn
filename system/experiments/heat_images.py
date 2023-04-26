import experiment as exp
import arena
import schedule
import video_system


class HeatImagesExperiment(exp.Experiment):
    default_params = {
        "image_src_ids": ["top", "thermal"],
        "video_src_ids": ["thermal"],
        "on_time": 30*60,
        "off_time": 30*60,
        "$inter_trial_interval": 5,
    }

    def run(self):
        self.log.info("Switching heat matrix on")
        arena.run_command("set", "AC Line 1", [1], True)

    def run_trial(self):
        v = exp.session_state["cur_trial"]
        exp.event_logger.log("heat_on", v)
        arena.run_command("set", f"Light{v}", [1], True)
        video_system.capture_images(exp.get_params()["image_src_ids"], f"off_before{v}")
        self.log.info(f"Switching heat lamp {v} on")
        video_system.set_filename_prefix(f"light{v}")
        video_system.start_record(exp.get_params()["video_src_ids"])

        def off_period():
            v = exp.session_state["cur_trial"]
            exp.event_logger.log("heat_off", v)
            video_system.capture_images(exp.get_params()["image_src_ids"], f"light{v}")
            arena.run_command("set", f"Light{v}", [0], True)
            self.log.info(f"Switching heat lamp {v} off")
            schedule.once(exp.next_trial, exp.get_params()["off_time"])

        schedule.once(off_period, exp.get_params()["on_time"])

    def end_trial(self):
        video_system.stop_record()
        video_system.set_filename_prefix(None)

    def end(self):
        self.log.info("Switching heat matrix off")
        arena.run_command("set", "AC Line 1", [0], True)
