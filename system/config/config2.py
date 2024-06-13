from pathlib import Path
import numpy as np

session_data_root: Path = Path("/data/reptilearn/sessions/")

media_dir: Path = Path("/data/reptilearn/media/")

archive_dirs = {
    "Local archive": Path("/media/2TB/rl_archive"),
    "Tal on SIL2": Path("/media/sil2/tal/reptilearn_sessions/rl2_archive")
}

video_record = {
    "video_frame_rate": 50,
}

# Arena hardware controller
arena = {
    "poll_interval": 60,
    "displays": {},

    # Set this to False if you don't want to run the MQTT-Serial bridge
    "run_bridge_process": True,

    "data_log": {  # requires a database connection
        "table_name": "arena",
        "columns": [
            ("Temp_0", "double precision"),
            ("Temp_1", "double precision"),
        ],
    },
}

web_ui = {
    "host": "0.0.0.0",
    "port": 3500,
}

# Database connection
database = {
    "user": "postgres",
    "host": "127.0.0.1",
    "port": 5432,
    "db": "reptilearn",
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
