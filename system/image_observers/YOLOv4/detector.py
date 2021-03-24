import numpy as np
import cv2 as cv
from ctypes import c_int, pointer
import image_observers.YOLOv4.darknet as darknet
import bbox


class YOLOv4Detector:
    """
    Bounding box detector using the YOLOv4 algorithm, based on the paper
    "YOLOv4: Optimal Speed and Accuracy of Object Detection"
    Code from: https://github.com/AlexeyAB/darknet, including a python wrapper for the C modules.

    The resized image used for the last detection is stored in self.curr_img
    """

    def __init__(
        self,
        cfg_path="image_observers/YOLOv4/yolo4_2306.cfg",
        weights_path="image_observers/YOLOv4/yolo4_gs_best_2306.weights",
        meta_path="image_observers/YOLOv4/obj.data",
        conf_thres=0.9,
        nms_thres=0.6,
        return_neareast_detection=False,
    ):
        """
        Initialize detector.
        :param cfg_path: Path to yolo network configuration file
        :param weights_path: Path to trained network weights
        :param meta_path: Path to yolo metadata file (pretty useless for inference but necessary)
        :param conf_thres: float in (0,1), confidence threshold for bounding box detections
        :param nms_thres: float in (0,1), Non-max suppression threshold. Suppresses multiple detections for the same object.
        :param use_neareast_detection: When true, only the detection nearest to the previous one is returned.
        """
        self.cfg_path = cfg_path
        self.weights_path = weights_path
        self.meta_path = meta_path
        self.conf_thres = conf_thres
        self.nms_thres = nms_thres
        self.return_neareast_detection = return_neareast_detection

    def load(self):
        self.curr_img = None
        self.prev_bbox = None

        self.net = darknet.load_net_custom(
            self.cfg_path.encode("ascii"), self.weights_path.encode("ascii"), 0, 1
        )
        self.meta = darknet.load_meta(self.meta_path.encode("ascii"))
        self.model_width = darknet.lib.network_width(self.net)
        self.model_height = darknet.lib.network_height(self.net)
        print(
            f"YOLOv4 detector loaded successfully ({self.model_width}x{self.model_height}; {self.cfg_path})."
        )

    def detect_image(self, img):
        """
        Bounding box inference on input image

        :param img: numpy array image
        :return: list of detections. Each row is x1, y1, x2, y1, confidence  (top-left and bottom-right corners).
        """

        input_height, input_width = img.shape[:2]

        image = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        image = cv.resize(
            image, (self.model_width, self.model_height), interpolation=cv.INTER_LINEAR
        )
        self.curr_img = image

        # C bindings for Darknet inference
        image, arr = darknet.array_to_image(image)
        num = c_int(0)
        pnum = pointer(num)
        darknet.predict_image(self.net, image)

        dets = darknet.get_network_boxes(
            self.net,
            input_width,
            input_height,
            self.conf_thres,
            self.conf_thres,
            None,
            0,
            pnum,
            0,
        )

        num = pnum[0]
        if self.nms_thres:
            darknet.do_nms_sort(dets, num, self.meta.classes, self.nms_thres)

        # change format of bounding boxes
        res = np.zeros((num, 5))

        for i in range(num):
            b = dets[i].bbox
            res[i] = [
                b.x - b.w / 2,
                b.y - b.h / 2,
                b.x + b.w / 2,
                b.y + b.h / 2,
                dets[i].prob[i],
            ]

        nonzero = res[:, 4] > 0
        res = res[nonzero]

        darknet.free_detections(dets, num)

        if res.shape[0] == 0:
            return []
        
        if self.return_neareast_detection:
            if self.prev_bbox is None:
                self.prev_bbox = res[np.argmax(res[:, 4])]
            else:
                self.prev_bbox = bbox.nearest_bbox(res, bbox.xyxy_to_centroid(self.prev_bbox))
            return self.prev_bbox.tolist()
        else:
            return res.tolist()
