import numpy as np


def xywh_to_centroid(xywh):
    """
    :param xywh: bbox numpy array in x, y, width, height.
    :return: numpy array centroids of a bbox array in xywh values (1 or 2 dimensional).
    """

    if len(xywh.shape) == 1:
        x, y, w, h = xywh[:4]
        return np.array([x + w // 2, y + h // 2])

    x1 = xywh[:, 0]
    y1 = xywh[:, 1]
    box_w = xywh[:, 2]
    box_h = xywh[:, 3]

    return np.stack([x1 + (box_w // 2), y1 + (box_h // 2)], axis=1)


def xywh_to_xyxy(xywh):
    """
    Convert a numpy array of bbox coordinates from xywh to xyxy

    :param xywh: bbox numpy array in x, y, width, height
    :return: numpy bbox array in xyxy coordinates - [x1, y1, x2, y2] (top-left, bottom-right corners)
    """
    if len(xywh.shape) == 1:
        x, y, w, h = xywh[:4]
        return np.array([x, y, x + w, y + h])

    x1 = xywh[:, 0]
    y1 = xywh[:, 1]
    box_w = xywh[:, 2]
    box_h = xywh[:, 3]

    return np.stack([x1, y1, x1 + box_w, y1 + box_h], axis=1)


def xyxy_to_xywh(xyxy):
    """
    Convert a numpy array of bbox coordinates from xyxy to xywh

    :param xywh: numpy array bboxes in x, y, width, height format
    :return: numpy array boxes in x,y, width, height format
    """
    if len(xyxy.shape) == 1:
        x1, y1, x2, y2 = xyxy[:4]
        return np.array([x1, y1, (x2 - x1), (y2 - y1)])

    x1 = xyxy[:, 0]
    y1 = xyxy[:, 1]
    x2 = xyxy[:, 2]
    y2 = xyxy[:, 3]

    return np.stack([x1, y1, (x2 - x1), (y2 - y1)], axis=1)


def xyxy_to_centroid(xyxy):
    """
    Convert a numpy array of bbox coordinates (xyxy) to an array of bbox centroids.
    :param xyxy: bbox numpy array in x1, y1, x2, y2
    :return: numpy array of centroids, each row consisting of x, y centroid coordinates.
    """

    if len(xyxy.shape) == 1:
        x1, y1, x2, y2 = xyxy[:4]
        return np.array([(x2 + x1) / 2, (y2 + y1) / 2])

    x1 = xyxy[:, 0]
    y1 = xyxy[:, 0]
    x2 = xyxy[:, 2]
    y2 = xyxy[:, 3]

    return np.stack([(x1 + x2) / 2, (y1 + y2) / 2], axis=1)


def centwh_to_xyxy(centwh):
    """
    Convert a numpy array of bbox coordinates in center x, y, width, height format to xyxy format

    :param centwh: bboxes in xywh format where x, y are the centroid coordinates
    :return: bboxes in xyxy format (top-left, bottom-right corners)
    """
    if type(centwh) == list or len(centwh.shape) == 1:
        cx, cy, w, h = centwh[:4]
        return np.array([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])

    cx = centwh[:, 0]
    cy = centwh[:, 1]
    w = centwh[:, 2]
    h = centwh[:, 3]

    return np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)


def nearest_bbox(bboxes, centroid):
    """
    Return the bbox from the bboxes array whose centroid is closest to the centroid parameter.
    When only one bbox is supplied it is returned.

    :param bboxes: numpy bboxes array.
    :param centroid: numpy array centroid of to compare with.
    :return: A single row from the bboxes array.
    """

    if bboxes.shape[0] > 1:
        detected_centroids = xyxy_to_centroid(bboxes)
        deltas = centroid - detected_centroids
        dists = np.linalg.norm(deltas, axis=1)
        arg_best = np.argmin(dists)
        return bboxes[arg_best]
    else:
        return bboxes[0]


def bbox_iou(box1, box2, x1y1x2y2=True):
    """
    :param box1: numpy array, predicted bounding box
    :param box2: numpy array, ground-truth bounding box
    :param x1y1x2y2: format of the bounding boxes
    :return: float, intersection over union (IoU) of the bboxes
    """
    if not x1y1x2y2:
        # Transform from center and width to exact coordinates
        b1_x1, b1_x2 = box1[:, 0] - box1[:, 2] / 2, box1[:, 0] + box1[:, 2] / 2
        b1_y1, b1_y2 = box1[:, 1] - box1[:, 3] / 2, box1[:, 1] + box1[:, 3] / 2
        b2_x1, b2_x2 = box2[:, 0] - box2[:, 2] / 2, box2[:, 0] + box2[:, 2] / 2
        b2_y1, b2_y2 = box2[:, 1] - box2[:, 3] / 2, box2[:, 1] + box2[:, 3] / 2
    else:
        # Get the coordinates of bounding boxes
        b1_x1, b1_y1, b1_x2, b1_y2 = box1[:, 0], box1[:, 1], box1[:, 2], box1[:, 3]
        b2_x1, b2_y1, b2_x2, b2_y2 = box2[:, 0], box2[:, 1], box2[:, 2], box2[:, 3]

    # get the corrdinates of the intersection rectangle
    inter_rect_x1 = np.max(b1_x1, b2_x1)
    inter_rect_y1 = np.max(b1_y1, b2_y1)
    inter_rect_x2 = np.min(b1_x2, b2_x2)
    inter_rect_y2 = np.min(b1_y2, b2_y2)
    # Intersection area
    inter_area = np.max(inter_rect_x2 - inter_rect_x1 + 1, 0) * np.max(
        inter_rect_y2 - inter_rect_y1 + 1
    )
    # Union Area
    b1_area = (b1_x2 - b1_x1 + 1) * (b1_y2 - b1_y1 + 1)
    b2_area = (b2_x2 - b2_x1 + 1) * (b2_y2 - b2_y1 + 1)

    iou = inter_area / (b1_area + b2_area - inter_area + 1e-16)

    return iou
