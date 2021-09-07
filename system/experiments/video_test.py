import video_record
import experiment as exp
import arena
import monitor
import pandas as pd
import schedule
from state import state


class VideoPlayExperiment(exp.Experiment):
    default_params = {
        "vid_path": "/data/amit/videos/headbobbing1.mp4",
        "background_color": "black",
        "record_video": True,
        "block_duration": None,
    }

    def setup(self):
        arena.turn_touchscreen(True)
        monitor.on_playback_end(self.playback_ended)
        color = exp.session_state["params"]["background_color"]
        self.actions["Set background"] = {"run": lambda: monitor.set_color(color)}
        
    def run(self, params):
        monitor.set_color(params["background_color"])
        if params["record_video"]:
            video_record.start_record()

    def run_block(self, params):
        self.log.info("Playing video...")
        if len(params["vid_path"]) > 0:
            monitor.play_video(params["vid_path"])
        if params["block_duration"] is not None:
            schedule.once(exp.next_block, params["block_duration"])

    def end_block(self, params):
        monitor.stop_video()

    def end(self, params):
        if params["record_video"]:
            video_record.stop_record()

    def release(self):
        arena.turn_touchscreen(False)
        monitor.unsubscribe_playback_end()

    def playback_ended(self, timestamps):
        csv_path = exp.session_state["data_dir"] / "video_timestamps.csv"
        self.log.info(f"Video playback finished. Saving timestamps to: {csv_path}")
        df = pd.DataFrame(data=timestamps, columns=["frame", "time"])
        df.to_csv(csv_path, index=False)
        if exp.get_phase_params()["block_duration"] is None:
            exp.next_block()
