import multiprocessing as mp
import threading
from video_stream import ImageObserver
import time
import logging

# import mqtt


class YOLOv4ImageObserver(ImageObserver):
    default_params = {
        **ImageObserver.default_params,
        "buffer_size": None,
        "cfg_path": None,
        "weights_path": None,
        "meta_path": None,
        "conf_thres": 0.9,
        "nms_thres": 0.6,
        "return_neareast_detection": False,
    }

    def _init(self):
        from image_observers.YOLOv4.detector import YOLOv4Detector

        super()._init()
        yolo_config = dict(self.config)

        if self.get_config("buffer_size") is not None:
            self.buffer_size = self.get_config["buffer_size"]
            self.detection_buffer = []
        else:
            self.buffer_size = None
            self.detection_buffer = None

        del yolo_config["buffer_size"]
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
