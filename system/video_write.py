import time
from datetime import datetime
from state import state
from video_stream import ImageObserver
import video_system
import imageio
import queue
import threading


def get_write_path(src_id, file_ext, timestamp=datetime.now()):
    rec_state = state["video", "record"]
    filename_prefix = rec_state["filename_prefix"]
    write_dir = rec_state["write_dir"]

    if len(filename_prefix.strip()) > 0:
        filename_prefix += "_"

    base = filename_prefix + src_id + "_" + timestamp.strftime("%Y%m%d-%H%M%S") + "."
    return write_dir / (base + file_ext)


def save_image(image, timestamp, prefix):
    dt = datetime.fromtimestamp(timestamp)
    path = get_write_path(prefix, "jpg", dt)
    imageio.imwrite(str(path), image)
    return path


class VideoWriter(ImageObserver):
    default_params = {
        **ImageObserver.default_params,
        "frame_rate": 60,
        "file_ext": "mp4",
        "encoding_params": {},
        "queue_max_size": 0,
    }

    def _init(self):
        super()._init()
        self.frame_rate = self.get_config("frame_rate")
        self.file_ext = self.get_config("file_ext")
        self.encoding_params = video_system._config.video_record["encoding_configs"][self.img_src.get_config("encoding_config")]
        self.queue_max_size = self.get_config("queue_max_size")

        self.img_src.state["writing"] = False

        if len(self.img_src.image_shape) == 3 and self.img_src.image_shape[2] == 3:
            self.convert_bgr = True
        else:
            self.convert_bgr = False

        self.prev_timestamp = None  # for missing frames alert
        self.q = None

    def on_start(self):
        if not self.img_src.state["acquiring"]:
            self.log.error("Can't write video. Image source is not acquiring.")
            return

        timestamp = datetime.now()
        vid_path = get_write_path(self.img_src.id, self.file_ext, timestamp)
        ts_path = get_write_path(self.img_src.id, "csv", timestamp)

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

        self.img_src.state["writing"] = True
        self.q = queue.Queue(self.queue_max_size)
        self.max_queued_items = 0

        self.missed_frames_count = 0
        self.missed_frame_events = 0
        self.prev_timestamp = None

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

    def on_image_update(self, img, timestamp):
        img, timestamp = self.img_src.get_image()

        # missing frames alert
        if self.prev_timestamp is not None:
            delta = timestamp - self.prev_timestamp
            frame_dur = 1 / self.frame_rate
            missed_frames = int(delta / frame_dur)
            if missed_frames > 1:
                self.missed_frames_count += missed_frames
                self.missed_frame_events += 1

        self.prev_timestamp = timestamp
        # end missing frames
        self.q.put((img, timestamp))

    def on_stop(self):
        self.img_src.state["writing"] = False
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

        time_ms = self.avg_write_time * 1000

        self.log.info(
            (
                f"Finished writing {self.write_count} frames. "
                + f"Avg. write time: {time_ms:.3f}ms, "
                + f"Max queued frames: {self.max_queued_items}"
                + s_missed_frames
            )
        )
        self.prev_timestamp = None
        self.writer.close()
        self.ts_file.close()
