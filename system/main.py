import multiprocessing as mp
import threading
import logging
import flask
import flask_cors
from flask_socketio import SocketIO, emit
import cv2

import storage
from detector import DetectorImageObserver
from YOLOv4.detector import YOLOv4Detector
import undistort
import image_utils
import state
import experiment
import mqtt
import video_record
import config
from dynamic_loading import instantiate_class

logger = mp.log_to_stderr(logging.INFO)

# initialize state
state.update_state(["image_sources"], {})

image_sources = [
    instantiate_class(
        src_config["class"], src_id, src_config, state_root=["image_sources"]
    )
    for (src_id, src_config) in config.image_sources.items()
]

video_record.init(image_sources)

experiment.init(logger)

"""
def store_detection(det, image_timestamp, detection_timestamp):
    if det is None:
        det = [None] * 5
    det.insert(0, image_timestamp / 1e9)
    storage.insert_bbox_position(db_conn, det)


   
detector_obs = DetectorImageObserver(image_sources[config["detector_source"]],
                                     YOLOv4Detector(conf_thres=0.8, return_neareast_detection=True),
                                     detection_buffer=detection_buffer,
                                     on_detect=store_detection,
                                     buffer_size=20)
"""


# detector_obs.start()

for img_src in image_sources:
    img_src.start()


#### Flask API ####

app = flask.Flask("API")
flask_cors.CORS(app)
app.config["SECRET_KEY"] = "reptilearn"
socketio = SocketIO(app, cors_allowed_origins="*")


# Broadcast state updates
def send_state(old, new):
    logger.info("Emitting state update")
    socketio.emit("state", (old, new))


listen, stop_listening = state.register_listener(send_state)
listen_process = threading.Thread(target=listen)
listen_process.start()


@socketio.on("connect")
def handle_connect():
    logger.info(f"New SocketIO connection. Emitting state")
    emit("state", (None, state.get_state()))


@app.route("/config")
def get_config():
    return flask.jsonify(config)


@app.route("/video_stream/<src_id>")
def video_stream(src_id, width=None, height=None):
    img_src = next(filter(lambda s: s.src_id == src_id, image_sources))
    if img_src.src_id in config.image_sources:
        src_config = config.image_sources[img_src.src_id]
    else:
        src_config = None

    swidth = flask.request.args.get("width")
    width = None if swidth is None else int(swidth)
    sheight = flask.request.args.get("height")
    height = None if sheight is None else int(sheight)
    frame_rate = int(
        flask.request.args.get("frame_rate", default=config.stream_frame_rate)
    )

    if (
        flask.request.args.get("undistort") == "true"
        and src_config is not None
        and "undistort" in src_config
    ):
        oheight, owidth = img_src.image_shape
        undistort_mapping, _, _ = undistort.get_undistort_mapping(
            owidth, oheight, src_config["undistort"]
        )
    else:
        undistort_mapping = None

    def flask_gen():
        gen = img_src.stream_gen(frame_rate)
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


@app.route("/stop_stream/<src_id>")
def stop_stream(src_id):
    img_src = next(filter(lambda s: s.src_id == src_id, image_sources))
    img_src.stop_stream()
    return flask.Response("ok")


@app.route("/video_record/<cmd>")
def request_video_record(cmd):
    src_ids = flask.request.args.getlist("src")
    if len(src_ids) == 0:
        src_ids = None

    if cmd == "start":
        video_record.start_record(src_ids=src_ids)
    elif cmd == "stop":
        video_record.stop_record(src_ids=src_ids)

    return flask.Response("ok")


@app.route("/state")
def route_state():
    return flask.jsonify(state.get_state())


@app.route("/list_experiments")
def route_list_experiments():
    return flask.jsonify(list(experiment.experiments.keys()))


@app.route("/set_experiment/<name>")
def route_set_experiment(name):
    experiment.set_experiment(name)
    return flask.Response("ok")


@app.route("/run_experiment", methods=["POST"])
def route_run_experiment():
    params = flask.request.json

    if not isinstance(params, dict):
        return flask.abort(400, "Invalid params json.")

    try:
        experiment.run(**params)
        return flask.Response("ok")
    except Exception as e:
        flask.abort(500, description=str(e))


@app.route("/end_experiment")
def route_end_experiment():
    try:
        experiment.end()
        return flask.Response("ok")
    except Exception as e:
        flask.abort(500, description=str(e))


@app.route("/")
def root():
    return "ReptiLearn Controller"

"""
@app.after_request
def after_request(response):
    print("After request")
    header = response.headers
    header["Access-Control-Allow-Origin"] = "*"
    header["Access-Control-Allow-Headers"] = "*"
    header["Access-Control-Allow-Methods"] = "POST, GET"
    print(response.data)
    return response
"""

@app.errorhandler(500)
def server_error(e):
    print(str(e))
    return flask.jsonify(error=str(e)), 500


app_log = logging.getLogger("werkzeug")
app_log.setLevel(logging.ERROR)
socketio.run(app, use_reloader=False)

# After flask server is terminated due to KeyboardInterrupt:
logger.info("System shutting down...")
experiment.shutdown()

for img_src in image_sources:
    img_src.join()


state.shutdown()
