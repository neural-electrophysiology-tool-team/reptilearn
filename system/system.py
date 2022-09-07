# -*- coding: utf-8 -*-
"""
The main module. Start all system components and shutdown gracefully.

Author: Tal Eisenberg, 2021
"""
import multiprocessing
import threading
import logging
import time
import flask
import flask_cors
from flask_socketio import SocketIO, emit
import json
import sys
import argparse
from dotenv import load_dotenv

import configure
import rl_logging
import mqtt
import arena
import schedule
import managed_state
import experiment
import task
import video_system
import routes
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

print("🦎 Loading ReptiLearn")

# Import configuration module
config = configure.load_config(args.config)

# Set process start method according to the config module
multiprocessing.set_start_method(config.process_start_method)

# Initialize the flask app for the REST API
app = flask.Flask(
    "reptiLearnAPI",
    static_folder=config.static_web_path,
    static_url_path="/" + str(config.static_web_path.name),
)
app.config["SECRET_KEY"] = "reptilearn"
flask_cors.CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create state store
state_store = managed_state.StateStore(
    address=config.state_store_address, authkey=config.state_store_authkey
)

# Create a Cursor pointing to the root of the state. It can be used only from the main process.
state = None
while state is None:  # retry until the store server is running
    try:
        state = managed_state.Cursor(
            (), address=config.state_store_address, authkey=config.state_store_authkey
        )
    except (ConnectionRefusedError, multiprocessing.AuthenticationError):
        time.sleep(0.01)


# Run a state dispatcher thread. This is can be used anywhere on the main process.
dispatcher = managed_state.StateDispatcher(state)
dispatcher_thread = threading.Thread(target=dispatcher.listen)
dispatcher_thread.start()

# Setup Logging
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(rl_logging.formatter)

app_log = logging.getLogger("werkzeug")

log = rl_logging.init(
    log_handlers=(
        rl_logging.SocketIOHandler(socketio),
        stderr_handler,
        rl_logging.SessionLogHandler(state),
    ),
    extra_loggers=(app_log, app.logger),
    extra_log_level=logging.WARNING,
    default_level=config.log_level,
)

# Initialize all other modules
mqtt.init()
task.init()
arena.init(state)
video_system.init(state)
experiment.init(state)

# Setup flask http routes
routes.add_routes(app)

# Start the video system
video_system.start()


# Setup SocketIO state updates
def send_state(_, new):
    new_json = json.dumps(new, default=json_convert)
    socketio.emit("state", new_json)


@socketio.on("connect")
def handle_connect():
    blob = json.dumps(state.get_self(), default=json_convert)
    emit("state", blob)


state_listen, stop_state_emitter = state.register_listener(send_state)
threading.Thread(target=state_listen).start()


# Run Flask server
socketio.run(app, port=config.api_port)


# Shutdown (flask server was terminated)
def shutdown():
    video_system.shutdown()
    schedule.cancel_all(pool=None, wait=True)
    arena.shutdown()
    mqtt.shutdown()

    log.info("Shutting down logging and state store...")
    rl_logging.shutdown()
    stop_state_emitter()
    dispatcher.stop()
    state_store.shutdown()


log.info("System is shutting down...")
if "session" in state:
    state.add_callback("session", lambda old, new: shutdown())
    experiment.shutdown()
else:
    experiment.shutdown()
    shutdown()
