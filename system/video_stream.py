"""
Streaming image data between processes
Author: Tal Eisenberg, 2021

The following classes use shared memory buffers to generate and process image data in an asynchronous manner using multiple os processes.

- ImageSource: a multiprocessing.Process that writes image data to a shared memory buffer.
- ImageObserver: a multiprocessing.Process that can receive a stream of images from ImageSource objects.
"""
import uuid
import numpy as np
import multiprocessing as mp
import cv2
import time
import threading
import rl_logging
import managed_state
from image_utils import convert_to_8bit


class AcquireException(Exception):
    pass


class ConfigurableProcess(mp.Process):
    """
    a Configurable multiprocessing.Process

    This is the base class of ImageSource and ImageObserver, and takes care of setting default configuration parameters
    as well as accessing them while the process is running. It also sets up a logger that can be accessed from the new process at self.log.

    Adding default configuration parameters in a subclass:

    The default parameters are defined in the class field `default_params`. To add parameters use this pattern:

    ```python
    default_params = {
        **ConfigurableProcess.default_params,  # replace ConfigurableProcess with whatever class your inheriting from
        "additional_param": some_default_value,
        "another_param": another_default_value,
    }
    ```

    Using configuration parameters in a subclass:
    The actual values of the parameters can be accessed using the `get_config(key)` method, where `key` is the parameter name.
    """

    default_params = {
        "class": None,
    }

    def __init__(
        self,
        id: str,
        config: dict,
        state_path: str,
        state_store_address: tuple,
        state_store_authkey: str,
    ):
        super().__init__()
        self.id = id
        self.config = config
        self.logging_configurer = rl_logging.get_logger_configurer()
        self.state_path = state_path
        self.state_store_address = state_store_address
        self.state_store_authkey = state_store_authkey

    def get_config(self, key):
        """
        Return a config value for the supplied `key`. If it doesn't exist, return the default value for `key`.
        """
        if key in self.config:
            return self.config[key]
        elif key in self.__class__.default_params:
            return self.__class__.default_params[key]
        else:
            raise KeyError(f"Unknown config key: {key}")

    def run(self):
        # This code runs on the child process
        self.state = managed_state.Cursor(
            self.state_path,
            address=self.state_store_address,
            authkey=self.state_store_authkey,
        )
        if not self.state.exists(()):
            self.state.set_self({})
        self.log = self.logging_configurer.configure_child(mp.current_process().name)
        self.log.debug("Running...")


