import multiprocessing as mp
import logging
import flask
from flir_cameras import FLIRImageSource
from video_stream import VideoImageSource, VideoWriter
from pathlib import Path

logger = mp.log_to_stderr(logging.INFO)

config = {
    "acq_fps": 60,
    "stream_fps": 15,
    "manager_port": 50000,
    "cam_ids": ["20349302", "20349310"],
    "exposure": 8000,
}

state = {}
image_sources = []
video_writers = []

"""
video_path = Path("./feeding4_vid.avi")
image_sources.append(
    VideoImageSource(
        video_path, fps=config["acq_fps"], repeat=True, start_frame=1000, end_frame=2000
    )
)
image_sources.append(
    VideoImageSource(
        video_path, fps=config["acq_fps"], repeat=True, start_frame=2000, end_frame=None
    )
)
"""
for cam_id in config["cam_ids"]:
    image_sources.append(FLIRImageSource(cam_id, config))

for img_src in image_sources:
    video_writers.append(VideoWriter(img_src, fps=60, write_path=Path("videos")))

for w in video_writers:
    w.start()

for img_src in image_sources:
    img_src.start()


app = flask.Flask("API")


@app.route("/config")
def get_config():
    return flask.jsonify(config)


@app.route("/video_stream/<int:idx>")
@app.route("/video_stream/<int:idx>/<int:width>/<int:height>")
def video_stream(idx, width=None, height=None):
    img_src = image_sources[idx]
    return flask.Response(
        img_src.stream_gen((width, height), config["stream_fps"]),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/stop_stream/<int:idx>")
def stop_stream(idx):
    img_src = image_sources[idx]
    img_src.stop_stream()
    return flask.Response("ok")


@app.route("/video_writer/<int:idx>/<cmd>")
def video_writer(idx, cmd):
    vid_writer = video_writers[idx]
    if cmd == "start":
        vid_writer.start_writing()
    if cmd == "stop":
        vid_writer.stop_writing()

    return flask.Response("ok")


@app.route("/list_image_sources")
def list_image_sources():
    return flask.jsonify([s.src_id for s in image_sources])


@app.route("/")
def root():
    return "Reptilearn Controller"


@app.after_request
def after_request(response):
    header = response.headers
    header["Access-Control-Allow-Origin"] = "*"
    return response


app.run(use_reloader=False)
