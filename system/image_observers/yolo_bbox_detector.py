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
            config,
            state_cursor
    ):
        super().__init__(img_src, config, state_cursor)
        if "buffer_size" in config:
            self.buffer_size = config["buffer_size"]
            self.detection_buffer = []
            yolo_config = dict(config)
            del yolo_config["buffer_size"]
        else:
            self.buffer_size = None
            self.detection_buffer = None
            yolo_config = config

        del yolo_config["src_id"]
        del yolo_config["class"]
        self.detector = YOLOv4Detector(**yolo_config)

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

        if self.detection_buffer is not None and self.buffer_size:
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
