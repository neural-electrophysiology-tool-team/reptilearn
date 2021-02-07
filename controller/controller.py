import multiprocessing as mp
import logging
import flask
from flir_cameras import FLIRImageSource
from video_stream import VideoWriter, VideoImageSource
from pathlib import Path
from detector import DetectorImageObserver
from YOLOv4.detector import YOLOv4Detector

logger = mp.log_to_stderr(logging.INFO)

config = {
    "acq_fps": 60,
    "stream_fps": 15,
    "manager_port": 50000,
    "cam_ids": ["20349302", "20349310"],
    "exposure": 8000,
    "detector_source": 0,
}

state_mgr = mp.Manager()
general_state = state_mgr.dict()
img_src_state = state_mgr.dict()
detection_buffer = state_mgr.list()


def get_state():
    state = general_state.copy()
    state["img_srcs"] = img_src_state.copy()
    state["detections"] = list(detection_buffer)
    return state


image_sources = []
video_writers = []

"""
image_sources.append(
    VideoImageSource(
        Path("./feeding4_vid.avi"),
        state_dict=img_src_state,
        start_frame=1000,
        end_frame=2000,
        fps=60,
        repeat=True,
        is_color=False,
    )
)
"""

for cam_id in config["cam_ids"]:
    image_sources.append(FLIRImageSource(cam_id, config, img_src_state))

for img_src in image_sources:
    video_writers.append(VideoWriter(img_src, fps=60, write_path=Path("videos")))

detector_obs = DetectorImageObserver(image_sources[config["detector_source"]],
                                     YOLOv4Detector(conf_thres=0.8, return_neareast_detection=True),
                                     detection_buffer=detection_buffer,
                                     buffer_size=20)

for w in video_writers:
    w.start()

detector_obs.start()

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


@app.route("/video_writer/all/<cmd>")
def video_writer_all(cmd):
    for i in range(len(video_writers)):
        video_writer(i, cmd)

    return flask.Response("ok")


@app.route("/list_image_sources")
def list_image_sources():
    return flask.jsonify([s.src_id for s in image_sources])


@app.route("/state")
def route_state():
    return flask.jsonify(get_state())


@app.route("/")
def root():
    return "Reptilearn Controller"


@app.after_request
def after_request(response):
    header = response.headers
    header["Access-Control-Allow-Origin"] = "*"
    return response


app_log = logging.getLogger("werkzeug")
app_log.setLevel(logging.ERROR)

app.run(use_reloader=False)
