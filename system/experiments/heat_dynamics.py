import experiment as exp
import arena
import schedule
import video_system


class HeatImagesExperiment(exp.Experiment):
    default_params = {
        "image_src_ids": ["top", "thermal"],
        "video_src_ids": ["thermal"],
        "on_time": 30 * 60,
        "off_time": 30 * 60,
        "lamp_idx": 4,
    }

    def values_changed(self, _, timestamp):
        v = exp.state['arena', 'values', 'Temp', 1]
        exp.event_logger.log("temp", {"ts": timestamp, "temp": v})

    def run(self):
        self.log.info("Switching heat matrix on")
        arena.run_command("set", "AC Line 1", [1], True)
        exp.state.add_callback(("arena", "timestamp"), self.values_changed)

    def run_trial(self):
        v = exp.get_params()["lamp_idx"]
        exp.event_logger.log("heat_on", v)
        arena.run_command("set", f"Light{v}", [1], True)
        video_system.capture_images(exp.get_params()["image_src_ids"], f"off_before{v}")
        self.log.info(f"Switching heat lamp {v} on")
        video_system.set_filename_prefix(f"lamp{v}")
        video_system.start_record(exp.get_params()["video_src_ids"])

        def off_period():
            exp.event_logger.log("heat_off", v)
            video_system.capture_images(exp.get_params()["image_src_ids"], f"lamp{v}")
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
        exp.state.remove_callback(("arena", "timestamp"))
