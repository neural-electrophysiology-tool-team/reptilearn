import multiprocessing as mp
import threading
from video_stream import ImageObserver, ImageSource
import time
import logging

# import mqtt
from image_observers.YOLOv4.detector import YOLOv4Detector


class YOLOv4ImageObserver(ImageObserver):
    def __init__(
        self,
        img_src: ImageSource,
        buffer_size=None,
        *yolo_args,
        **yolo_kwargs,
    ):
        super().__init__(img_src)
        self.detector = YOLOv4Detector(*yolo_args, **yolo_kwargs)

        if buffer_size is not None:
            self.detection_buffer = []
        else:
            self.detection_buffer = None

        self.buffer_size = buffer_size
        self.det_pipe_parent, self.det_pipe_child = mp.Pipe()
        self.on_detection = None
        self.pipe_thread = threading.Thread(target=self._recv_dets)
        self.pipe_thread.start()

    def _recv_dets(self):
        while True:
            try:
                payload = self.det_pipe_parent.recv()
                if self.on_detection is not None:
                    self.on_detection(payload)
            except KeyboardInterrupt:
                break

            except Exception:
                logging.getLogger("Main").exception(
                    "Exception while receiving detections:"
                )

    def setup(self):
        self.detector.load()
        self.log.info(
            f"YOLOv4 detector loaded successfully ({self.detector.model_width}x{self.detector.model_height} cfg: {self.detector.cfg_path} weights: {self.detector.weights_path})."
        )

    def on_start(self):
        self.log.info("Starting object detection.")

    def on_stop(self):
        self.log.info("Stopping object detection.")

    def on_image_update(self, img, image_timestamp):
        det = self.detector.detect_image(img)
        detection_timestamp = time.time()

        if det is not None:
            det = det.tolist()

        if self.detection_buffer is not None:
            if len(self.detection_buffer) >= self.buffer_size:
                self.detection_buffer.pop(0)  # slow, but probably ok for small buffers
            self.detection_buffer.append(det)

        payload = {
            "detection": det,
            "image_timestamp": image_timestamp,
            "detection_timestamp": detection_timestamp,
        }

        self.det_pipe_child.send(payload)

    def release(self):
        pass
