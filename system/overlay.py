import time
import video_system
import cv2

# TODO:
# - overlay params !important
# - way to choose overlays



class ImageOverlay:
    def apply(self, img, timestamp):
        return img


class BarPlot(ImageOverlay):
    def __init__(self, obs_id) -> None:
        self.obs_id = obs_id

    def apply(self, img, timestamp):
        if self.obs_id in video_system.image_observers:
            output, timestamp = video_system.image_observers[self.obs_id].get_output()
            if timestamp == 0:
                return img

            max_len = 80
            scale = 2
            for idx, bin in enumerate(output):
                line_len = max_len * bin // output.max()
                if line_len > 0:
                    cv2.line(
                        img,
                        (1440 - len(output) * scale + idx * scale, 1080),
                        (1440 - len(output) * scale + idx * scale, 1080 - line_len),
                        color=255,
                        thickness=scale,
                    )

        return img


class TimestampVisualizer(ImageOverlay):
    def apply(self, img, timestamp):
        stime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

        cv2.putText(
            img,
            stime,
            (20, 1060),
            fontFace=cv2.FONT_HERSHEY_PLAIN,
            fontScale=3,
            color=255,
            thickness=4,
            lineType=1,
        )
        return img


overlays = {}


def apply_overlays(img, timestamp, src_id):
    img = img.copy()
    for overlay in overlays[src_id]:
        img = overlay.apply(img, timestamp)
    return img
