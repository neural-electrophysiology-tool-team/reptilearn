import numpy as np
import multiprocessing as mp
import cv2 as cv
import time
import state
from datetime import datetime
from pathlib import Path

# TODO:
# - videowriter should check if the timestamp matches the fps. if delta is about twice the 1/fps, it should repeat the
#   current frame twice, etc.


class AcquireException(Exception):
    pass


class ImageSource(mp.Process):
    def __init__(
        self, src_id, image_shape, state_root=None, buf_len=1, logger=mp.get_logger()
    ):
        super().__init__()
        self.image_shape = image_shape
        self.buf_len = buf_len
        self.log = logger
        self.src_id = src_id

        if state_root is not None:
            self.state_path = state_root + [src_id]
            state.update_state(self.state_path, {
                "streaming": False,
                "acquiring": False
            })

        self.buf_shape = image_shape  # currently supports only a single image buffer
        self.buf = mp.Array("B", int(np.prod(self.buf_shape)))
        self.buf_np = np.frombuffer(self.buf.get_obj(), dtype="uint8").reshape(
            self.buf_shape
        )

        self.timestamp = mp.Value("L")
        self.end_event = mp.Event()  # do we really need two events? v--
        self.stop_event = mp.Event()

        self.observer_events = []
        self.stream_obs_event = mp.Event()
        self.add_observer_event(self.stream_obs_event)
        self.name = f"{type(self).__name__}:{self.src_id}"

    def set_state(self, new_state):
        if self.state_path is not None:
            state.assoc_state(self.state_path, new_state)

    def get_state(self, key):
        return state.get_state_path(self.state_path + [key])

    def add_observer_event(self, obs: mp.Event):
        self.observer_events.append(obs)

    def remove_observer_event(self, obs: mp.Event):
        self.observer_events.remove(obs)

    def stop_stream(self):
        self.set_state({"streaming": False})

    def kill(self):
        self.end_event.set()

    def stream_gen(self, fps=15):
        self.log.info(f"Streaming from {self.src_id}.")
        self.set_state({"streaming": True})

        while True:
            t1 = time.time()
            self.stream_obs_event.wait()
            self.stream_obs_event.clear()

            if self.end_event.is_set():
                self.stop_stream()

            if not self.get_state("streaming"):
                break

            yield self.get_image()
            
            if fps is not None:
                dt = time.time() - t1
                time.sleep(max(1 / fps - dt, 0))

        self.log.info(f"Stopped streaming from {self.src_id}.")
        self.set_state({"streaming": False})

    def run(self):
        if not self.on_begin():
            return
        
        self.set_state({"acquiring": True})
        
        try:
            while True:
                try:
                    img, timestamp = self.acquire_image()
                except AcquireException as e:
                    self.log.error(e)
                    break

                if img is None:
                    break

                if self.stop_event.is_set():
                    self.log.info("Stopping process")
                    self.stop_event.clear()
                    break

                with self.buf.get_lock():
                    self.timestamp.value = timestamp
                    self.buf_np = np.frombuffer(self.buf.get_obj(), dtype="uint8").reshape(
                        self.buf_shape
                    )
                    np.copyto(self.buf_np, img)

                    for obs in self.observer_events:
                        obs.set()

        except KeyboardInterrupt:
            pass
        finally:
            self.set_state({"acquiring": False})
            self.on_finish()
        
        for obs in self.observer_events:
            obs.set()
        self.end_event.set()

    def get_image(self):
        img = np.frombuffer(self.buf.get_obj(), dtype="uint8").reshape(self.buf_shape)
        timestamp = self.timestamp.value
        return img, timestamp

    def acquire_image(self):
        pass

    def on_finish(self):
        pass

    def on_begin(self):
        pass


class ImageObserver(mp.Process):
    def __init__(self, img_src: ImageSource, logger=mp.get_logger()):
        super().__init__()
        self.log = logger
        self.img_src = img_src
        self.update_event = mp.Event()
        img_src.add_observer_event(self.update_event)
        self.name = type(self).__name__

    def run(self):
        self.on_begin()

        try:
            while True:
                if self.img_src.end_event.is_set():
                    self.log.info("End event is set")
                    break

                self.update_event.wait()
                self.update_event.clear()

                img, timestamp = self.img_src.get_image()
                self.on_image_update(img, timestamp)

        except KeyboardInterrupt:
            pass
        finally:
            self.on_finish()
        
    def on_begin(self):
        pass

    def on_image_update(self, img, timestamp):
        pass

    def on_finish(self):
        pass


