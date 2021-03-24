from video_stream import ImageObserver, ImageSource
import time
import mqtt
from image_observers.YOLOv4.detector import YOLOv4Detector


class YOLOv4ImageObserver(ImageObserver):
    def __init__(
        self,
        img_src: ImageSource,
        buffer_size=1,
        *yolo_args,
        **yolo_kwargs,
    ):
        super().__init__(img_src)
        self.detector = YOLOv4Detector(*yolo_args, **yolo_kwargs)
        self.detection_buffer = []
        self.buffer_size = buffer_size

    def setup(self):
        self.mqttc = mqtt.MQTTClient()
        self.mqttc.log = self.log
        self.mqttc.connect()
        self.detector.load()

    def on_image_update(self, img, image_timestamp):
        det = self.detector.detect_image(img)
        detection_timestamp = time.time() * 1e9  # in ns

        if self.detection_buffer is not None:
            if len(self.detection_buffer) >= self.buffer_size:
                self.detection_buffer.pop(0)  # slow, but probably ok for small buffers
            self.detection_buffer.append(det)

        self.mqttc.publish_json(
            "reptilearn/pogona_head_bbox",
            {
                "detection": det,
                "image_timestamp": image_timestamp,
                "detection_timestamp": detection_timestamp,
            },
        )

    def release(self):
        self.mqttc.disconnect()
