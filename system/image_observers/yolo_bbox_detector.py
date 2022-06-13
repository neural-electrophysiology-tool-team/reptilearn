from video_stream import ImageObserver
import numpy as np
import video_system
import data_log
import experiment as exp


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

    def _setup(self):
        self.detector.load()
        self.log.info(
            f"YOLOv4 detector loaded successfully ({self.detector.model_width}x{self.detector.model_height} cfg: {self.detector.cfg_path} weights: {self.detector.weights_path})."
        )
        self.nan_det = np.empty_like(self.output)
        self.nan_det[:] = np.nan

    def _on_start(self):
        self.log.info("Starting object detection.")

    def _on_stop(self):
        self.log.info("Stopping object detection.")

    def _on_image_update(self, img, _):
        det = self.detector.detect_image(img)

        if det is not None:
            self.output[:] = det
        else:
            self.output[:] = self.nan_det

        self._notify_listeners()

    def _release(self):
        pass

    def _get_buffer_opts(self):
        return "d", 5, 5, np.double


class BBoxDataCollector:
    def __init__(self):
        self.obs = None
        self.bbox_log = None
        self.remove_listener = None

    def start(self, listener=None, obs_id="head_bbox"):
        if obs_id not in video_system.image_observers:
            raise ValueError(f"Unknown image observer '{obs_id}'")

        self.obs: ImageObserver = video_system.image_observers[obs_id]

        if listener is not None:
            # NOTE: assuming this runs on the main process
            self.remove_listener = self.obs.add_listener(listener, exp.state)

        self.bbox_log = data_log.ObserverLogger(
            self.obs,
            columns=[
                ("time", "timestamptz not null"),
                ("x1", "double precision"),
                ("y1", "double precision"),
                ("x2", "double precision"),
                ("y2", "double precision"),
                ("confidence", "double precision"),
            ],
            csv_path=exp.session_state["data_dir"] / "head_bbox.csv",
            table_name="bbox_position",
            split_csv=True,
        )
        self.bbox_log.start()
        self.obs.start_observing()

    def stop(self):
        if self.obs:
            self.obs.stop_observing()
        if self.bbox_log:
            self.bbox_log.stop()
        if self.remove_listener:
            self.remove_listener()
