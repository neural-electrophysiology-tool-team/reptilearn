import cv2
import time
from overlay import ConfigurableOverlay, ImageOverlay


class TimestampVisualizer(ConfigurableOverlay):
    default_params = {
        **ConfigurableOverlay.default_params,
        "time_format": "%Y-%m-%d %H:%M:%S",
        "color": 255,
    }

    def apply(self, img, timestamp):
        stime = time.strftime(self.get_config("time_format"), time.localtime(timestamp))
        im_h, im_w = img.shape[:2]
        font = cv2.FONT_HERSHEY_PLAIN
        font_scale = 3
        text_size = cv2.getTextSize(stime, font, font_scale, 10)[0]
        while text_size[0] > 0.7 * im_w and font_scale > 0:
            font_scale -= 1
            text_size = cv2.getTextSize(stime, font, font_scale, 10)[0]

        cv2.putText(
            img,
            stime,
            (font_scale * 5, im_h - font_scale * 5),
            fontFace=font,
            fontScale=font_scale,
            color=self.get_config("color"),
            thickness=4,
            lineType=1,
        )
        return img
