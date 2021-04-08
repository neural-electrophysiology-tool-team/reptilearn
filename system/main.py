"""
Main module. Run this module to start the system.
Author: Tal Eisenberg, 2021

Run 'python main.py -h' for help on command line arguments.
"""

import threading
import logging
import flask
import flask_cors
from flask_socketio import SocketIO, emit
import cv2
import json
from pathlib import Path
import sys
import argparse
import importlib
import traceback

import rl_logging
import mqtt
import arena
import schedule
import undistort
import image_utils
from state import state
import state as state_mod
import experiment
import video_record
from dynamic_loading import instantiate_class

# Parse command-line arguments
arg_parser = argparse.ArgumentParser(description="ReptiLearn")
arg_parser.add_argument(
    "--config",
    default="config",
    help="The name of a config module residing in the ./config/ directory",
)
args = arg_parser.parse_args()

# Import configuration module
try:
    config = importlib.import_module(f"config.{args.config}")
except Exception:
    traceback.print_exc()
    sys.exit(1)

# Initialize state module
state_mod.init()

app = flask.Flask("API")
flask_cors.CORS(app)
app.config["SECRET_KEY"] = "reptilearn"
socketio = SocketIO(app, cors_allowed_origins="*")


# Setup Logging
class SocketIOHandler(logging.Handler):
    def emit(self, record):
        socketio.emit("log", self.format(record))


class ExperimentLogHandler(logging.StreamHandler):
    def __init__(self, log_filename="experiment.log"):
        super().__init__()
        state.add_callback(("experiment", "is_running"), self.on_experiment_run_update)
        self.stream = None
        self.log_filename = log_filename

    def on_experiment_run_update(self, old, new):
        if self.stream is not None:
            self.acquire()
            self.stream.close()
            self.stream = None
            self.release()

        if old is False and new is True:  # Experiment is running
            filename = state["experiment", "data_dir"] / self.log_filename
            self.stream = open(filename, "a")

    def emit(self, record):
        if self.stream is not None:
            logging.StreamHandler.emit(self, record)

    def close(self):
        self.acquire()
        try:
            try:
                if self.stream is not None:
                    try:
                        self.flush()
                    finally:
                        self.stream.close()
            finally:
                logging.StreamHandler.close(self)
        finally:
            self.release()


socketio_handler = SocketIOHandler()
socketio_handler.setFormatter(rl_logging.formatter)
experiment_log_handler = ExperimentLogHandler()
experiment_log_handler.setFormatter(rl_logging.formatter)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(rl_logging.formatter)

log = rl_logging.init(
    (socketio_handler, stderr_handler, experiment_log_handler), config.log_level
)

# Configure flask loggers to send messages over socketio and change level.
app_log = logging.getLogger("werkzeug")
app_log.addHandler(socketio_handler)
app_log.addHandler(experiment_log_handler)
app_log.setLevel(logging.WARNING)
app.logger.addHandler(socketio_handler)
app_log.addHandler(experiment_log_handler)
app.logger.setLevel(logging.WARNING)


# Initialize image sources and observers
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

image_observers = {
    obs_id: instantiate_class(
        obs_config["class"], image_sources[obs_config["src_id"]], **obs_config["args"]
    )
    for obs_id, obs_config in config.image_observers.items()
}

# Initialize all other modules
mqtt.init(log, config)
arena.init(log, config.arena_defaults)
video_record.init(image_sources, log, config)
experiment.init(image_observers, log, config)

# Start processes of image observers and sources
for img_obs in image_observers.values():
    img_obs.start()

for img_src in image_sources.values():
    img_src.start()


def convert_for_json(v):
    if hasattr(v, "tolist"):
        return v.tolist()
    if isinstance(v, Path):
        return str(v)
    raise TypeError(v)


# Broadcast state updates over SocketIO
def send_state(old, new):
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


# Flask REST API
@app.route("/config/<attribute>")
def route_config(attribute):
    return flask.Response(
        json.dumps(getattr(config, attribute), default=convert_for_json),
        mimetype="application/json",
    )


def parse_image_request(src_id):
    swidth = flask.request.args.get("width")
    width = None if swidth is None else int(swidth)
    sheight = flask.request.args.get("height")
    height = None if sheight is None else int(sheight)

    if src_id in config.image_sources:
        src_config = config.image_sources[src_id]
    else:
        src_config = None

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

    return (width, height, undistort_mapping)


def encode_image_for_response(img, width, height, undistort_mapping):
    if undistort_mapping is not None:
        img = undistort.undistort_image(img, undistort_mapping)

    return image_utils.encode_image(
        img,
        encoding=".webp",
        encode_params=[cv2.IMWRITE_WEBP_QUALITY, 20],
        shape=(width, height),
    )


@app.route("/image_sources/<src_id>/get_image")
def route_image_sources_get_image(src_id, width=None, height=None):
    img, timestamp = image_sources[src_id].get_image()
    enc_img = encode_image_for_response(img, *parse_image_request(src_id))
    return flask.Response(enc_img, mimetype="image/jpeg")


@app.route("/image_sources/<src_id>/stream")
def route_image_sources_stream(src_id, width=None, height=None):
    img_src = image_sources[src_id]

    frame_rate = int(
        flask.request.args.get("frame_rate", default=config.stream_frame_rate)
    )

    enc_args = parse_image_request(src_id)

    def flask_gen():
        gen = img_src.stream_gen(frame_rate)
        while True:
            try:
                img, timestamp = next(gen)
                enc_img = encode_image_for_response(img, *enc_args)

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
    if f is arena.run_command:
        raise ValueError("Invalid arena command: run_command")

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


# Run Flask server
socketio.run(app, use_reloader=False)


# Shutdown (flask server was terminated due to KeyboardInterrupt)
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
