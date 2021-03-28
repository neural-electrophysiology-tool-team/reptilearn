import numpy as np
from pathlib import Path

experiment_modules_dir = Path("./experiments/")
experiment_data_root = Path("/data/reptilearn/experiments/")
videos_dir = Path("/data/reptilearn/media/")

# undistort lens correction
undistort_flir_firfly_4mm = {
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

stream_frame_rate = 15

image_sources = dict(
    {
        "left": {  # firefly-dl 1
            "class": "image_sources.flir_cameras.FLIRImageSource",
            "cam_id": "20349302",
            "exposure": 8000,
            "trigger": "ttl",  # or "frame_rate"
            "image_shape": (1080, 1440),
            "undistort": undistort_flir_firfly_4mm,
        },
        "right": {  # firefly-dl 2
            "class": "image_sources.flir_cameras.FLIRImageSource",
            "cam_id": "20349310",
            "exposure": 8000,
            "trigger": "ttl",
            # "frame_rate": 60,
            "image_shape": (1080, 1440),
            "undistort": undistort_flir_firfly_4mm,
        },
        "top": {  # BFS-U3-16S2M
            "class": "image_sources.flir_cameras.FLIRImageSource",
            "cam_id": "0138A051",
            "exposure": 8000,
            "trigger": "frame_rate",
            "frame_rate": 60,
            "image_shape": (1080, 1440),
            "undistort": undistort_flir_blackfly_computar,
        },
        "test": {
            "class": "video_stream.VideoImageSource",
            "video_path": Path("./media/0138A051_20210222-133916.mp4"),
            "start_frame": 0,
            "end_frame": None,
            "frame_rate": 60,
            "image_shape": (1080, 1440),
            "repeat": True,
            "is_color": False,
            "undistort": undistort_flir_blackfly_computar,
        },
    },
)


image_observers = {
    "head_bbox": {
        "src_id": "test",
        "class": "image_observers.yolo_bbox_detector.YOLOv4ImageObserver",
        "args": {
            "conf_thres": 0.8,
            "return_neareast_detection": True,
            "buffer_size": 20,
        },
    }
}

video_record = {
    "video_encoding": {
        # These parameters are passed to imageio.get_writer function
        # See available options here: https://imageio.readthedocs.io/en/stable/format_ffmpeg.html
        "codec": "libx264",
        "quality": 5,
        "macro_block_size": 8,  # to work with 1440x1080 image size
    },
    "video_frame_rate": 60,
    "file_ext": "mp4",
    "start_trigger_on_startup": False,
}

mqtt = {
    "host": "localhost",
    "port": 1883,
}

arena_defaults = {
    "signal_led": False,
    "day_lights": False
}

event_log = {
    "default_events": [
        ("mqtt", "arena/#"),
        ("state", ("experiment", "is_running")),
        ("state", ("experiment", "cur_block")),
        ("state", ("experiment", "cur_trial")),
        ("state", ("video_record", "is_recording")),
    ]
}
