# -*- coding: utf-8 -*-

import threading
import logging
import flask
import flask_cors
from flask_socketio import SocketIO, emit
import routes
import json
import sys
import argparse
import importlib
import traceback
from dotenv import load_dotenv
import multiprocessing as mp
import platform

import rl_logging
import mqtt
import arena
import schedule
from state import state
import state as state_mod
import experiment
import task
import video_system
from json_convert import json_convert

# Load environment variables from .env file.
load_dotenv()

# Parse command-line arguments
arg_parser = argparse.ArgumentParser(description="ReptiLearn")
arg_parser.add_argument(
    "--config",
    default="config",
    help="The name of a config module residing in the ./config/ directory",
)
args = arg_parser.parse_args()

print("🦎 Loading Reptilearn")

# Import configuration module
try:
    config = importlib.import_module(f"config.{args.config}")
except Exception:
    traceback.print_exc()
    sys.exit(1)

if platform.system() == "Darwin":
    mp.set_start_method("fork")

# Initialize state module
state_mod.init()

# Initialize Flask REST app
app = flask.Flask("reptiLearnAPI", static_folder=config.static_web_path, static_url_path='/' + str(config.static_web_path.name))
app.config["SECRET_KEY"] = "reptilearn"
flask_cors.CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


# Setup Logging
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(rl_logging.formatter)

app_log = logging.getLogger("werkzeug")

log = rl_logging.init(
    log_handlers=(
        rl_logging.SocketIOHandler(socketio),
        stderr_handler,
        rl_logging.SessionLogHandler(),
    ),
    log_buffer=rl_logging.LogBuffer(config.log_buffer_size),
    extra_loggers=(app_log, app.logger),
    extra_log_level=logging.WARNING,
    default_level=config.log_level,
)

# Initialize all other modules
mqtt.init(log, config)
task.init(log, config)
arena.init(log, config)
video_system.init(log, config)
experiment.init(log, config)

# Setup flask http routes
routes.add_routes(app, config, log)

# Load image sources and observers
video_system.start()


# Setup SocketIO state updates
def send_state(_, new):
    new_json = json.dumps(new, default=json_convert)
    socketio.emit("state", new_json)


@socketio.on("connect")
def handle_connect():
    blob = json.dumps(state.get_self(), default=json_convert)
    emit("state", blob)
    # TODO: emit("log", all_past_log_or_session_log?)


state_listen, stop_state_emitter = state_mod.register_listener(send_state)
threading.Thread(target=state_listen).start()


# Run Flask server
try:
    socketio.run(app, use_reloader=False, host="0.0.0.0", port=config.api_port)
except KeyboardInterrupt:
    pass


# Shutdown (flask server was terminated)
log.info("System is shutting down...")
stop_state_emitter()
experiment.shutdown()
video_system.shutdown()
schedule.cancel_all(pool=None, wait=True)
arena.shutdown()
mqtt.shutdown()
log.info("Shutting down logging and global state...")
rl_logging.shutdown()
state_mod.shutdown()
