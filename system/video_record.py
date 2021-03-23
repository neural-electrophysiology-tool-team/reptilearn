import multiprocessing as mp
from pathlib import Path
from threading import Timer
from datetime import datetime
import imageio
import time

import mqtt
import config
from video_stream import ImageSource
from state import state
import rl_logging


# TODO:
# - videowriter should check if the timestamp matches the fps. if delta is about twice the 1/fps, it should repeat the
#   current frame twice, etc.
# - take fps from image source if possible, allow custom fps
# - maybe set trigger pulse len according to video_frame_rate or the other way around.

rec_state = state.get_cursor("video_record")
video_writers = {}
_image_sources = None
_log = None


def init(image_sources, logger):
    global _image_sources, _log
    _log = logger
    _image_sources = image_sources
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

    rec_state.set_self(
        {
            "selected_sources": [ims.src_id for ims in image_sources],
            "ttl_trigger": ttl_trigger,
            "is_recording": False,
            "write_dir": config.videos_dir,
            "filename_prefix": "",
        }
    )

    for w in video_writers.values():
        w.start()


def restore_rec_dir():
    rec_state["write_dir"] = config.videos_dir


def set_selected_sources(src_ids):
    rec_state["selected_sources"] = src_ids


def select_source(src_id):
    if src_id in rec_state["selected_sources"]:
        return

    rec_state.append("selected_sources", src_id)


def unselect_source(src_id):
    rec_state.remove("selected_sources", src_id)


def start_trigger(pulse_len=17, update_state=True):
    if update_state:
        rec_state["ttl_trigger"] = True
    mqtt.client.publish_json("arena/ttl_trigger/start", {"pulse_len": pulse_len})


def stop_trigger(update_state=True):
    if update_state:
        rec_state["ttl_trigger"] = False
    mqtt.client.publish("arena/ttl_trigger/stop")


_do_restore_trigger = False


def start_record(src_ids=None):
    if rec_state["is_recording"] is True:
        return

    global _do_restore_trigger
    if src_ids is None:
        src_ids = rec_state["selected_sources"]

    if len(src_ids) == 0:
        return

    def standby():
        rec_state["is_recording"] = True
        for src_id in src_ids:
            video_writers[src_id].start_writing()

    if rec_state["ttl_trigger"]:
        _do_restore_trigger = True
        stop_trigger(update_state=False)
        Timer(1, start_trigger, kwargs={"update_state": False}).start()

    Timer(0.5, standby).start()


def stop_record(src_ids=None):
    global _do_restore_trigger
    if rec_state["is_recording"] is False:
        return

    if src_ids is None:
        src_ids = rec_state["selected_sources"]

    if len(src_ids) == 0:
        return

    def stop():
        rec_state["is_recording"] = False
        for src_id in src_ids:
            video_writers[src_id].stop_writing()

    if _do_restore_trigger:
        stop_trigger(update_state=False)
        Timer(1, start_trigger, kwargs={"update_state": False}).start()
        _do_restore_trigger = False

    Timer(0.5, stop).start()


def save_image(src_ids=None):
    if src_ids is None:
        src_ids = rec_state["selected_sources"]

    images = [img_src.get_image() for img_src in _image_sources]
    paths = [_get_new_write_path(src_id, "jpg") for src_id in src_ids]
    for p, im, src in zip(paths, images, src_ids):
        _log.info(f"Saved image from {src} to {p}")
        imageio.imwrite(str(p), im[0])


def _get_new_write_path(src_id, file_ext):
    filename_prefix = rec_state["filename_prefix"]
    write_dir = rec_state["write_dir"]

    if len(filename_prefix.strip()) > 0:
        filename_prefix += "_"

    base = (
        filename_prefix + src_id + "_" + datetime.now().strftime("%Y%m%d-%H%M%S") + "."
    )
    return write_dir / (base + file_ext)


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

        vid_path = _get_new_write_path(
            self.img_src.src_id, config.video_record["file_ext"]
        )
        ts_path = _get_new_write_path(self.img_src.src_id, "csv")

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
        self.log = rl_logging.logger_configurer(self.name)
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
