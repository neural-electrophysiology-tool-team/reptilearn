from video_stream import ImageObserver
import numpy as np


class HistogramObserver(ImageObserver):
    """
    An observer that calculates the image histogram for each frame and stores it in the observer output.
    """

    default_params = {
        **ImageObserver.default_params,
        "bin_count": 255,
    }

    def _on_image_update(self, img, timestamp):
        bins = self.config["bin_count"]
        hist, bins = np.histogram(img, bins=bins)
        self._update_output(hist)

    def _get_buffer_opts(self):
        bins = self.config["bin_count"]

        if len(self.image_shape) == 3:
            size = bins * self.image_shape[-1]
            buf_shape = (self.image_shape[-1], bins)
        else:
            size = bins
            buf_shape = bins

        return "L", size, buf_shape, "long"
