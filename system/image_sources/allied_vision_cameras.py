try:
    import vimba
except Exception:
    pass

from video_stream import ImageSource
import time
import numpy as np

FRAME_QUEUE_SIZE = 10


class AlliedVisionImageSource(ImageSource):
    default_params = {
        **ImageSource.default_params,
        "exposure": 8000,
        "trigger": True,
        "frame_rate": None,
        "cam_id": None,
        "trigger_source": "Line3",
    }

    def configure_camera(self):
        """Configure camera for trigger mode before acquisition"""
        try:
            self.cam.ExposureAuto.set('Off')
            self.cam.ExposureMode.set('Timed')
            self.cam.ExposureTime.set(self.get_config("exposure"))
            self.cam.DeviceLinkThroughputLimit.set(450000000)
            # self.cam.set_pixel_format(vimba.PixelFormat.Mono8)

            if self.get_config("trigger") is True:
                self.cam.AcquisitionFrameRateEnable.set(False)
                self.cam.TriggerMode.set('Off')
                self.cam.TriggerSelector.set('FrameStart')
                self.cam.LineSelector.set(self.get_config("trigger_source"))
                self.cam.LineMode.set('Input')
                self.cam.TriggerSource.set(self.get_config("trigger_source"))

                self.cam.TriggerMode.set('On')
                self.cam.TriggerActivation.set('FallingEdge')

            elif self.get_config("frame_rate") is not None:
                self.cam.TriggerMode.set('Off')
                self.cam.AcquisitionFrameRateEnable.set(True)
                self.cam.AcquisitionFrameRate.set(self.get_config("frame_rate"))
            else:
                self.log.error(
                    "Configuriation error: Expecting either a 'trigger' or 'frame_rate' properties"
                )
                return

            self.cam.AcquisitionMode.set('Continuous')
        except Exception:
            self.log.exception("Exception while configuring camera:")

    def update_time_delta(self):
        self.cam.TimestampLatch.run()
        cam_time = self.cam.TimestampLatchValue.get()  # in nanosecs
        server_time = time.time_ns()
        self.camera_time_delta = (server_time - cam_time) / 1e9
        self.log.info(f"Updated time delta: {self.camera_time_delta}")

    def _on_start(self):
        try:
            self.configure_camera()

            self.update_time_delta()
            # self.cam.start_streaming(self._frame_hander)
            self.log.info("Camera initialized.")
            self.image_result = None

            self.prev_writing = self.state.get("writing", False)

        except vimba.VimbaCameraError:
            self.log.error('Failed to access Camera {}. Abort.'.format(self.get_config("cam_id")))

        return True

    def run(self):
        super(ImageSource, self).run()
        self.system = vimba.Vimba.get_instance()
        with self.system as v:
            cams = v.get_all_cameras()
            print('Cameras found: {}'.format(len(cams)))
            for cam in cams:
                print_camera(cam)
            self.cam = v.get_camera_by_id(self.get_config("cam_id"))
            with self.cam:
                try:
                    if not self._on_start():
                        return
                    self.cam.start_streaming(self._frame_hander)
                    self.state["acquiring"] = True
                    self.stop_event.wait()
                    if self.stop_event.is_set():
                        self.log.info("Shutting down")
                        self.stop_event.clear()
                except KeyboardInterrupt:
                    pass
                finally:
                    if "acquiring" in self.state:
                        self.state["acquiring"] = False
                    self._on_stop()

    def _frame_hander(self, cam, frame):
        try:
            if self.prev_writing is False and self.state.get("writing", False) is True:
                self.update_time_delta()
            self.prev_writing = self.state.get("writing", False)
            timestamp = frame.get_timestamp() / 1e9 + self.camera_time_delta
            img = frame.as_numpy_ndarray()
            self.image_result = img

            with self.buf.get_lock():
                self.timestamp.value = timestamp

                self.buf_np = np.frombuffer(
                    self.buf.get_obj(), dtype=self.buf_dtype
                ).reshape(self.buf_shape)
                np.copyto(self.buf_np, img)

                for obs in self.observer_events:
                    obs.set()
        except Exception:
            self.log.exception("Exception while getting image from alliedVision camera:")
        finally:
            cam.queue_frame(frame)

    def _acquire_image(self):
        raise NotImplemented('')

    def _on_stop(self):
        if self.cam.is_streaming():
            self.cam.stop_streaming()


def factory_reset(cam_id):
    """not tested"""
    raise NotImplemented('No factory reset for allied-vision')


def print_camera(cam):
    print('/// Camera Name   : {}'.format(cam.get_name()))
    print('/// Model Name    : {}'.format(cam.get_model()))
    print('/// Camera ID     : {}'.format(cam.get_id()))
    print('/// Serial Number : {}'.format(cam.get_serial()))
    print('/// Interface ID  : {}\n'.format(cam.get_interface_id()))


if __name__ == "__main__":
    with vimba.Vimba.get_instance() as v:
        cams = v.get_all_cameras()

        print('Cameras found: {}'.format(len(cams)))

        for cam in cams:
            print_camera(cam)
