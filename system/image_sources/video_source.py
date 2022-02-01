from video_stream import ConfigurableProcess, ImageSource, AcquireException
import cv2
import time


class VideoImageSource(ImageSource):
    """
    VideoImageSource - an image source that reads images from a video file.
    """

    default_params = {
        **ImageSource.default_params,
        "video_path": None,
        "frame_rate": 60,
        "start_frame": 0,
        "end_frame": None,
        "repeat": False,
        "is_color": False,
    }

    def _init(self):

        self.video_path = self.get_config("video_path")
        self.frame_rate = self.get_config("frame_rate")
        self.start_frame = self.get_config("start_frame")
        self.end_frame = self.get_config("end_frame")
        self.repeat = self.get_config("repeat")
        self.is_color = self.get_config("is_color")

        vcap = cv2.VideoCapture(str(self.video_path))
        if self.is_color:
            self.config["image_shape"] = (
                int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                3,
            )
        else:
            self.config["image_shape"] = (
                int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            )

        vcap.release()
        super()._init()

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
