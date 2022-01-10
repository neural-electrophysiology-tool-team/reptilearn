from video_stream import ImageSource
import cv2
import time


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
            config["image_shape"] = (
                int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                3,
            )
        else:
            config["image_shape"] = (
                int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            )

        vcap.release()

        super().__init__(src_id, config, state_cursor)

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
