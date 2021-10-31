import numpy as np
import multiprocessing as mp
import cv2
import time
import rl_logging

# TODO
# - consider using imageio for VideoImageSource


class AcquireException(Exception):
    pass


class ImageSource(mp.Process):
    def __init__(self, src_id, config, state_cursor):
        super().__init__()
        self.image_shape = config["image_shape"]
        self.buf_len = config.get("buf_len", 1)
        self.src_id = src_id

        self.state = state_cursor
        self.state.set_self({"acquiring": False})
        self.config = config

        self.buf_shape = (
            self.image_shape
        )  # currently supports only a single image buffer
        self.buf = mp.Array("B", int(np.prod(self.buf_shape)))
        self.buf_np = np.frombuffer(self.buf.get_obj(), dtype="uint8").reshape(
            self.buf_shape
        )

        self.timestamp = mp.Value("d")
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

    def make_timeout_img(self, shape, text="NO IMAGE"):
        im_h, im_w = shape
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, 5, 10)[0]
        pos = ((im_w - text_size[0]) // 2, (im_h + text_size[1]) // 2)
        img = np.zeros(shape)
        
        cv2.putText(
            img,
            text,
            pos,
            font,
            5,
            (160, 160, 160),
            10,
            cv2.LINE_AA,
        )
        return img

    def stream_gen(self, frame_rate=15):
        self.stop_streaming()

        stop_this_stream_event = mp.Event()
        self.stop_streaming_events.append(stop_this_stream_event)

        timeout_img = self.make_timeout_img(self.image_shape)

        while True:
            t1 = time.time()
            self.stream_obs_event.wait(5)
            if not self.stream_obs_event.is_set():
                # timed out while waiting for image
                yield timeout_img, None
                continue

            self.stream_obs_event.clear()

            if self.end_event.is_set() or stop_this_stream_event.is_set():
                self.stop_streaming_events.remove(stop_this_stream_event)
                break

            yield self.get_image()

            if frame_rate is not None:
                dt = time.time() - t1
                time.sleep(max(1 / frame_rate - dt, 0))

    def run(self):
        self.log = rl_logging.logger_configurer(self.name)

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
                except KeyboardInterrupt:
                    continue

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

            if "acquiring" in self.state:
                self.state["acquiring"] = False

        except Exception:
            self.log.exception("Exception while acquiring images:")
        finally:
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
    def __init__(self, img_src: ImageSource, config: dict = None, state_cursor=None):
        super().__init__()
        self.img_src = img_src
        self.state = state_cursor
        if self.state is not None and config is not None:
            self.config = config

        self.update_event = mp.Event()
        img_src.add_observer_event(self.update_event)

        self.parent_pipe, self.child_pipe = mp.Pipe()

        self.name = f"{type(self).__name__}:{self.img_src.src_id}"

    def start_observing(self, num_frames=None):
        self.parent_pipe.send("start")

    def stop_observing(self):
        self.parent_pipe.send("stop")

    def shutdown(self):
        self.parent_pipe.send("shutdown")

    def run(self):
        self.log = rl_logging.logger_configurer(self.name)

        self.setup()
        cmd = None

        while True:
            try:
                cmd = self.child_pipe.recv()
            except KeyboardInterrupt:
                continue

            if self.img_src.end_event.is_set():
                break

            if cmd == "shutdown":
                self.log.info("Shutting down")
                break

            if cmd == "start":
                self.avg_proc_time = 0
                self.frame_count = 0

                self.on_start()
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
                            self.on_image_update(*self.img_src.get_image())
                            dt = time.time() - t0
                            self.frame_count += 1
                            if self.frame_count == 1:
                                self.avg_proc_time = dt
                            else:
                                self.avg_proc_time = (
                                    self.avg_proc_time * (self.frame_count - 1) + dt
                                ) / self.frame_count
                except Exception:
                    self.log.exception("Exception while observing:")
                finally:
                    try:
                        self.on_stop()
                    except Exception:
                        self.log.exception("Exception while stopping observer:")

    def on_start(self):
        pass

    def on_image_update(self, img, timestamp):
        pass

    def on_stop(self):
        pass

    def setup(self):
        pass

    def release(self):
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

        vcap = cv2.VideoCapture(str(self.video_path))
        if self.is_color:
            image_shape = (
                int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                3,
            )
        else:
            image_shape = (
                int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            )

        vcap.release()

        super().__init__(src_id, image_shape, state_cursor)

    def on_begin(self):
        self.vcap = cv2.VideoCapture(str(self.video_path))
        if self.end_frame is None:
            self.end_frame = self.vcap.get(cv2.CAP_PROP_FRAME_COUNT) - 1
        if self.start_frame != 0:
            self.vcap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)

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
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if self.frame_num >= self.end_frame:
            if self.repeat is False:
                return None, t
            elif self.repeat is True or type(self.repeat) is int:
                self.repeat_count += 1
                if type(self.repeat) is int and self.repeat_count >= self.repeat:
                    self.log.info(f"Done repeating {self.repeat} times.")
                    return None, t
                else:
                    self.vcap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
                    self.frame_num = self.start_frame

        self.frame_num += 1
        self.last_acquire_time = time.time() - t
        return img, t

    def on_finish(self):
        self.vcap.release()
