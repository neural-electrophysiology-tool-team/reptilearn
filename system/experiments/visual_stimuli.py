import experiment as exp

from pathlib import Path
import monitor
import arena
import schedule
import random
import video_record


class VisualStimuli(exp.Experiment):
    default_params = {
        "stimuli_duration": 5,  # seconds
        "stimuli_path": "/data/nimrod/stimuli_images",
        "interstimuli_duration": 2,
        "record_video": True,
        "interstimuli_color": "lightgrey",
        "preseq_delay": 3,
    }

    def setup(self):
        arena.turn_touchscreen(True)
        self.actions["Clear screen"] = {"run": self.clear}
        monitor.set_color("lightgrey")

    def clear(self, color=None):
        if color is None:
            color = exp.get_phase_params()["interstimuli_color"]
        self.log.info("Clearing screen.")
        monitor.set_color(color)
        monitor.clear()
        
    def run(self, params):
        self.paths = list(Path(params["stimuli_path"]).rglob("*.jpg")) + list(
            Path(params["stimuli_path"]).rglob("*.JPG")
        )

        random.shuffle(self.paths)
        exp.session_state["image_list"] = self.paths

        self.log.info(f"Loaded {len(self.paths)} images.")

        intervals = [params["preseq_delay"]] + [
            params["stimuli_duration"],
            params["interstimuli_duration"],
        ] * len(self.paths)

        self.cur_index = 0
        self.clear(params["interstimuli_color"])

        self.cancel_sequence = schedule.sequence(self.display_stimuli, intervals)
        video_record.start_record()

    def display_stimuli(self):

        if self.cur_index % 2 == 0:
            img_path = self.paths[self.cur_index // 2]
            monitor.show_image(img_path)
            exp.event_logger.log("show_image", str(img_path))
        else:
            monitor.clear()
            exp.event_logger.log("image_off", None)

        if self.cur_index == len(self.paths) * 2 - 1:
            exp.next_block()

        self.cur_index += 1

    def end(self, params):
        monitor.clear()
        self.cancel_sequence()
        video_record.stop_record()

    def release(self):
        arena.turn_touchscreen(False)
