import cv2

from overlay import ObserverOverlay, is_point_in_bounds
from bbox import xyxy_to_centroid


class BBoxOverlay(ObserverOverlay):
    default_params = {
        **ObserverOverlay.default_params,
        "show_centroid": True,
        "show_bbox": True,
        "centroid_color": (255, 0, 0),
        "centroid_dot_radius": 4,
        "bbox_color": (0, 255, 0),
        "bbox_line_thickness": 2,
    }

    def obs_apply(self, img, img_timestamp, obs_out, obs_out_timestamp):
        if self.get_config("show_bbox"):
            cv2.rectangle(
                img,
                tuple(obs_out[:2]),
                tuple(obs_out[2:4]),
                self.get_config("bbox_color"),
                self.get_config("bbox_line_thickness"),
            )

        if self.get_config("show_centroid"):
            c = xyxy_to_centroid(obs_out[:4])
            if is_point_in_bounds(c, img):
                cv2.circle(
                    img,
                    center=tuple(c),
                    radius=self.get_config("centroid_dot_radius"),
                    color=self.get_config("centroid_color"),
                    thickness=-1,
                    lineType=cv2.LINE_AA,
                )

        return img
