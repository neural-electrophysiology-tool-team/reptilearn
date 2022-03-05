from video_stream import ImageObserver
import numpy as np


class YOLOv4ImageObserver(ImageObserver):
    default_params = {
        **ImageObserver.default_params,
        "cfg_path": None,
        "weights_path": None,
        "meta_path": None,
        "conf_thres": 0.9,
        "nms_thres": 0.6,
    }

    def _init(self):
        from image_observers.YOLOv4.detector import YOLOv4Detector

        super()._init()
        yolo_config = dict(self.config)

        del yolo_config["src_id"]
        del yolo_config["class"]

        self.detector = YOLOv4Detector(**yolo_config, return_neareast_detection=True)

    def setup(self):
        self.detector.load()
        self.log.info(
            f"YOLOv4 detector loaded successfully ({self.detector.model_width}x{self.detector.model_height} cfg: {self.detector.cfg_path} weights: {self.detector.weights_path})."
        )
        self.nan_det = np.empty_like(self.output)
        self.nan_det[:] = np.nan

    def on_start(self):
        self.log.info("Starting object detection.")

    def on_stop(self):
        self.log.info("Stopping object detection.")

    def on_image_update(self, img, _):
        det = self.detector.detect_image(img)

        if det is not None:
            self.output[:] = det
        else:
            self.output[:] = self.nan_det

    def release(self):
        pass
