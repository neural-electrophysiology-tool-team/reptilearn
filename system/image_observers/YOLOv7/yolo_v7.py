from video_stream import ImageObserver
import numpy as np
import video_system
import data_log
import experiment as exp


class YOLOv7ImageObserver(ImageObserver):
    default_params = {
        **ImageObserver.default_params,
        "model_config": None,
        "weights_path": None,
        "conf_threshold": 0.6,
        "iou_threshold": 0.4,
    }

    def _init(self):
        from yolov7 import YOLOv7  # Assuming you have a YOLOv7 Python package or module

        super()._init()
        yolo_config = {
            'model_config': self.get_config('model_config'),
            'weights_path': self.get_config('weights_path'),
            'conf_threshold': self.get_config('conf_threshold'),
            'iou_threshold': self.get_config('iou_threshold'),
        }
        self.detector = YOLOv7(**yolo_config)
        self.detector.load_model()

