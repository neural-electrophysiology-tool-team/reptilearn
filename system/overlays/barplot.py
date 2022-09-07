import cv2
from overlay import ObserverOverlay


class BarPlot(ObserverOverlay):
    default_params = {
        **ObserverOverlay.default_params,
        "max_len": 80,
        "scale": 2,
    }

    def obs_apply(self, img, _1, obs_out, _2):
        max_len = self.get_config("max_len")
        scale = self.get_config("scale")
        for idx, bin in enumerate(obs_out):
            line_len = max_len * bin // obs_out.max()
            if line_len > 0:
                cv2.line(
                    img,
                    (1440 - len(obs_out) * scale + idx * scale, 1080),
                    (1440 - len(obs_out) * scale + idx * scale, 1080 - line_len),
                    color=255,
                    thickness=scale,
                )

        return img