class VideoImageSource(ImageSource):
    def __init__(
        self,
        video_path: Path,
        state_root=None,
        start_frame=0,
        end_frame=None,
        fps=60,
        repeat=False,
        is_color=True,
        logger=mp.get_logger(),
    ):
        self.video_path = video_path
        self.fps = fps
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.repeat = repeat
        self.is_color = is_color
        
        vcap = cv.VideoCapture(str(video_path))
        if is_color:
            image_shape = (
                int(vcap.get(cv.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv.CAP_PROP_FRAME_WIDTH)),
                3
            )
        else:
            image_shape = (
                int(vcap.get(cv.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv.CAP_PROP_FRAME_WIDTH))
            )
            
        vcap.release()
        src_id = video_path.stem + str(start_frame)
        if end_frame is not None:
            src_id += "_" + str(end_frame)

        super().__init__(src_id, image_shape, state_root, logger=logger)

    def on_begin(self):
        self.vcap = cv.VideoCapture(str(self.video_path))
        if self.end_frame is None:
            self.end_frame = self.vcap.get(cv.CAP_PROP_FRAME_COUNT) - 1
        if self.start_frame != 0:
            self.vcap.set(cv.CAP_PROP_POS_FRAMES, self.start_frame)

        self.frame_num = self.start_frame
        self.repeat_count = 0
        self.last_acquire_time = None
        return True

    def acquire_image(self):
        if self.last_acquire_time is not None:
            time.sleep(max(1 / self.fps - self.last_acquire_time, 0))
        t = time.time()
        ret, img = self.vcap.read()
        if not ret:
            raise AcquireException("Error reading frame")

        if not self.is_color:
            img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
            
        if self.frame_num >= self.end_frame:
            if self.repeat is False:
                return None, t
            elif self.repeat is True or type(self.repeat) is int:
                self.repeat_count += 1
                if type(self.repeat) is int and self.repeat_count >= self.repeat:
                    self.log.info(f"Done repeating {self.repeat} times.")
                    return None, t
                else:
                    self.log.info("Repeating video")
                    self.vcap.set(cv.CAP_PROP_POS_FRAMES, self.start_frame)
                    self.frame_num = self.start_frame

        self.frame_num += 1
        self.last_acquire_time = time.time() - t
        return img, int(t * 1e9)

    def on_finish(self):
        self.vcap.release()


class VideoWriter(mp.Process):
    def __init__(
        self,
        img_src: ImageSource,
        fps,
        write_path=Path("."),
        codec="mp4v",
        file_ext="mp4",
        logger=mp.get_logger(),
    ):
        super().__init__()
        self.codec = codec
        self.fps = fps
        self.img_src = img_src
        self.img_src.set_state({"writing": False})

        self.write_path = write_path
        self.file_ext = file_ext
        self.log = logger
        self.update_event = mp.Event()
        img_src.add_observer_event(self.update_event)

        self.parent_pipe, self.child_pipe = mp.Pipe()
        self.name = f"{type(self).__name__}:{self.img_src.src_id}"

    def start_writing(self, num_frames=None):
        self.parent_pipe.send("start")

    def stop_writing(self):
        self.parent_pipe.send("stop")
        self.img_src.set_state({"writing": False})

    def _get_new_write_paths(self):
        base = (
            self.img_src.src_id + "_" + datetime.now().strftime("%Y%m%d-%H%M%S") + "."
        )
        return (
            self.write_path / (base + self.file_ext),
            self.write_path / (base + "csv"),
        )

    def _begin_writing(self):
        if not self.img_src.get_state("acquiring"):
            self.log.error("Can't write video. Image source is not acquiring.")
            return
            
        vid_path, ts_path = self._get_new_write_paths()
        is_color = len(self.img_src.image_shape) == 3
        self.log.info(f"Starting to write video to: {vid_path}")
        self.writer = cv.VideoWriter(
            str(vid_path),
            cv.VideoWriter_fourcc(*self.codec),
            self.fps,
            tuple(reversed(self.img_src.image_shape[:2])),
            isColor=is_color,
        )
        self.ts_file = open(str(ts_path), "w")
        self.ts_file.write("timestamp\n")

        self.img_src.set_state({"writing": True})

    def _write(self):
        img, timestamp = self.img_src.get_image()

        self.ts_file.write(str(timestamp) + "\n")
        self.writer.write(img)

    def _finish_writing(self):
        self.writer.release()
        self.ts_file.close()

    def run(self):
        cmd = None
        while True:
            try:
                cmd = self.child_pipe.recv()
            except KeyboardInterrupt:
                break
            
            if cmd == "start":
                self._begin_writing()

                try:
                    while True:
                        if self.img_src.end_event.is_set():
                            break
                        if self.child_pipe.poll() and self.child_pipe.recv() == "stop":
                            break
                        if self.update_event.wait(1):
                            self.update_event.clear()
                            self._write()
                            
                except KeyboardInterrupt:
                    break
                finally:
                    self.log.info("Stopped writing.")
                    self._finish_writing()
