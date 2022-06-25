import time
from datetime import datetime
from video_stream import ImageObserver, ImageSource
import imageio
import pickle
import queue
import threading
from image_utils import convert_to_8bit


def get_write_path(src_id, rec_state, file_ext, timestamp=datetime.now()):
    filename_prefix = rec_state["filename_prefix"]
    write_dir = rec_state["write_dir"]

    if len(filename_prefix.strip()) > 0:
        filename_prefix += "_"

    base = filename_prefix + src_id + "_" + timestamp.strftime("%Y%m%d-%H%M%S") + "."
    return write_dir / (base + file_ext)


def save_image(image, timestamp, rec_state, prefix):
    dt = datetime.fromtimestamp(timestamp)
    ext = "jpg" if image.dtype == "uint8" else "pickle"
    path = get_write_path(prefix, rec_state, ext, dt)

    if image.dtype == "uint8":
        imageio.imwrite(str(path), image)
    else:
        with open(path, "wb") as f:
            pickle.dump(image, f)

    return path


class VideoWriter(ImageObserver):
    default_params = {
        **ImageObserver.default_params,
        "frame_rate": 60,
        "file_ext": "mp4",
        "encoding_params": {},
        "queue_max_size": 0,
    }

    def __init__(
        self,
        id: str,
        config: dict,
        encoding_params,
        image_source: ImageSource,
        state_store_address: tuple,
        state_store_authkey: str,
        running_state_key="writing",
    ):
        self.img_src_id = image_source.id
        self.scaling_8bit = image_source.scaling_8bit
        self.encoding_params = encoding_params

        super().__init__(
            id,
            config,
            image_source,
            state_store_address,
            state_store_authkey,
            ("video", "image_sources", image_source.id),
            running_state_key,
        )

    def _init(self):
        super()._init()
        self.frame_rate = self.get_config("frame_rate")
        self.file_ext = self.get_config("file_ext")
        self.queue_max_size = self.get_config("queue_max_size")

        if len(self.image_shape) == 3 and self.image_shape[2] == 3:
            self.convert_bgr = True
        else:
            self.convert_bgr = False

        self.prev_timestamp = None  # for missing frames alert
        self.q = None

    def _on_start(self):
        if not self.state["acquiring"]:
            self.log.error("Can't write video. Image source is not acquiring.")
            return

        timestamp = datetime.now()
        vid_path = get_write_path(
            self.img_src_id,
            self.state.root()["video", "record"],
            self.file_ext,
            timestamp,
        )
        ts_path = get_write_path(
            self.img_src_id, self.state.root()["video", "record"], "csv", timestamp
        )

        self.log.info(f"Starting to write video to: {vid_path}")
        self.writer = imageio.get_writer(
            str(vid_path),
            format="FFMPEG",
            mode="I",
            fps=self.frame_rate,
            **self.encoding_params,
        )

        self.ts_file = open(str(ts_path), "w")
        self.ts_file.write("timestamp\n")

        self.q = queue.Queue(self.queue_max_size)
        self.max_queued_items = 0

        self.missed_frames_count = 0
        self.missed_frame_events = 0
        self.prev_timestamp = None
        self.avg_frame_time = float("nan")
        self.frame_count = 0

        self.write_thread = threading.Thread(target=self.write_queue)
        self.write_thread.start()

    def write_queue(self):
        self.write_count = 0
        self.avg_write_time = float("nan")

        while True:
            if self.q.qsize() > self.max_queued_items:
                self.max_queued_items = self.q.qsize()

            item = self.q.get()
            if item is None:
                break

            t0 = time.time()
            img, timestamp = item

            if self.convert_bgr:
                img = img[..., ::-1]

            self.ts_file.write(str(timestamp) + "\n")
            self.writer.append_data(img)

            dt = time.time() - t0
            self.write_count += 1
            if self.write_count == 1:
                self.avg_write_time = dt
            else:
                self.avg_write_time = (
                    self.avg_write_time * (self.write_count - 1) + dt
                ) / self.write_count

            self.q.task_done()

    def _on_image_update(self, img, timestamp):
        if self.prev_timestamp is not None:
            delta = timestamp - self.prev_timestamp

            frame_dur = 1 / self.frame_rate
            missed_frames = int(delta / frame_dur)
            if missed_frames > 1:
                self.missed_frames_count += missed_frames
                self.missed_frame_events += 1

            if self.frame_count == 1:
                self.avg_frame_time = delta
            else:
                self.avg_frame_time = (
                    self.avg_frame_time * (self.frame_count - 1) + delta
                ) / self.frame_count

        self.prev_timestamp = timestamp

        if self._img_src_buf_dtype == "uint16":
            img = convert_to_8bit(img, self.scaling_8bit)

        self.q.put((img, timestamp))

    def _on_stop(self):
        if self.write_thread is not None:
            self.q.put_nowait(None)
            self.write_thread.join()

        if self.missed_frames_count > 0:
            s_missed_frames = (
                f", {self.missed_frames_count} missed frame candidates in "
                + f"{self.missed_frame_events} events."
            )
        else:
            s_missed_frames = "."

        self.log.info(
            (
                f"Finished writing {self.write_count} frames. "
                + f"Avg. write time: {self.avg_write_time * 1000:.3f}ms, "
                + f"Avg. frame rate: {1 / self.avg_frame_time:.3f}fps, "
                + f"Max queued frames: {self.max_queued_items}"
                + s_missed_frames
            )
        )
        self.prev_timestamp = None
        self.writer.close()
        self.ts_file.close()
