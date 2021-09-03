import numpy as np
from pathlib import Path
import logging

# Logging level of process and main loggers.
log_level = logging.INFO

# Where experiment python modules can be found.
experiment_modules_dir: Path = Path("./experiments/")

# Session data (videos, images, csv files, etc.) will be stored here.
session_data_root: Path = Path("/data/reptilearn/experiments/")

# Videos and images that were collected when not running an experiment are stored here.
media_dir: Path = Path("/data/reptilearn/media/")

# Lens correction values for various camera and lens combinations.
undistort_flir_firefly_4mm = {
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
}

undistort_flir_blackfly_computar = {
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
}

# The frame rate of HTTP image source streaming. Lower this to reduce network usage.
stream_frame_rate = 15

# Cameras and other image sources are configured here.
image_sources = dict(
    {
        "top": {  # BFS-U3-16S2M
            "class": "video_stream.VideoImageSource",
            "video_path": Path(
                "/data/reptilearn/experiments/pv20_20210714_140216/top_20210714-145857.mp4"
            ),
            "start_frame": 0,
            "end_frame": None,
            "frame_rate": 60,
            "image_shape": (1080, 1440),
            "repeat": True,
            "is_color": False,
            "undistort": undistort_flir_blackfly_computar,
        },
        "left": {  # firefly-dl 1
            "class": "video_stream.VideoImageSource",
            "video_path": Path(
                "/data/reptilearn/experiments/pv20_20210714_140216/left_20210714-145857.mp4"
            ),
            "start_frame": 0,
            "end_frame": None,
            "frame_rate": 60,
            "image_shape": (1080, 1440),
            "repeat": True,
            "is_color": False,
            "undistort": undistort_flir_firefly_4mm,
        },
        "right": {  # firefly-dl 2
            "class": "video_stream.VideoImageSource",
            "video_path": Path(
                "/data/reptilearn/experiments/pv20_20210714_140216/right_20210714-145857.mp4"
            ),
            "start_frame": 0,
            "end_frame": None,
            "frame_rate": 60,
            "image_shape": (1080, 1440),
            "repeat": True,
            "is_color": False,
            "undistort": undistort_flir_firefly_4mm,
        },
        "back": {
            "class": "video_stream.VideoImageSource",
            "video_path": Path(
                "/data/reptilearn/experiments/pv20_20210714_140216/back_20210714-145857.mp4"
            ),
            "start_frame": 0,
            "end_frame": None,
            "frame_rate": 60,
            "image_shape": (1080, 1440),
            "repeat": True,
            "is_color": False,
            "undistort": undistort_flir_firefly_4mm,
        },
    },
)

# Image observers are defined here. These process images from image sources in real-time.
image_observers = {}
"""    "head_bbox": {
        "src_id": "top",
        "class": "image_observers.yolo_bbox_detector.YOLOv4ImageObserver",
        "args": {
            "conf_thres": 0.8,
            "return_neareast_detection": True,
            "buffer_size": 20,
            "weights_path": "image_observers/YOLOv4/yolo4_reptilearn260421_best.weights",
            "cfg_path": "image_observers/YOLOv4/yolo4_2306.cfg",
        },
    }
}"""

# Video encoding parameters:
# These parameters are passed to imageio.get_writer function
# See available options here: https://imageio.readthedocs.io/en/stable/format_ffmpeg.html

cpu_encoding_params = {
    "codec": "libx264",
    "quality": 5,
    "macro_block_size": 8,  # to work with 1440x1080 image size
}

gpu_encoding_params = {
    "codec": "h264_nvenc",
    "quality": None,
    "macro_block_size": 1,
    "pixelformat": "bgr0",
    "ffmpeg_log_level": "warning",
    "output_params": ["-preset", "slow", "-qmin", "25", "-qmax", "30"],
}

video_record = {
    "encoding_params": {
        "test": gpu_encoding_params,
        "top": gpu_encoding_params,
        "right": gpu_encoding_params,
        "left": cpu_encoding_params,
        "back": cpu_encoding_params,
    },
    "video_frame_rate": 60,
    "trigger_interval": 17,
    "file_ext": "mp4",
    "max_write_queue_size": 0,  # 0 means infinite queue.
    "start_trigger_on_startup": False,
}

# MQTT server address
mqtt = {
    "host": "localhost",
    "port": 1883,
}

# Configure the startup values of the arena hardware.
arena_defaults = {
    "signal_led": False,
    "day_lights": False,
    "touchscreen": False,
}

# Database connection configuration
database = {
    "host": "127.0.0.1",
    "port": 5432,
    "db": "reptilearn",
}

# Event data logger configuration.
event_log = {
    # This is a list of default events that will be logged. Additional events
    # can be defined in custom experiment modules. Either MQTT or state update
    # events can be used. See event_log.py for more information.
    "default_events": [
        ("mqtt", "arena/dispense_reward"),
        ("mqtt", "arena/day_lights"),
        ("state", ("session", "cur_block")),
        ("state", ("session", "cur_trial")),
        ("state", ("video", "record", "is_recording")),
    ],
    # Whether to log events to the database.
    "log_to_db": True,
    # Whether to log events to csv files.
    "log_to_csv": True,
    # The database table where events will be stored.
    "table_name": "events",
}
