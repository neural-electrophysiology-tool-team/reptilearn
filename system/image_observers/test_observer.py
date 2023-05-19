from video_stream import ImageObserver
import numpy as np


class TestObeserver(ImageObserver):
    """An image observer that does nothing except output random integers on each image update."""

    def _on_start(self):
        self.log.info("on_start")

    def _on_image_update(self, img, timestamp):
        self._update_output(np.random.random_integers(64, 128, 64))

    def _on_stop(self):
        self.log.info("on_stop")

    def _setup(self):
        self.log.info("setup")

    def _release(self):
        self.log.info("release")

    def _get_buffer_opts(self):
        return "B", np.arange(64, 128, 1), 64, "uint8"
