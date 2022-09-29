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
    "Archive1": Path("/path/to/archive/dir"),
    "Archive2": Path("/path/to/another/archive/dir"),
}

# Image source streaming over HTTP settings
http_streaming = {
    "frame_rate": 15,  # http streaming frame rate

    # See https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.save
    # and https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
    "encoding": "WebP",
    "encode_params": {"method": 2},
}


video_record = {
    "video_frame_rate": 60,  # the default frame rate for recorded videos
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
            "ffmpeg_log_level": "warning",
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
            "ffmpeg_log_level": "warning",
            "output_params": ["-preset", "slow", "-qp", "30", "-rc", "constqp"],
        },
    },
}

# MQTT broker server address
mqtt = {
    "host": "localhost",
    "port": 1883,
}


# Arena hardware controller
arena = {
    "poll_interval": 60,
    "displays": {"touchscreen": ":0"},
    # Uncomment the following lines to log values from the specified arena interfaces to a database table.
    # "data_log": {  # requires a database connection
    #     "table_name": "arena",
    #     "columns": [
    #         ("Temp_0", "double precision"),
    #         ("Temp_1", "double precision"),
    #     ],
    # },
    "command_topic": "arena_command",  # Arena commands will be published to this MQTT topic
    "receive_topic": "arena",  # Incoming arena messages will arrive on this MQTT topic
}


# Database connection
database = {
    "user": "postgres",
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


# Lens correction values for various camera and lens combinations. Each dict value
# should have "mtx" and "dist" keys.
undistort = {
}
