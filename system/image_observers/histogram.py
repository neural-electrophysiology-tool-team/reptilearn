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
        hist, _ = np.histogram(img, bins=self.config["bin_count"])
        self._update_output(hist)

    def _get_buffer_opts(self):
        bin_count = self.config["bin_count"]

        if len(self.image_shape) == 3:
            size = bin_count * self.image_shape[-1]
            buf_shape = (self.image_shape[-1], bin_count)
        else:
            size = bin_count
            buf_shape = bin_count

        return "L", size, buf_shape, "long"
