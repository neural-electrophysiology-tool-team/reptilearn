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
        monitor.change_color("lightgrey")
        arena.turn_touchscreen(True)

    def run(self, params):
        self.paths = (
            list(Path(params["stimuli_path"]).rglob("*.jpg"))
            + list(Path(params["stimuli_path"]).rglob("*.JPG"))
        )

        random.shuffle(self.paths)
        exp.session_state["image_list"] = self.paths

        self.log.info(f"Loaded {len(self.paths)} images.")

        intervals = [params["preseq_delay"]] + [
            params["stimuli_duration"],
            params["interstimuli_duration"],
        ] * len(self.paths)
        
        self.cur_index = 0
        self.color = params["interstimuli_color"]
        monitor.change_color(self.color)
        
        self.cancel_sequence = schedule.sequence(self.display_stimuli, intervals)
        video_record.start_record()

    def display_stimuli(self):

        if self.cur_index % 2 == 0:
            img_path = self.paths[self.cur_index // 2]
            monitor.show_image(img_path)
            exp.event_logger.log("show_image", str(img_path))
        else:
            monitor.change_color(self.color)
            exp.event_logger.log("image_off", None)
            
        if self.cur_index == len(self.paths) * 2 - 1:
            monitor.change_color(self.color)
            exp.next_block()

        self.cur_index += 1

    def end(self, params):
        monitor.change_color(self.color)
        self.cancel_sequence()
        video_record.stop_record()
