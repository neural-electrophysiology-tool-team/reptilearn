import flask
from video_stream import ImageSource
import multiprocessing as mp
import time
import cv2 as cv
import logging
import paho.mqtt.client as mqtt


class API(mp.Process):
    def __init__(
        self,
        img_srcs: [ImageSource],
        video_writer_conns=[],
        config={},
        logger=mp.get_logger(),
    ):
        super().__init__()
        self.img_srcs = img_srcs
        self.config = config
        self.log = logger
        self.img_obs_events = {img_src: mp.Event() for img_src in img_srcs}
        self.name = type(self).__name__

        for img_src in img_srcs:
            img_src.add_observer_event(self.img_obs_events[img_src])

        self.video_writer_conns = video_writer_conns
        self.is_streaming = False

    def on_mqtt_connect(self, client, userdata, flags, rc):
        self.log.info(f"MQTT connected (code {rc})")

    def stream_gen(self, img_src, img_size):
        self.log.log(logging.INFO, "Starting stream")
        img_obs_event = self.img_obs_events[img_src]
        self.is_streaming = True

        while True:
            t1 = time.time()
            img_obs_event.wait()
            img_obs_event.clear()
            if img_src.end_event.is_set():
                break
            if not self.is_streaming:
                self.log.info("Stopping streaming")
                break

            enc_img, timestamp = img_src.get_encoded_image(
                encoding=".webp",
                encode_params=[cv.IMWRITE_WEBP_QUALITY, 20],
                resize=img_size,
            )

            yield (
                b"--frame\r\n"
                b"Content-Type: image/webp\r\n\r\n" + bytearray(enc_img) + b"\r\n\r\n"
            )
            if "stream_fps" in self.config:
                dt = time.time() - t1
                time.sleep(max(1 / self.config["stream_fps"] - dt, 0))

    def run(self):
        app = flask.Flask("API")

        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = self.on_mqtt_connect
        mqtt_client.connect("localhost")

        @app.route("/video_stream/<int:idx>")
        @app.route("/video_stream/<int:idx>/<int:width>/<int:height>")
        def video_stream(idx, width=None, height=None):
            return flask.Response(
                self.stream_gen(self.img_srcs[idx], (width, height)),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )

        @app.route("/stop_stream/")
        def stop_stream():
            self.is_streaming = False
            return flask.Response("ok")

        @app.route("/video_writer/<int:idx>/<cmd>")
        def video_writer(idx, cmd):
            self.video_writer_conns[idx].send(cmd)
            return flask.Response("ok")

        @app.route("/")
        def root():
            return "API Running"

        @app.after_request
        def after_request(response):
            header = response.headers
            header["Access-Control-Allow-Origin"] = "*"
            return response

        app.run(use_reloader=False)
