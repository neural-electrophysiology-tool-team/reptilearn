import numpy as np
import multiprocessing as mp
import cv2 as cv
import time
import logger
import logging

# TODO
# - consider using imageio for VideoImageSource


class AcquireException(Exception):
    pass


class ImageSource(mp.Process):
    def __init__(self, src_id, image_shape, state_cursor, buf_len=1):
        super().__init__()
        self.image_shape = image_shape
        self.buf_len = buf_len
        self.log = logging.getLogger(__name__)
        self.src_id = src_id

        self.state = state_cursor
        self.state.set_self({"acquiring": False})

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
        self.stop_streaming_events = []
        self.add_observer_event(self.stream_obs_event)
        self.name = f"{type(self).__name__}:{self.src_id}"

    def add_observer_event(self, obs: mp.Event):
        self.observer_events.append(obs)

    def remove_observer_event(self, obs: mp.Event):
        self.observer_events.remove(obs)

    def kill(self):
        self.end_event.set()

    def stop_streaming(self):
        for e in self.stop_streaming_events:
            e.set()

    def stream_gen(self, frame_rate=15):
        self.log.info(f"Streaming from {self.src_id}.")

        self.stop_streaming()

        stop_this_stream_event = mp.Event()
        self.stop_streaming_events.append(stop_this_stream_event)

        while True:
            t1 = time.time()
            self.stream_obs_event.wait()
            self.stream_obs_event.clear()

            if self.end_event.is_set() or stop_this_stream_event.is_set():
                self.stop_streaming_events.remove(stop_this_stream_event)
                break

            yield self.get_image()

            if frame_rate is not None:
                dt = time.time() - t1
                time.sleep(max(1 / frame_rate - dt, 0))

        self.log.info(f"Stopped streaming from {self.src_id}.")

    def run(self):
        logger.logger_configurer(__name__)

        if not self.on_begin():
            return

        self.state["acquiring"] = True

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
                    self.buf_np = np.frombuffer(
                        self.buf.get_obj(), dtype="uint8"
                    ).reshape(self.buf_shape)
                    np.copyto(self.buf_np, img)

                    for obs in self.observer_events:
                        obs.set()

        except KeyboardInterrupt:
            pass
        finally:
            self.state["acquiring"] = False
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
    def __init__(self, img_src: ImageSource):
        super().__init__()
        self.log = logging.getLogger(__name__)
        self.img_src = img_src
        self.update_event = mp.Event()
        img_src.add_observer_event(self.update_event)
        self.name = type(self).__name__

    def run(self):
        logger.logger_configurer(__name__)
        self.on_begin()

        try:
            while True:
                if self.img_src.end_event.is_set():
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
    def __init__(self, src_id, config, state_cursor=None):
        self.video_path = config["video_path"]
        self.frame_rate = config.get("frame_rate", 60)
        self.start_frame = config.get("start_frame", 0)
        self.end_frame = config.get("end_frame", None)
        self.repeat = config.get("repeat", False)
        self.is_color = config.get("is_color", False)
        self.src_id = src_id

        vcap = cv.VideoCapture(str(self.video_path))
        if self.is_color:
            image_shape = (
                int(vcap.get(cv.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv.CAP_PROP_FRAME_WIDTH)),
                3,
            )
        else:
            image_shape = (
                int(vcap.get(cv.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv.CAP_PROP_FRAME_WIDTH)),
            )

        vcap.release()

        super().__init__(src_id, image_shape, state_cursor)

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
            time.sleep(max(1 / self.frame_rate - self.last_acquire_time, 0))
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
                    self.vcap.set(cv.CAP_PROP_POS_FRAMES, self.start_frame)
                    self.frame_num = self.start_frame

        self.frame_num += 1
        self.last_acquire_time = time.time() - t
        return img, int(t * 1e9)

    def on_finish(self):
        self.vcap.release()
