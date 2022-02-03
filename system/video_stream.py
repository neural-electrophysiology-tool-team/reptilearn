import uuid
import numpy as np
import multiprocessing as mp
import cv2
import time
import rl_logging
import state
import video_system
import threading


class AcquireException(Exception):
    pass


class ConfigurableProcess(mp.Process):
    default_params = {
        "class": None,
    }

    def __init__(self, id: str, config: dict, state_cursor: state.Cursor):
        super().__init__()
        self.id = id
        self.state = state_cursor
        self.config = config

        self._init()

    def get_config(self, key):
        if key in self.config:
            return self.config[key]
        elif key in self.__class__.default_params:
            return self.__class__.default_params[key]
        else:
            raise ValueError(f"Unknown config key: {key}")

    def run(self):
        self.log = rl_logging.logger_configurer(self.name)

    def _init(self):
        pass


class ImageSource(ConfigurableProcess):
    """
    ImageSource - a multiprocessing.Process that writes image data to a shared memory buffer.
    """

    default_params = {
        **ConfigurableProcess.default_params,
        "buf_len": 1,
        "image_shape": None,
        "encoding_config": None,
    }

    def _init(self):
        self.image_shape = self.get_config("image_shape")
        self.buf_len = self.get_config("buf_len")
        self.state.set_self({"acquiring": False})

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
        self.name = f"{type(self).__name__}:{self.id}"

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
        im_h, im_w = shape[:2]
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
        super().run()

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
        return self.buf_np, self.timestamp.value

    def acquire_image(self):
        pass

    def on_finish(self):
        pass

    def on_begin(self):
        pass


class ImageObserver(ConfigurableProcess):
    """
    ImageObserver - a multiprocessing.Process that can receive a stream of images from ImageSource objects.
    """

    default_params = {
        **ConfigurableProcess.default_params,
        "src_id": None,
    }

    def _init(self):
        """
        Initialize the observer. Called by ConfigurableProcess.__init__()
        """
        self.img_src = video_system.image_sources[self.get_config("src_id")]
        self.update_event = mp.Event()
        self.img_src.add_observer_event(self.update_event)

        if self.state is not None:
            self.state.set_self({"observing": False})

        atype, asize, shape, dtype = self.get_buffer_opts()
        self.output_buf = mp.Array(atype, asize)
        self.output_shape = shape
        self.output_dtype = dtype
        self.output = np.frombuffer(self.output_buf.get_obj(), dtype=dtype).reshape(
            self.output_shape
        )
        self.output_timestamp = mp.Value("d")  # a double

        self.parent_pipe, self.child_pipe = mp.Pipe()

        self.name = f"{type(self).__name__}:{self.img_src.id}"

    def add_listener(self, fn):
        """Can only be called from the main process"""
        print("Adding listener")
        listener_uuid = uuid.uuid4()
        update_event = state._mgr.Event()
        kill_event = threading.Event()
        self.parent_pipe.send(["add", update_event, listener_uuid])

        def listener():
            print("Starting listener")
            while True:
                if update_event.wait(1):
                    print("Received update notification")
                    fn(self.output, self.output_timestamp.value)
                    update_event.clear()

                if kill_event.is_set():
                    print("Killing listener")
                    break

        threading.Thread(target=listener, args=()).start()

        def remove_listener():
            print("Removing listener")
            self.parent_pipe.send(["remove", listener_uuid])

        return remove_listener

    def get_output(self):
        return self.output, self.output_timestamp.value
        
    def start_observing(self):
        """Can only be called from the main process"""
        self.parent_pipe.send("start")

    def stop_observing(self):
        """Can only be called from the main process"""
        self.parent_pipe.send("stop")

    def shutdown(self):
        """Can only be called from the main process"""
        self.parent_pipe.send("shutdown")

    def run(self):
        super().run()

        self.output = np.frombuffer(self.output_buf.get_obj(), dtype=self.output_dtype).reshape(
            self.output_shape
        )

        self.output_update_events = {}

        self.setup()
        cmd = None

        while True:
            try:
                cmd = self.child_pipe.recv()
            except KeyboardInterrupt:
                continue

            if self.img_src.end_event.is_set():
                break

            if isinstance(cmd, list):
                if cmd[0] == 'add':
                    self.log.info(f"Added update event: {cmd[2]}")
                    self.output_update_events[cmd[2]] = cmd[1]
                elif cmd[0] == 'remove':
                    self.log.info(f"Removing update event: {cmd[1]}")
                    del self.output_update_events[cmd[1]]

            if cmd == "shutdown":
                self.log.info("Shutting down")
                break

            if cmd == "start":
                self.avg_proc_time = 0
                self.frame_count = 0

                if self.state is not None:
                    self.state["observing"] = True
                self.on_start()
                self.update_event.clear()

                try:
                    while True:
                        if self.img_src.end_event.is_set():
                            break

                        if self.child_pipe.poll():
                            cmd = self.child_pipe.recv()
                            if cmd == "stop":
                                break
                            elif isinstance(cmd, list):
                                if cmd[0] == 'add':
                                    self.log.info(f"Added update event: {cmd[2]}")
                                    self.output_update_events[cmd[2]] = cmd[1]
                                elif cmd[0] == 'remove':
                                    self.log.info(f"Removing update event: {cmd[1]}")
                                    del self.output_update_events[cmd[1]]

                        if self.update_event.wait(1):
                            self.update_event.clear()

                            t0 = time.time()
                            img, timestamp = self.img_src.get_image()
                            self.output_timestamp.value = timestamp
                            self.on_image_update(img, timestamp)
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
                        if self.state is not None:
                            self.state["observing"] = False
                        self.on_stop()
                    except Exception:
                        self.log.exception("Exception while stopping observer:")

    def notify_listeners(self):
        for evt in self.output_update_events.values():
            evt.set()

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

    def get_buffer_opts(self):
        return "B", 0, 0, "uint8"
