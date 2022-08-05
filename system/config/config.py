import numpy as np
from pathlib import Path
import logging

# Method for starting up child processes. Valid values are "spawn" and "fork".
# See https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
process_start_method = "spawn"

# Logging level of process and main loggers.
log_level = logging.INFO

# Max number of recent log lines that will be stored in the log buffer.
log_buffer_size = 1000

# A tuple (host, port) of the shared state store server
state_store_address = ("127.0.0.1", 50000)

# Authkey of the shared state store
state_store_authkey = "reptilearn"

# Port number for a REST and socketio api server. If changed, edit ui/src/config.js with
# a matching value.
api_port = 5000

# Where experiment python modules can be found.
experiment_modules_dir: Path = Path("./experiments/")

# Where python modules containing tasks can be found.
tasks_modules_dir: Path = Path("./tasks/")

# Session data (videos, images, csv files, etc.) will be stored here.
session_data_root: Path = Path("/data/reptilearn/sessions/")

# Videos and images that were collected without an open session are stored here.
media_dir: Path = Path("/data/reptilearn/media/")

# Path to the video configuration file
video_config_path: Path = Path("./config/video_config.json")

# Path to the arena hardware controller configuration file
arena_config_path: Path = Path("./config/arena_config.json")

# Path to a folder containing static web assets. The url to access these assets will be: http://<api host>:<api_port>/<static folder name>/<filename> (e.g. http://localhost:5000/stimuli/x.mp4)
static_web_path: Path = Path("../stimuli")

# Available archive directories
archive_dirs = {
    "Local archive": Path("/media/2TB/rl_archive"),
    "Tal on SIL2": Path("/media/sil2/tal/reptilearn_sessions/rl2_archive"),
}

# Image source streaming over HTTP settings
http_streaming = {
    "frame_rate": 15,
    # See https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.save
    # and https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
    "encoding": "WebP",
    "encode_params": {"method": 2},
}


video_record = {
    "video_frame_rate": 60,
    "file_ext": "mp4",
    "start_trigger_on_startup": False,
    "max_write_queue_size": 0,  # 0 means infinite queue.
    "encoding_configs": {
        # Video encoding parameters:
        # These parameters are passed to imageio.get_writer function
        # See available options here: https://imageio.readthedocs.io/en/stable/format_ffmpeg.html
        "cpu": {
            "codec": "libx264",
            "quality": 5,
            "macro_block_size": 8,  # to work with 1440x1080 image size
        },
        "gpu": {
            "codec": "h264_nvenc",
            "quality": None,
            "macro_block_size": 1,
            "pixelformat": "bgr0",
            "ffmpeg_log_level": "warning",
            "output_params": ["-preset", "slow", "-qp", "30", "-rc", "constqp"],
        },
        "color": {
            "codec": "h264_nvenc",
            "quality": None,
            "macro_block_size": 1,
            # "pixelformat": "bgr0",
            "ffmpeg_log_level": "warning",
            "output_params": ["-preset", "slow", "-qp", "30", "-rc", "constqp"],
        },
    },
}

# MQTT server address
mqtt = {
    "host": "localhost",
    "port": 1883,
}


# Arena hardware controller
arena = {
    "poll_interval": 60,
    "displays": {"touchscreen": ":0"},
    # "data_log": {  # requires a database connection
    #     "table_name": "arena",
    #     "columns": [
    #         ("Temp_0", "double precision"),
    #         ("Temp_1", "double precision"),
    #     ],
    # },
    "command_topic": "arena_command",
    "receive_topic": "arena",
}


# Database connection
database = {
    "user": "postgre",
    "host": "127.0.0.1",
    "port": 5432,
    "db": "reptilearn",
}

# Event data logger
event_log = {
    # This is a list of default events that will be logged. Additional events
    # can be defined in custom experiment modules. Either MQTT or state update
    # events can be used. See event_log.py for more information.
    "default_events": [
        ("mqtt", "arena_command"),
        ("state", ("session", "cur_block")),
        ("state", ("session", "cur_trial")),
        ("state", ("video", "record", "is_recording")),
    ],
    # Whether to log events to the database.
    "log_to_db": False,
    # Whether to log events to csv files.
    "log_to_csv": True,
    # The database table where events will be stored.
    "table_name": "events",
}


# Lens correction values for various camera and lens combinations.
undistort = {
    "flir_firefly_4mm": {
        "mtx": np.array(
            [
                [1.14515564e03, 0.00000000e00, 7.09060713e02],
                [0.00000000e00, 1.14481967e03, 5.28220061e02],
                [0.00000000e00, 0.00000000e00, 1.00000000e00],
            ]
        ),
        "dist": np.array(
            [
                [
                    -4.25580120e-01,
                    3.02361751e-01,
                    -1.56952670e-03,
                    -4.04385846e-04,
                    -2.27525587e-01,
                ]
            ]
        ),
    },
    "flir_blackfly_computar": {
        "dist": np.array(
            [
                [
                    -3.73487649e-01,
                    1.70639650e-01,
                    2.12535002e-04,
                    9.02337277e-05,
                    -4.25039396e-02,
                ]
            ]
        ),
        "mtx": np.array(
            [
                [1.04345883e03, 0.00000000e00, 7.94892178e02],
                [0.00000000e00, 1.04346538e03, 6.09748241e02],
                [0.00000000e00, 0.00000000e00, 1.00000000e00],
            ]
        ),
    },
}
