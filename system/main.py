import threading
import rl_logging
import logging
import flask
import flask_cors
from flask_socketio import SocketIO, emit
import cv2
import json
from pathlib import Path
from collections import Sequence
import sys
import mqtt
import arena
import schedule
import undistort
import image_utils
from state import state
import state as state_mod
import experiment
import video_record
import config
from dynamic_loading import instantiate_class


app = flask.Flask("API")
flask_cors.CORS(app)
app.config["SECRET_KEY"] = "reptilearn"
socketio = SocketIO(app, cors_allowed_origins="*")


# Setup Logging

class SocketIOHandler(logging.Handler):
    def emit(self, record):
        socketio.emit("log", self.format(record))


socketio_handler = SocketIOHandler()
socketio_handler.setFormatter(rl_logging.formatter)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(rl_logging.formatter)
# h = logging.handlers.RotatingFileHandler("mptest.log", "a", 300, 10)

log = rl_logging.init((socketio_handler, stderr_handler))

app_log = logging.getLogger("werkzeug")
app_log.addHandler(socketio_handler)
app_log.setLevel(logging.WARNING)
app.logger.addHandler(socketio_handler)
app.logger.setLevel(logging.WARNING)


# initialize state
state["image_sources"] = {}

image_sources = {
    src_id: instantiate_class(
        src_config["class"],
        src_id,
        src_config,
        state_cursor=state.get_cursor(("image_sources", src_id)),
    )
    for (src_id, src_config) in config.image_sources.items()
}

image_observers = [
    instantiate_class(
        obs_config["class"], image_sources[obs_config["src_id"]], **obs_config["args"]
    )
    for obs_config in config.image_observers
]

mqtt.init(log)
arena.init(log)
video_record.init(image_sources.values(), log)
experiment.init(log)

for img_obs in image_observers:
    img_obs.start()

for img_src in image_sources.values():
    img_src.start()


#### Flask API ####


def convert_for_json(v):
    if hasattr(v, "tolist"):
        return v.tolist()
    if isinstance(v, Path):
        return str(v)
    raise TypeError(v)


# Broadcast state updates
def send_state(old, new):
    # logger.info("Emitting state update")
    old_json = json.dumps(old, default=convert_for_json)
    new_json = json.dumps(new, default=convert_for_json)
    socketio.emit("state", (old_json, new_json))


state_listen, stop_state_emitter = state_mod.register_listener(send_state)
state_emitter_process = threading.Thread(target=state_listen)
state_emitter_process.start()


@socketio.on("connect")
def handle_connect():
    log.info("New SocketIO connection. Emitting state")
    blob = json.dumps(state.get_self(), default=convert_for_json)
    emit("state", (None, blob))


@app.route("/config/<attribute>")
def route_config(attribute):
    return flask.Response(
        json.dumps(getattr(config, attribute), default=convert_for_json),
        mimetype="application/json",
    )


@app.route("/video_stream/<src_id>")
def route_video_stream(src_id, width=None, height=None):
    img_src = image_sources[src_id]
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
def route_stop_stream(src_id):
    img_src = image_sources[src_id]
    img_src.stop_streaming()
    return flask.Response("ok")


@app.route("/state")
def route_state():
    return flask.jsonify(state.get_self())


@app.route("/experiment/list")
def route_experiment_list():
    return flask.jsonify(list(experiment.experiment_specs.keys()))


@app.route("/experiment/refresh_list")
def route_experiment_refresh_list():
    experiment.refresh_experiment_list()
    return route_experiment_list()


@app.route("/experiment/set/<name>")
def route_experiment_set(name):
    if name == "None":
        name = None
    experiment.set_experiment(name)
    return flask.Response("ok")


@app.route("/experiment/default_params")
def route_experiment_default_params():
    if experiment.cur_experiment is None:
        return flask.jsonify(None)
    return flask.jsonify(
        {
            "params": experiment.cur_experiment.default_params,
            "blocks": experiment.cur_experiment.default_blocks,
        }
    )


@app.route("/experiment/run", methods=["POST"])
def route_experiment_run():
    params = flask.request.json["params"]

    if not isinstance(params, dict):
        return flask.abort(400, "Invalid params json.")

    blocks = flask.request.json.get("blocks", [])
    exp_id = flask.request.json["id"]
    
    try:
        experiment.run(exp_id, params, blocks)
        return flask.Response("ok")
    except Exception as e:
        log.exception("Exception while running experiment")
        flask.abort(500, e)


@app.route("/experiment/end")
def route_experiment_end():
    try:
        experiment.end()
        return flask.Response("ok")
    except Exception as e:
        log.exception("Exception while ending experiment.")
        flask.abort(500, e)


@app.route("/experiment/next_block")
def route_experiment_next_block():
    try:
        experiment.next_block()
        return flask.Response("ok")
    except Exception as e:
        log.exception("Exception while moving to next block.")
        flask.abort(500, e)


@app.route("/experiment/next_trial")
def route_experiment_next_trial():
    try:
        experiment.next_trial()
        return flask.Response("ok")
    except Exception as e:
        log.exception("Exception while moving to next trial.")
        flask.abort(500, e)


@app.route("/video_record/select_source/<src_id>")
def route_select_source(src_id):
    video_record.select_source(src_id)
    return flask.Response("ok")


@app.route("/video_record/unselect_source/<src_id>")
def route_unselect_source(src_id):
    video_record.unselect_source(src_id)
    return flask.Response("ok")


@app.route("/video_record/<cmd>")
def route_video_record(cmd):
    if cmd == "start":
        video_record.start_record()
    elif cmd == "stop":
        video_record.stop_record()

    return flask.Response("ok")


@app.route("/video_record/start_trigger")
def route_start_trigger():
    video_record.start_trigger()
    return flask.Response("ok")


@app.route("/video_record/stop_trigger")
def route_stop_trigger():
    video_record.stop_trigger()
    return flask.Response("ok")


@app.route("/video_record/set_prefix/")
@app.route("/video_record/set_prefix/<prefix>")
def route_set_prefix(prefix=""):
    state[("video_record", "filename_prefix")] = prefix
    return flask.Response("ok")


@app.route("/arena/<cmd>/<value>")
@app.route("/arena/<cmd>/")
def route_arena(cmd, value="unused"):
    f = getattr(arena, cmd)
    if value == "false":
        f(False)
    elif value == "true":
        f(True)
    elif value == "unused":
        f()
    elif value == "None":
        f(None)

    return flask.Response("ok")


@app.route("/save_image/<src_id>")
def route_save_image(src_id):
    video_record.save_image([src_id])
    return flask.Response("ok")


@app.route("/")
def root():
    return "ReptiLearn Controller"


"""
@app.errorhandler(500)
def server_error(e):
    print(str(e), type(e))
    return flask.jsonify(error=str(e)), 500
"""

socketio.run(app, use_reloader=False)

# After flask server is terminated due to KeyboardInterrupt:
log.info("System is shutting down...")
stop_state_emitter()
experiment.shutdown()

video_record.start_trigger()

for img_src in image_sources.values():
    img_src.join()

video_record.stop_trigger()
schedule.cancel_all()
mqtt.shutdown()
rl_logging.shutdown()
state_mod.shutdown()
