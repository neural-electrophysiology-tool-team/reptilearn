import time
import video_system
import cv2

# TODO:
# - each image source needs own list of transforms
# - transform params !important
# - way to choose transforms
# - maybe should be overlays because observers get the original frame and the overlays just get the transformed frame AND ARE NOT SUPPOSED TO LOOK AT THE IMAGE.


class ImageTransform:
    def apply(self, img, timestamp):
        return img


class BarPlot(ImageTransform):
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


class TimestampVisualizer(ImageTransform):
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


transforms = {
    # "top": [TimestampVisualizer()],
    "right": [TimestampVisualizer()],
    "left": [TimestampVisualizer()],
    "back": [TimestampVisualizer()],
}


def apply_transforms(img, timestamp, src_id):
    img = img.copy()
    for transform in transforms[src_id]:
        img = transform.apply(img, timestamp)
    return img
