from threading import Timer
from datetime import datetime
import imageio
import queue
import threading

import mqtt
from video_stream import ImageSource, ImageObserver
from state import state


# TODO:
# - videowriter should check if the timestamp matches the fps. if delta is about twice the 1/fps, it should repeat the
#   current frame twice, etc.
# - take fps from image source if possible, allow custom fps
# - maybe set trigger pulse len according to video_frame_rate or the other way around.

rec_state = None
video_writers = {}
_image_sources = None
_log = None
_do_restore_trigger = False


def init(image_sources, logger, config):
    global _image_sources, _log, _config, rec_state
    _config = config
    _log = logger
    _image_sources = image_sources
    rec_state = state.get_cursor("video_record")

    for src_id in image_sources.keys():
        video_writers[src_id] = VideoWriter(
            image_sources[src_id],
            frame_rate=config.video_record["video_frame_rate"],
        )

    ttl_trigger = config.video_record["start_trigger_on_startup"]
    if ttl_trigger:
        start_trigger(update_state=False)
    else:
        stop_trigger(update_state=False)

    rec_state.set_self(
        {
            "selected_sources": [src_id for src_id in image_sources.keys()],
            "ttl_trigger": ttl_trigger,
            "is_recording": False,
            "write_dir": config.media_dir,
            "filename_prefix": "",
        }
    )

    for w in video_writers.values():
        w.start()


def restore_after_experiment():
    rec_state["write_dir"] = _config.media_dir
    rec_state["filename_prefix"] = ""


def set_selected_sources(src_ids):
    rec_state["selected_sources"] = src_ids


def select_source(src_id):
    if src_id in rec_state["selected_sources"]:
        return

    rec_state.append("selected_sources", src_id)


def unselect_source(src_id):
    rec_state.remove("selected_sources", src_id)


def start_trigger(pulse_len=None, update_state=True):
    if pulse_len is None:
        pulse_len = _config.video_record["trigger_interval"]

    if update_state:
        rec_state["ttl_trigger"] = True
    mqtt.client.publish_json("arena/ttl_trigger/start", {"pulse_len": str(pulse_len)})


def stop_trigger(update_state=True):
    if update_state:
        rec_state["ttl_trigger"] = False
    mqtt.client.publish("arena/ttl_trigger/stop")


def start_record(src_ids=None):
    global _do_restore_trigger

    if rec_state["is_recording"] is True:
        return

    if src_ids is None:
        src_ids = rec_state["selected_sources"]

    if len(src_ids) == 0:
        return

    def standby():
        rec_state["is_recording"] = True
        for src_id in src_ids:
            video_writers[src_id].start_observing()

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
            video_writers[src_id].stop_observing()

    if _do_restore_trigger:
        stop_trigger(update_state=False)
        Timer(1, start_trigger, kwargs={"update_state": False}).start()
        _do_restore_trigger = False

    Timer(0.5, stop).start()


def save_image(src_ids=None):
    if src_ids is None:
        src_ids = rec_state["selected_sources"]

    images = [_image_sources[src_id].get_image() for src_id in src_ids]
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


class VideoWriter(ImageObserver):
    def __init__(
        self,
        img_src: ImageSource,
        frame_rate,
        file_ext="mp4",
    ):
        super().__init__(img_src)

        self.frame_rate = frame_rate
        self.file_ext = file_ext
        self.img_src.state["writing"] = False

        self.prev_timestamp = None  # missing frames alert
        self.q = None

    def on_start(self):
        if not self.img_src.state["acquiring"]:
            self.log.error("Can't write video. Image source is not acquiring.")
            return

        vid_path = _get_new_write_path(
            self.img_src.src_id, _config.video_record["file_ext"]
        )
        ts_path = _get_new_write_path(self.img_src.src_id, "csv")

        self.log.info(f"Starting to write video to: {vid_path}")
        self.writer = imageio.get_writer(
            str(vid_path),
            format="FFMPEG",
            mode="I",
            fps=self.frame_rate,
            **_config.video_record["video_encoding"],
        )

        self.ts_file = open(str(ts_path), "w")
        self.ts_file.write("timestamp\n")

        self.img_src.state["writing"] = True
        self.q = queue.Queue()

        self.write_thread = threading.Thread(target=self.write_queue)
        self.write_thread.start()

    def write_queue(self):
        while True:
            item = self.q.get()
            if item is None:
                break
            img, timestamp = item

            self.ts_file.write(str(timestamp) + "\n")
            self.writer.append_data(img)
            self.q.task_done()

    def on_image_update(self, img, timestamp):
        img, timestamp = self.img_src.get_image()

        # missing frames alert
        if self.prev_timestamp is not None:
            delta = timestamp - self.prev_timestamp

            if delta > (1 / self.frame_rate) * 1.5:
                self.log.info(f"Possible missed frame during write (delta={delta*1e3:.6f}ms).")

        self.prev_timestamp = timestamp
        # end missing frames
        self.q.put((img, timestamp))

    def on_stop(self):
        self.img_src.state["writing"] = False
        if self.write_thread is not None:
            self.q.put_nowait(None)
            self.write_thread.join()

        self.log.info(
            f"Finished writing {self.frame_count} frames. Average frame write time: {self.avg_proc_time*1000:.3f}ms"
        )
        self.prev_timestamp = None
        self.writer.close()
        self.ts_file.close()
