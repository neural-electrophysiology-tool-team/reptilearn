import PySpin
from video_stream import ImageSource
import re
import multiprocessing as mp
import logging
import time


class FLIRImageSource(ImageSource):
    def __init__(self, cam_id, config, state_root=None, logger=mp.get_logger()):
        super().__init__(cam_id, config["img_shape"], state_root, logger=logger)
        self.cam_id = cam_id
        self.config = config

    def configure_camera(self):
        """Configure camera for trigger mode before acquisition"""
        try:
            self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
            self.cam.ExposureMode.SetValue(PySpin.ExposureMode_Timed)
            self.cam.ExposureTime.SetValue(self.config["exposure"])
                
            if self.config["trigger"] == "ttl":
                self.cam.AcquisitionFrameRateEnable.SetValue(False)
                self.cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
                self.cam.TriggerSelector.SetValue(PySpin.TriggerSelector_FrameStart)
                # self.cam.LineSelector.SetValue(PySpin.LineSelector_Line3)
                # self.cam.LineMode.SetValue(PySpin.LineMode_Input)
                self.cam.TriggerSource.SetValue(PySpin.TriggerSource_Line3)
                # self.cam.TriggerActivation.SetValue(PySpin.TriggerActivation_RisingEdge)
                # self.cam.DeviceLinkThroughputLimit.SetValue(self.get_max_throughput())
                self.cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
                self.cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
            elif self.config["trigger"] == "frame_rate":
                self.cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
                self.cam.AcquisitionFrameRateEnable.SetValue(True)
                self.cam.AcquisitionFrameRate.SetValue(self.config["frame_rate"])
                self.cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)

            self.log.info("Finished Configuration")
            # while True:
            #    self.log.info(self.cam.LineStatus.GetValue())
            #    time.sleep(0.025)

        except PySpin.SpinnakerException as exc:
            self.log.error(f"(configure_images); {exc}")

    def on_begin(self):
        self.system = PySpin.System_GetInstance()
        self.cam_list = self.system.GetCameras()
        filtered = filter_cameras(self.cam_list, self.cam_id)
        if len(filtered) < 1:
            self.log.error(f"Camera {self.cam_id} was not found.")
            return False

        self.cam = filtered[0]
        self.cam.Init()
        self.log.info("Initialized camera.")
        self.configure_camera()

        self.cam.TimestampLatch()
        cam_time = self.cam.TimestampLatchValue.GetValue()  # in nanosecs
        server_time = time.time_ns()
        self.camera_time_delta = server_time - cam_time
        self.log.info(f"Camera time delta: {self.camera_time_delta}")

        self.cam.BeginAcquisition()
        self.image_result = None

        return True

    def acquire_image(self):
        if self.image_result is not None:
            self.image_result.Release()

        self.image_result = self.cam.GetNextImage(5000)
        timestamp = self.image_result.GetTimeStamp() + self.camera_time_delta
        return (self.image_result.GetNDArray(), timestamp)

    def on_finish(self):
        if self.cam.IsStreaming():
            self.cam.EndAcquisition()

        self.cam.DeInit()
        self.cam = None
        self.cam_list.Clear()
        self.system.ReleaseInstance()


def get_device_id(cam) -> str:
    """Get the camera device ID of the cam instance"""
    nodemap_tldevice = cam.GetTLDeviceNodeMap()
    device_id = PySpin.CStringPtr(nodemap_tldevice.GetNode("DeviceID")).GetValue()
    m = re.search(r"SRL_[a-zA-Z\d]{8}", device_id)
    if not m:
        return device_id
    return m[0][4:]


def filter_cameras(cam_list: PySpin.CameraList, cameras_string: str) -> None:
    """Filter cameras according to camera_label, which can be a name or last digits of device ID"""
    current_devices = [get_device_id(cam) for cam in cam_list]
    chosen_devices = []
    for cam_id in cameras_string.split(","):
        if re.match(r"[a-zA-Z]+", cam_id):
            if cam_id and cam_id in current_devices:
                chosen_devices.append(cam_id)
        elif re.match(r"[0-9]+", cam_id):
            chosen_devices.extend(
                [d for d in current_devices if d[-len(cam_id) :] == cam_id]
            )

    def _remove_from_cam_list(device_id):
        devices = [get_device_id(c) for c in cam_list]
        cam_list.RemoveByIndex(devices.index(device_id))

    for d in current_devices:
        if d not in chosen_devices:
            _remove_from_cam_list(d)

    return cam_list


def get_cam_ids():
    system = PySpin.System.GetInstance()
    cameras = system.GetCameras()
    dids = [get_device_id(cam) for cam in cameras]
    cameras.Clear()
    system.ReleaseInstance()
    return dids


def factory_reset(cam_id):
    """not tested"""
    system = PySpin.System.GetInstance()
    cameras = system.GetCameras()
    filtered = filter_cameras(cameras, cam_id)
    if len(filtered) == 0:
        raise Exception(f"Camera {cam_id} was not found.")

    cam = filtered[0]
    cam.FactoryReset.Execute()

    cameras.Clear()
    system.ReleaseInstance()


if __name__ == "__main__":
    """
    logger = mp.log_to_stderr(level=logging.INFO)
    cam_ids = ["20349302", "20349310"]

    fs = [FLIRImageSource(cam_id, {"exposure": 8000}) for cam_id in cam_ids]
    for f in fs:
        f.start()
    for f in fs:
        f.join()
    """
    print(get_cam_ids())
