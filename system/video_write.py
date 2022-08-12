"""
Writing image data to video files and images.
Author: Tal Eisenberg, 2021
"""
from pathlib import Path
import time
from datetime import datetime
from video_stream import ImageObserver, ImageSource
import imageio
import pickle
import queue
import threading
import json
from image_utils import convert_to_8bit


def get_write_path(
    src_id: str,
    write_dir: Path,
    filename_ext: str,
    filename_prefix: str,
    timestamp=datetime.now(),
) -> Path:
    """
    Return a Path object suitable for writing.

    Args:
    - src_id: The ImageSource id that acquired this image
    - write_dir: The parent directory of the file
    - filename_ext: File suffix after the last dot
    - filename_prefix: File prefix before all other identifiers
    - timestamp: A datetime which will be formatted into the file name
    """
    if len(filename_prefix.strip()) > 0:
        filename_prefix += "_"

    stem = filename_prefix + src_id + "_" + timestamp.strftime("%Y%m%d-%H%M%S") + "."
    return write_dir / (stem + filename_ext)


def save_image(image, src_id, write_dir, filename_prefix, timestamp):
    """
    Save an image to file.
    An `image` with type `uint8` will be saved to a jpeg file.
    Any other array type will be saved to a pickle file.

    Args:
    - image: a 2d numpy.array representing an image
    - timestamp: A datetime which will be formatted into the file name
    - src_id: The ImageSource id that acquired this image
    - write_dir: The parent directory of the file
    - filename_prefix: File prefix before all other identifiers

    """
    dt = datetime.fromtimestamp(timestamp)
    ext = "jpg" if image.dtype == "uint8" else "pickle"
    path = get_write_path(src_id, write_dir, ext, filename_prefix, dt)

    if image.dtype == "uint8":
        imageio.imwrite(str(path), image)
    else:
        with open(path, "wb") as f:
            pickle.dump(image, f)

    return path


class VideoWriter(ImageObserver):
    """
    VideoWriter - a video_stream.ImageObserver that writes image data to video files.

    The VideoWriter has no output and no additional config parameters. It observes a
    single ImageSource and writes its buffer contents whenever the buffer is updated.
    Use `ImageObserver.start_observing()` and `ImageObserver.stop_observing()` to start or stop
    writing the image stream.
    """

    def __init__(
        self,
        config: dict,
        encoding_params,
        frame_rate,
        queue_max_size,
        media_dir,
        file_ext,
        image_source: ImageSource,
        state_store_address: tuple,
        state_store_authkey: str,
        running_state_key="writing",
    ):
        """
        Initialize a VideoWriter.

        Args:
            - encoding_params: A dictionary of video encoding parameters. These are passed to the function imageio.get_writer
                               See available options here: https://imageio.readthedocs.io/en/stable/format_ffmpeg.html
            - frame_rate: Used for setting the video rate and measuring potential missing frames
            - queue_max_size: The max size of the writing queue. If <=0 the queue is inifinite (the default)
            - media_dir: The writer writes to the session directory when there's an open session. Otherwise it will use this directory.
            - file_ext: Video filename suffix after the dot
            - image_source: The observed ImageSource
            - state_store_address, state_store_authkey: Credentials for the state store
            - running_state_key: Uses this key (str) in the state of the observed ImageSource to indicate whether it's currently writing or not.
        """
        self.img_src_id = image_source.id
        self.scaling_8bit = image_source.scaling_8bit
        self.encoding_params = encoding_params
        self.media_dir = media_dir
        self.frame_rate = frame_rate
        self.file_ext = file_ext
        self.queue_max_size = queue_max_size

        super().__init__(
            self.img_src_id + ".writer",
            config,
            image_source,
            state_store_address,
            state_store_authkey,
            ("video", "image_sources", image_source.id),
            running_state_key,
        )

    def _init(self):
        super()._init()

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

        write_dir = self.state.root().get(("session", "data_dir"), self.media_dir)
        filename_prefix = self.state.root().get(
            ("video", "record", "filename_prefix"), ""
        )
        timestamp = datetime.now()
        vid_path: Path = get_write_path(
            self.img_src_id,
            write_dir,
            self.file_ext,
            filename_prefix,
            timestamp,
        )
        ts_path = vid_path.parent / (vid_path.stem + ".csv")
        metadata_path = vid_path.parent / (vid_path.stem + ".json")

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

        with open(str(metadata_path), "w") as f:
            json.dump(
                {
                    "image_source_config": self._img_src_config,
                    "encoding_params": self.encoding_params,
                },
                f,
            )

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
            try:
                self.writer.append_data(img)
            except StopIteration:
                break
            except Exception:
                self.log.exception("Error while writing image to video file:")

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

        avg_frame_rate = 1 / self.avg_frame_time if self.avg_frame_time != 0 else "NaN"
        self.log.info(
            (
                f"Finished writing {self.write_count} frames. "
                + f"Avg. write time: {self.avg_write_time * 1000:.3f}ms, "
                + f"Avg. frame rate: {avg_frame_rate:.3f}fps, "
                + f"Max queued frames: {self.max_queued_items}"
                + s_missed_frames
            )
        )

        self.prev_timestamp = None
        self.writer.close()
        self.ts_file.close()
