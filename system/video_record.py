import multiprocessing as mp
import config
from video_stream import ImageSource
from pathlib import Path
import mqtt
from threading import Timer
from datetime import datetime
import imageio
import time
from state import state
import logger
import logging

# TODO:
# - videowriter should check if the timestamp matches the fps. if delta is about twice the 1/fps, it should repeat the
#   current frame twice, etc.
# - take fps from image source if possible, allow custom fps
# - maybe set trigger pulse len according to video_frame_rate or the other way around.

video_writers = {}


def init(image_sources):
    for img_src in image_sources:
        video_writers[img_src.src_id] = VideoWriter(
            img_src,
            frame_rate=config.video_record["video_frame_rate"],
        )

    ttl_trigger = config.video_record["start_trigger_on_startup"]
    if ttl_trigger:
        start_trigger(update_state=False)
    else:
        stop_trigger(update_state=False)

    state["video_record"] = {
        "selected_sources": [ims.src_id for ims in image_sources],
        "ttl_trigger": ttl_trigger,
        "is_recording": False,
        "write_dir": Path("videos"),
        "filename_prefix": "",
    }

    for w in video_writers.values():
        w.start()


def set_selected_sources(src_ids):
    state[("video_record", "selected_sources")] = src_ids


def select_source(src_id):
    selected_sources = state[("video_record", "selected_sources")]
    if src_id in selected_sources:
        return

    selected_sources.append(src_id)
    state[("video_record", "selected_sources")] = selected_sources


def unselect_source(src_id):
    selected_sources = state[("video_record", "selected_sources")]
    if src_id not in selected_sources:
        return

    selected_sources.remove(src_id)
    state[("video_record", "selected_sources")] = selected_sources


def start_trigger(pulse_len=17, update_state=True):
    if update_state:
        state[("video_record", "ttl_trigger")] = True
    mqtt.client.publish_json("arena/ttl_trigger/start", {"pulse_len": pulse_len})


def stop_trigger(update_state=True):
    if update_state:
        state[("video_record", "ttl_trigger")] = False
    mqtt.client.publish("arena/ttl_trigger/stop")


do_restore_trigger = False


def start_record(src_ids=None):
    global do_restore_trigger
    if src_ids is None:
        src_ids = state[("video_record", "selected_sources")]

    if len(src_ids) == 0:
        return

    def standby():
        state[("video_record", "is_recording")] = True
        for src_id in src_ids:
            video_writers[src_id].start_writing()

    if state[("video_record", "ttl_trigger")]:
        do_restore_trigger = True
        stop_trigger(update_state=False)
        Timer(1, start_trigger, kwargs={"update_state": False}).start()

    Timer(0.5, standby).start()


def stop_record(src_ids=None):
    if src_ids is None:
        src_ids = state[("video_record", "selected_sources")]

    if len(src_ids) == 0:
        return

    def stop():
        state[("video_record", "is_recording")] = False
        for src_id in src_ids:
            video_writers[src_id].stop_writing()

    if do_restore_trigger:
        stop_trigger(update_state=False)
        Timer(1, start_trigger, kwargs={"update_state": False}).start()

    Timer(0.5, stop).start()


def _get_new_write_paths(src_id):
    filename_prefix = state[("video_record", "filename_prefix")]
    write_dir = state[("video_record", "write_dir")]
    file_ext = config.video_record["file_ext"]
    if len(filename_prefix.strip()) > 0:
        filename_prefix += "_"

    base = (
        filename_prefix + src_id + "_" + datetime.now().strftime("%Y%m%d-%H%M%S") + "."
    )
    return (
        write_dir / (base + file_ext),
        write_dir / (base + "csv"),
    )


class VideoWriter(mp.Process):
    def __init__(
        self,
        img_src: ImageSource,
        frame_rate,
        file_ext="mp4",
    ):
        super().__init__()
        self.frame_rate = frame_rate
        self.img_src = img_src
        self.img_src.state["writing"] = False

        self.file_ext = file_ext
        self.log = logging.getLogger(__name__)
        self.update_event = mp.Event()
        img_src.add_observer_event(self.update_event)

        self.parent_pipe, self.child_pipe = mp.Pipe()
        self.name = f"{type(self).__name__}:{self.img_src.src_id}"

    def start_writing(self, num_frames=None):
        self.parent_pipe.send("start")

    def stop_writing(self):
        self.parent_pipe.send("stop")
        self.img_src.state["writing"] = False

    def _begin_writing(self):
        if not self.img_src.state["acquiring"]:
            self.log.error("Can't write video. Image source is not acquiring.")
            return

        vid_path, ts_path = _get_new_write_paths(self.img_src.src_id)

        self.log.info(f"Starting to write video to: {vid_path}")
        self.writer = imageio.get_writer(
            str(vid_path),
            format="FFMPEG",
            mode="I",
            fps=self.frame_rate,
            **config.video_record["video_encoding"],
        )

        self.ts_file = open(str(ts_path), "w")
        self.ts_file.write("timestamp\n")

        self.img_src.state["writing"] = True

    def _write(self):
        img, timestamp = self.img_src.get_image()

        self.ts_file.write(str(timestamp) + "\n")
        self.writer.append_data(img)

    def _finish_writing(self):
        self.writer.close()
        self.ts_file.close()

    def run(self):
        logger.logger_configurer(__name__)
        cmd = None

        while True:
            try:
                cmd = self.child_pipe.recv()
            except KeyboardInterrupt:
                break

            if cmd == "start":
                self.avg_write_time = 0
                self.frame_count = 0

                self._begin_writing()
                self.update_event.clear()

                try:
                    while True:
                        if self.img_src.end_event.is_set():
                            break
                        if self.child_pipe.poll() and self.child_pipe.recv() == "stop":
                            break
                        if self.update_event.wait(1):
                            self.update_event.clear()
                            t0 = time.time()
                            self._write()
                            dt = time.time() - t0
                            self.frame_count += 1
                            if self.frame_count == 1:
                                self.avg_write_time = dt
                            else:
                                self.avg_write_time = (
                                    self.avg_write_time * (self.frame_count - 1) + dt
                                ) / self.frame_count
                except KeyboardInterrupt:
                    break
                finally:
                    self.log.info(
                        f"Finished writing {self.frame_count} frames. Average frame write time: {self.avg_write_time*1000:.3f}ms"
                    )
                    self._finish_writing()
