import multiprocessing as mp
import logging
import flask
import cv2

import storage
from flir_cameras import FLIRImageSource
from video_stream import VideoWriter, VideoImageSource
from pathlib import Path
from detector import DetectorImageObserver
from YOLOv4.detector import YOLOv4Detector
import undistort
import image_utils
from config import config

logger = mp.log_to_stderr(logging.INFO)

state_mgr = mp.Manager()
general_state = state_mgr.dict()
img_src_state = state_mgr.dict()
detection_buffer = state_mgr.list()

db_conn = storage.make_connection()


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
        start_frame=0,
        end_frame=None,
        fps=60,
        repeat=True,
        is_color=False,
    )
)
"""

for cam_id in config["cameras"].keys():
    image_sources.append(
        FLIRImageSource(cam_id, config["cameras"][cam_id], img_src_state)
    )

for img_src in image_sources:
    video_writers.append(VideoWriter(img_src, fps=60, write_path=Path("videos")))


def store_detection(det, image_timestamp, detection_timestamp):
    if det is None:
        det = [None] * 5
    det.insert(0, image_timestamp / 1e9)
    storage.insert_bbox_position(db_conn, det)


"""    
detector_obs = DetectorImageObserver(image_sources[config["detector_source"]],
                                     YOLOv4Detector(conf_thres=0.8, return_neareast_detection=True),
                                     detection_buffer=detection_buffer,
                                     on_detect=store_detection,
                                     buffer_size=20)
"""

for w in video_writers:
    w.start()

# detector_obs.start()

for img_src in image_sources:
    img_src.start()

app = flask.Flask("API")


@app.route("/config")
def get_config():
    return flask.jsonify(config)


@app.route("/video_stream/<int:idx>")
def video_stream(idx, width=None, height=None):
    src_config = list(config["cameras"].values())[idx]
    img_src = image_sources[idx]

    swidth = flask.request.args.get("width")
    width = None if swidth is None else int(swidth)
    sheight = flask.request.args.get("height")
    height = None if sheight is None else int(sheight)
    fps = int(flask.request.args.get("fps", default=config["stream_fps"]))

    if flask.request.args.get("undistort") == "true" and "undistort" in src_config:
        oheight, owidth = src_config["img_shape"]
        undistort_mapping, _, _ = undistort.get_undistort_mapping(
            owidth, oheight, src_config["undistort"]
        )
    else:
        undistort_mapping = None

    def flask_gen():
        gen = img_src.stream_gen(fps)
        while True:
            try:
                img, timestamp = next(gen)

                if undistort_mapping is not None:
                    img = undistort.undistort_image(img, undistort_mapping)

                enc_img = image_utils.encode_image(
                    img,
                    encoding=".webp",
                    encode_params=[cv2.IMWRITE_WEBP_QUALITY, 20],
                    shape=(width, height),
                )

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/webp\r\n\r\n"
                    + bytearray(enc_img)
                    + b"\r\n\r\n"
                )
                
            except StopIteration:
                break

    return flask.Response(
        flask_gen(),
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
    return "ReptiLearn Controller"


@app.after_request
def after_request(response):
    header = response.headers
    header["Access-Control-Allow-Origin"] = "*"
    return response


app_log = logging.getLogger("werkzeug")
app_log.setLevel(logging.ERROR)

app.run(use_reloader=False)