class ImageSource(ConfigurableProcess):
    """
    ImageSource - a multiprocessing.Process that writes image data to a shared memory buffer.

    ImageSource parameters (in addition to the "class" param):
    - buf_len: The number of images stored in the buffer.
    - buf_dtype: The data type of each image pixel channel. Currently "uint8" or "uint16" are supported, for unsigned 8-bit
                 integer or unsigned 16-bit integer respectively.
    - image_shape: a tuple with 2 element denoting the shape of each image in the buffer.
    - encoding_config: This parameter is used in video_write.VideoWriter to determine the video encoding parameters (see
                       video_write.VideoWriter documentation)
    - 8bit_scaling: Should be used in case buf_dtype is "uint16". Videos and images can currently only be encoded in 8 bits per pixel
                    channel. This configures the way 16 bit pixel values are scaled to 8 bits. It can be either:
                    - "auto" (str): Scale pixel intensities linearly so that the image minimum becomes 0 and the maximum becomes 255.
                    - "full_range" (str): Linear scaling which maps 0 to 0 and 65535 to 255.
                    - [a, b] (any two-element sequence): Linear scaling which maps a to 0 and b to 255.
    - video_frame_rate: The number of frames per second. Used for setting the speed of recorded videos.
    See documentation of the ConfigurableProcess class for more information on setting default params and runtime parameter access

    To make your own ImageSource subclass override any of the following methods:
    - _acquire_image(self)
    - _on_start(self)
    - _on_stop(self)

    See the documentation of each method for more information.
    """

    default_params = {
        **ConfigurableProcess.default_params,
        "buf_len": 1,
        "buf_dtype": "uint8",
        "image_shape": None,
        "encoding_config": None,
        "8bit_scaling": "full_range",
        "video_frame_rate": None,
    }

    def __init__(
        self,
        id: str,
        config: dict,
        state_store_address: tuple,
        state_store_authkey: str,
    ):
        super().__init__(
            id,
            config,
            ("video", "image_sources", id),
            state_store_address,
            state_store_authkey,
        )

        self.image_shape = self.get_config("image_shape")
        self.buf_len = self.get_config("buf_len")
        self.buf_dtype = self.get_config("buf_dtype")
        self.scaling_8bit = self.get_config("8bit_scaling")

        if self.buf_dtype == "uint8":
            self.buf_type_code = "B"
        elif self.buf_dtype == "uint16":
            self.buf_type_code = "H"
        else:
            raise ValueError(
                f"Unsupported buf_dtype: {self.buf_dtype}. Only uint8 or uint16 are currently supported."
            )

        # currently supports only a single image buffer
        self.buf_shape = self.image_shape
        self.buf = mp.Array(self.buf_type_code, int(np.prod(self.buf_shape)))
        self.buf_np = np.frombuffer(self.buf.get_obj(), dtype=self.buf_dtype).reshape(
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
        self._init()

    def _init(self):
        pass

    def add_observer_event(self, obs: mp.Event):
        self.observer_events.append(obs)

    def remove_observer_event(self, obs: mp.Event):
        self.observer_events.remove(obs)

    def kill(self):
        self.end_event.set()

    def stop_streaming(self):
        for e in self.stop_streaming_events:
            e.set()

    def _make_timeout_img(self, shape, text="NO IMAGE"):
        """
        Return a numpy.array image containing the supplied text

        This image will be yielded by the stream generator (see stream_gen method) when image acquisition times
        out (i.e. _acquire_image doesn't return for a certain timeout duration)
        """
        im_h, im_w = shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 7
        text_size = cv2.getTextSize(text, font, font_scale, 10)[0]
        while text_size[0] > im_w and font_scale > 0:
            font_scale -= 1
            text_size = cv2.getTextSize(text, font, font_scale, 10)[0]

        pos = ((im_w - text_size[0]) // 2, (im_h + text_size[1]) // 2)
        img = np.zeros(shape)

        cv2.putText(
            img,
            text,
            pos,
            font,
            font_scale,
            (160, 160, 160),
            10,
            cv2.LINE_AA,
        )
        return img

    def stream_gen(self, frame_rate=15, scale_to_8bit=False):
        self.stop_streaming()

        stop_this_stream_event = mp.Event()
        self.stop_streaming_events.append(stop_this_stream_event)

        timeout_img = self._make_timeout_img(self.image_shape)

        while True:
            t1 = time.time()
            self.stream_obs_event.wait(5)

            if self.end_event.is_set() or stop_this_stream_event.is_set():
                self.stop_streaming_events.remove(stop_this_stream_event)
                break

            if not self.stream_obs_event.is_set():
                # timed out while waiting for image
                yield timeout_img, None
                continue

            self.stream_obs_event.clear()

            yield self.get_image(scale_to_8bit=scale_to_8bit)

            if frame_rate is not None:
                dt = time.time() - t1
                time.sleep(max(1 / frame_rate - dt, 0))

    def run(self):
        # This code runs on the image source process
        super().run()

        if not self._on_start():
            return

        self.state["acquiring"] = True

        try:
            while True:
                img = None

                try:
                    img, timestamp = self._acquire_image()
                except AcquireException as e:
                    self.log.error(e)
                    break
                except KeyboardInterrupt:
                    img, timestamp = self._acquire_image()
                except Exception:
                    self.log.exception("Error while acquiring image:")

                if self.stop_event.is_set():
                    self.log.info("Shutting down")
                    self.stop_event.clear()
                    break

                if img is None:
                    continue

                with self.buf.get_lock():
                    self.timestamp.value = timestamp

                    self.buf_np = np.frombuffer(
                        self.buf.get_obj(), dtype=self.buf_dtype
                    ).reshape(self.buf_shape)
                    np.copyto(self.buf_np, img)

                    for obs in self.observer_events:
                        obs.set()

            if "acquiring" in self.state:
                self.state["acquiring"] = False

        except Exception:
            self.log.exception("Exception while acquiring images:")
        finally:
            self._on_stop()

        for obs in self.observer_events:
            obs.set()
        self.end_event.set()

    def get_image(self, scale_to_8bit=False):
        """
        Return img, timestamp
        - img: The current data in the image buffer (assuming a single image buffer)
        - timestamp: The timestamp of the current image buffer data in seconds since epoch.
        """
        if scale_to_8bit and self.buf_dtype == "uint16":
            img = convert_to_8bit(self.buf_np, self.scaling_8bit)
        else:
            img = self.buf_np

        return img, self.timestamp.value

    def _acquire_image(self):
        """
        Called when the ImageSource is ready for a new image.

        Return img, timestamp
        - img: Image data as numpy.array. Its shape must be the same as self.image_shape or self.get_config("image_shape")
        - timestamp: The image timestamp in seconds since epoch

        The image source process will stop if the returned img is None or an AcquireException is raised.
        """
        pass

    def _on_start(self):
        """
        Called when the image source process is starting.
        """
        pass

    def _on_stop(self):
        """
        Called when the image source process is shutting down.
        """
        pass


class _ImageObserverInterface:
    def __init__(self, other) -> None:
        self.output_buf = other.output_buf
        self.output_shape = other.output_shape
        self.output_dtype = other.output_dtype
        self.output_timestamp = other.output_timestamp
        self._proc_name = other.name

    def add_listener(self, fn, state: managed_state.Cursor):
        """Add a listener function that's called whenever the observer output changes.

        Args:
        - fn: A function with signature (output, timestamp).
            - output: a reference to the observer's output buffer (on main process)
            - timestamp: The timestamp of the current output data as seconds since epoch

        Return:
        A remove_listener() function to remove this listener

        NOTE: This method should only be called from the main process
        """
        listener_uuid = uuid.uuid4()
        kill_event = threading.Event()
        update_event = state.get_event(self._proc_name, listener_uuid)
        output = np.frombuffer(
            self.output_buf.get_obj(), dtype=self.output_dtype
        ).reshape(self.output_shape)

        def listener():
            while True:
                if update_event.wait(1):
                    fn(output, self.output_timestamp.value)
                    update_event.clear()

                if kill_event.is_set():
                    break

        threading.Thread(target=listener, args=()).start()

        def remove_listener():
            state.remove_event(self._proc_name, listener_uuid)

        return remove_listener


class ImageObserver(ConfigurableProcess):
    """
    ImageObserver - a multiprocessing.Process that can receive a stream of images from ImageSource objects.

    Observer parameters (in addition to the "class" param):
    - src_id: The id of an ImageSource (a key of video_system.image_sources) that will be observed by this observer.
    See documentation of the ConfigurableProcess class for more information on setting default params and runtime parameter access

    The observer can be controlled from the main process by using the following methods:
    - add_listener(fn)
    - start_observing()
    - stop_observing()
    - shutdown()

    To make your own observer override any of the following methods:
    - _on_start(self)
    - _on_image_update(self, img, timestamp)
    - _on_stop(self)
    - _setup(self)
    - _release(self)

    See the documentation of each method for more information.

    Observer output data:
    Each ImageObserver can store output data in a multiprocess output buffer (self.output - a numpy.array).

    To update the buffer, change the contents of self.output while taking care to not reassign the value of self.output.
    For example, do NOT use: ```self.output = np.zeros(some_shape)``` as this will overwrite the field without updating the buffer.
    To make this specific example work use: ```self.output[:] = np.zeros(self.output.shape)```

    Once the buffer is updated, call self._notify_listeners(). This will cause all listener functions to be called with the updated data.

    The buffer size and various options are determined according to the values returned by self.get_buffer_opts() (see method documentation for details).
    This method is called once while the observer is initializing.
    """

    default_params = {
        **ConfigurableProcess.default_params,
        "src_id": None,
    }

    def __init__(
        self,
        id: str,
        config: dict,
        image_source: ImageSource,
        state_store_address: tuple,
        state_store_authkey: str,
        state_path=None,
        running_state_key="observing",
    ):
        if state_path is None:
            state_path = ("video", "image_observers", id)

        super().__init__(
            id, config, state_path, state_store_address, state_store_authkey
        )

        self.update_event = mp.Event()
        image_source.add_observer_event(self.update_event)
        self._img_src_end_event = image_source.end_event
        self._img_src_buf = image_source.buf
        self._img_src_buf_shape = image_source.buf_shape
        self._img_src_buf_dtype = image_source.buf_dtype
        self._img_src_timestamp = image_source.timestamp
        self._img_src_config = image_source.config
        self.image_shape = image_source.image_shape
        self._running_state_key = running_state_key

        atype, asize, shape, dtype = self._get_buffer_opts()
        self.output_buf = mp.Array(atype, asize)
        self.output_shape = shape
        self.output_dtype = dtype
        self.output = np.frombuffer(self.output_buf.get_obj(), dtype=dtype).reshape(
            self.output_shape
        )
        self.output_timestamp = mp.Value("d")  # a double

        self.parent_pipe, self.child_pipe = mp.Pipe()

        self.name = f"{type(self).__name__}:{self.get_config('src_id')}"

        self._init()

    def _init(self):
        pass

    def get_interface(self):
        """
        Should be called from the main process. The returned object can then be accessed from any process
        """

        return _ImageObserverInterface(self)

    def add_listener(self, listener, state):
        """
        Should be called from the main process. To add a listener from another process, pass the object returned by
        get_interface() to the process and call its add_listener() method.
        """

        return self.get_interface().add_listener(listener, state)

    def get_output(self):
        """
        Return:
        - numpy.array: a reference to the observer output buffer.
        - the timestamp of the current output data in seconds since epoch.
        """
        return self.output, self.output_timestamp.value

    def start_observing(self):
        """
        Start processing images from the image source.

        NOTE: Can only be called from the main process
        """
        self.parent_pipe.send("start")

    def stop_observing(self):
        """
        Stop processing images.

        NOTE: Can only be called from the main process
        """
        self.parent_pipe.send("stop")

    def shutdown(self):
        """
        Shutdown the observer and its os process

        NOTE: Can only be called from the main process
        """
        self.parent_pipe.send("shutdown")

    def run(self):
        # This code runs on the observer process
        super().run()

        self.output = np.frombuffer(
            self.output_buf.get_obj(), dtype=self.output_dtype
        ).reshape(self.output_shape)

        self.output_update_events = self.state.get_update_events(self.name)
        on_update_events_changed = self.state.add_events_changed_event(self.name)
        self.state[self._running_state_key] = False

        self._setup()
        cmd = None

        while True:
            try:
                cmd = self.child_pipe.recv()
            except KeyboardInterrupt:
                pass

            if self._img_src_end_event.is_set():
                break

            if on_update_events_changed.is_set():
                on_update_events_changed.clear()
                self.output_update_events = self.state.get_update_events(self.name)

            if cmd == "shutdown":
                self.log.info("Shutting down")
                break

            if cmd == "start":
                self.avg_proc_time = 0
                self.frame_count = 0

                if self.state is not None:
                    self.state[self._running_state_key] = True
                self._on_start()
                self.update_event.clear()

                try:
                    self.log.debug("Started observing...")
                    while True:
                        if self._img_src_end_event.is_set():
                            break

                        if self.child_pipe.poll():
                            cmd = self.child_pipe.recv()
                            if cmd == "stop":
                                break

                        if on_update_events_changed.is_set():
                            on_update_events_changed.clear()
                            self.output_update_events = self.state.get_update_events(
                                self.name
                            )

                        if self.update_event.wait(1):
                            self.update_event.clear()

                            t0 = time.time()
                            img = np.frombuffer(
                                self._img_src_buf.get_obj(),
                                dtype=self._img_src_buf_dtype,
                            ).reshape(self._img_src_buf_shape)
                            timestamp = self._img_src_timestamp.value

                            self.output_timestamp.value = timestamp
                            self._on_image_update(img, timestamp)
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
                            self.state[self._running_state_key] = False
                        self._on_stop()
                        self.log.debug("Stopped observing")
                    except Exception:
                        self.log.exception("Exception while stopping observer:")

    def _notify_listeners(self):
        """
        Notify listeners that the output buffer was updated.
        Should be called by the inheriting class after new data was written to the output buffer.
        """
        for evt in self.output_update_events.values():
            evt.set()

    def _on_start(self):
        """
        Called when the start_observing() method is called.
        """
        pass

    def _on_image_update(self, img, timestamp):
        """
        Called after a new image was written to the image source buffer.

        Args:
        - img: A numpy.array containing the new image data
        - timestamp: The image timestamp in seconds since epoch
        """
        pass

    def _on_stop(self):
        """
        Called when the stop_observing() method is called.
        """
        pass

    def _setup(self):
        """
        Called when the observer process is started.
        """
        pass

    def _release(self):
        """
        Called when the observer process is shutdown.
        """
        pass

    def _get_buffer_opts(self):
        """
        Return the output buffer options for this observer.

        This method should return a tuple (atype, asize, shape, dtype) where:
        - atype (str): The typecode of the multiprocessing.Array used to store the observer output.
                       See: https://docs.python.org/3/library/array.html#module-array
        - asize: int or sequence. size_or_initializer argument of multiprocessing.Array.
                 See: https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Array
        - shape: The shape of the numpy array that is used to represent the output buffer.
        - dtype: The dtype of the output buffer numpy array.
        """
        return "B", 0, 0, "uint8"
