import PySpin
from video_stream import ImageSource
import time


class FLIRImageSource(ImageSource):
    default_params = {
        **ImageSource.default_params,
        "exposure": 8000,
        "trigger": True,
        "frame_rate": None,
        "stream_id": 0,
        "acquisition_timeout": 5000,
        "pyspin": {},
        "serial_number": None,
        "trigger_source": "Line3",
        "restart_on_timeout": False,
    }

    def configure_camera(self):
        """Configure camera for trigger mode before acquisition"""
        if "exposure" in self.config:
            try:
                self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                self.cam.ExposureMode.SetValue(PySpin.ExposureMode_Timed)
                self.cam.ExposureTime.SetValue(self.get_config("exposure"))
            except Exception:
                self.log.exception("Exception while configuring camera:")

        try:
            if self.get_config("trigger") is True:
                self.cam.AcquisitionFrameRateEnable.SetValue(False)
                self.cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
                self.cam.TriggerSelector.SetValue(PySpin.TriggerSelector_FrameStart)
                self.cam.TriggerSource.SetValue(
                    getattr(
                        PySpin, "TriggerSource_" + self.get_config("trigger_source")
                    )
                )
                self.cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
                self.cam.TriggerActivation.SetValue(
                    PySpin.TriggerActivation_FallingEdge
                )
            elif self.get_config("frame_rate") is not None:
                self.cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
                self.cam.AcquisitionFrameRateEnable.SetValue(True)
                self.cam.AcquisitionFrameRate.SetValue(self.get_config("frame_rate"))

            self.cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)

            pyspin_config = self.get_config("pyspin")

            node_map = self.cam.GetNodeMap()
            for key in pyspin_config.keys():
                value = pyspin_config[key]
                try:
                    self.set_pyspin_node(node_map, key, value)
                except Exception:
                    self.log.exception("Error while setting pyspin node:")
        except Exception:
            self.log.exception("Exception while configuring camera:")

    def set_pyspin_node(self, node_map, node_name, value):
        # self.log.info(f"Setting {node_name} to {value} ({type(value)})")
        if isinstance(value, int):
            node = PySpin.CIntegerPtr(node_map.GetNode(node_name))
        elif isinstance(value, float):
            node = PySpin.CFloatPtr(node_map.GetNode(node_name))
        elif isinstance(value, bool):
            node = PySpin.CBooleanPtr(node_map.GetNode(node_name))
        elif isinstance(value, str):
            node = PySpin.CEnumerationPtr(node_map.GetNode(node_name))
            if not PySpin.IsAvailable(node):
                node = PySpin.CStringPtr(node_map.GetNode(node_name))
                is_enum = False
            else:
                is_enum = True
        else:
            raise ValueError(f"Invalid value type: {value}")

        if not PySpin.IsAvailable(node):
            raise ValueError(f"Node {node_name} is not available.")
        if not PySpin.IsWritable(node):
            raise ValueError(f"Node {node_name} is not writable.")

        if isinstance(value, str) and is_enum:
            enum_entry = PySpin.CEnumEntryPtr(node.GetEntryByName(value))

            if not PySpin.IsAvailable(enum_entry) or not PySpin.IsReadable(enum_entry):
                raise ValueError(
                    f"Enum entry {value} is unavailable for node {node_name}"
                )
            node.SetIntValue(enum_entry.GetValue())
        else:
            node = value

    def get_pyspin_node(self, node_map, node_name):
        node = node_map.GetNode(node_name)

        if not PySpin.IsAvailable(node) or not PySpin.IsReadable(node):
            raise ValueError(f"Node {node_name} is not available or not readable")

        node_type = _int_type_to_pointer_type[node.GetPrincipalInterfaceType()]
        return node_type(node).GetValue()

    def update_time_delta(self):
        try:
            self.cam.TimestampLatch()
            cam_time = self.cam.TimestampLatchValue.GetValue()  # in nanoseconds
        except Exception:
            cam_time = self.cam.Timestamp.GetValue()

        server_time = time.time_ns()
        self.camera_time_delta = (server_time - cam_time) / 1e9
        self.log.debug(f"Updated time delta: {self.camera_time_delta}")

    def _on_start(self):
        self.restart_requested = False
        try:
            self.system: PySpin.SystemPtr = PySpin.System_GetInstance()
            self.cam_list = self.system.GetCameras()

            sn = str(self.get_config("serial_number"))
            self.cam: PySpin.CameraPtr = self.cam_list.GetBySerial(sn)
            try:
                self.cam.Init()
            except PySpin.SpinnakerException as e:
                if e.errorcode == -1015:
                    self.log.error(f"Camera with serial number {sn} was not found.")
                    return False

            self.configure_camera()

            self.update_time_delta()

            self.cam.BeginAcquisition()

            v = self.system.GetLibraryVersion()
            str_ver = f"{v.major}.{v.minor}.{v.type}.{v.build}"
            self.log.info(f"Camera initialized. Using FLIR Spinnaker SDK {str_ver}")
            self.image_result = None

            self.prev_writing = self.state.get("writing", False)
            return True
        except Exception:
            self.log.exception("Exception while initializing camera:")
            return False

    def _acquire_image(self):
        if self.image_result is not None:
            try:
                self.image_result.Release()
            except PySpin.SpinnakerException:
                pass

        if self.restart_requested:
            self.restart_requested = False
            self._on_stop()
            self._on_start()

        if self.prev_writing is False and self.state.get("writing", False) is True:
            self.update_time_delta()
        self.prev_writing = self.state.get("writing", False)

        if self.cam is None:
            return None, None

        try:
            self.image_result: PySpin.ImagePtr = self.cam.GetNextImage(
                self.get_config("acquisition_timeout"), self.get_config("stream_id")
            )
        except PySpin.SpinnakerException as e:
            if e.errorcode == -1011:
                # Failed waiting for EventData on NEW_BUFFER_DATA
                # This tries to prevent a problem we encountered with Flir A70 (and possibly other GigE cameras) on Ubuntu 20.04.
                # Every 65535*3 images we need to restart acquisition:
                if self.get_config("restart_on_timeout") is not True:
                    return None, None

                is_trigger_on = (
                    self.state.root().get(("video", "record", "ttl_trigger"), False)
                    is True
                )
                if (
                    self.get_config("trigger") is True and is_trigger_on
                ) or self.get_config("trigger") is False:
                    self.log.warn(
                        "Camera stopped responding. Trying to restart camera..."
                    )
                    self.restart_requested = True
                    return None, None
            else:
                self.log.exception("Error while acquiring next image:")
        except Exception:
            self.log.exception("Error while acquiring next image:")
            return None, None

        if self.image_result is None or self.image_result.IsIncomplete():
            return None, None

        timestamp = self.image_result.GetTimeStamp() / 1e9 + self.camera_time_delta

        try:
            img = self.image_result.GetNDArray()
            return img, timestamp
        except Exception:
            self.log.exception("Exception while getting image from flir camera:")
            return None, None

    def _on_stop(self):
        if self.cam is not None:
            try:
                if self.cam.IsStreaming():
                    self.cam.EndAcquisition()
                self.cam.DeInit()
                self.cam = None
            except PySpin.SpinnakerException:
                self.log.Exception("While shutting down camera:")

        self.image_result = None

        if self.cam_list is not None:
            self.cam_list.Clear()
            # self.cam_list = None

        self.system.ReleaseInstance()


# From https://github.com/klecknerlab/simple_pyspin
_int_type_to_pointer_type = {
    PySpin.intfIFloat: PySpin.CFloatPtr,
    PySpin.intfIBoolean: PySpin.CBooleanPtr,
    PySpin.intfIInteger: PySpin.CIntegerPtr,
    PySpin.intfIEnumeration: PySpin.CEnumerationPtr,
    PySpin.intfIString: PySpin.CStringPtr,
}
