import undistort

config = {
    "stream_fps": 15,
    "manager_port": 50000,
    "cameras": {
        "20349302": {  # firefly-dl 1
            "exposure": 8000,
            "trigger": "ttl",  # or "frame_rate"
            "img_shape": (1080, 1440),
            # "undistort": undistort.flir_firefly_attr
        },
        "20349310": {  # firefly-dl 2
            "exposure": 8000,
            "trigger": "ttl",
            # "frame_rate": 60,
            "img_shape": (1080, 1440),
        },
        "0138A051": {  # BFS-U3-16S2M
            "exposure": 8000,
            "trigger": "frame_rate",
            "frame_rate": 60,
            "img_shape": (1080, 1440),
            "undistort": undistort.flir_blackfly_attr,
        },
    },
    "detector_source": 0,
}
