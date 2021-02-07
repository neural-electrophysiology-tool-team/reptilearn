from video_stream import ImageObserver, ImageSource
from collections import deque
import multiprocessing as mp
import time


class Detector:
    def load_detector(self):
        """
        An abstract method that loads the detector into memory. Might run on a different process
        than the class init.
        """
        pass

    def detect_image(self, img):
        """
        An abstract method that runs img through the detector and returns a detections array
        img - Image in a numpy array.

        Return an arbitrary detections object.
        """


class DetectorImageObserver(ImageObserver):
    def __init__(
        self,
        img_src: ImageSource,
        detector: Detector,
        detection_buffer=None,
        on_detect=None,
        buffer_size=1,
        logger=mp.get_logger(),
    ):
        super().__init__(img_src, logger)
        self.detector = detector
        self.detection_buffer = detection_buffer
        self.buffer_size = buffer_size
        self.on_detect = on_detect

    def on_begin(self):
        self.detector.load_detector()

    def on_image_update(self, img, image_timestamp):
        det = self.detector.detect_image(img)
        detection_timestamp = time.time()

        # self.log.info(f"detecting {detection_timestamp}")
        if self.detection_buffer is not None:
            if len(self.detection_buffer) >= self.buffer_size:
                self.detection_buffer.pop(0)  # slow, but probably ok for small buffers
            self.detection_buffer.append(det)
            
        if self.on_detect is not None:
            self.on_detect(det, image_timestamp, detection_timestamp)
