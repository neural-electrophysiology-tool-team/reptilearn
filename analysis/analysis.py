from pathlib import Path
from dynamic_loading import load_module
import pandas as pd
import re


def load_config(config_name):
    config, _ = load_module(Path(f"config/{config_name}.py"))
    return config


def split_name_datetime(fn):
    """
    Split a string formatted as {name}_%Y%m%d_%H%M%S into name and a datetime64 object.
    """
    match = re.search("(.*)_([0-9]*)[-_]([0-9]*)", fn.stem)
    dt = pd.to_datetime(match.group(2) + " " + match.group(3), format="%Y%m%d %H%M%S")
    name = match.group(1)
    return name, dt


def list_experiments(experiment_data_root: Path):
    exp_dirs = list(filter(lambda p: p.is_dir(), experiment_data_root.glob("*")))
    dts = []
    names = []
    for exp_dir in exp_dirs:
        name, dt = split_name_datetime(exp_dir)
        dts.append(dt)
        names.append(name)

    df = pd.DataFrame(columns=["name", "dir"], index=dts)
    df.name = names
    df.dir = exp_dirs
    return df.sort_index()


def experiment_stats(exp_dir):
    exp_path = Path(exp_dir)
    video_files = list(exp_path.glob("*.mp4")) + list(exp_path.glob("*.avi"))
    image_files = list(exp_path.glob("*.png")) + list(exp_path.glob("*.jpg"))
    csv_files = list(exp_path.glob("*.csv"))

    return {
        "video_count": len(list(video_files)),
        "image_count": len(list(image_files)),
        "csv_count": len(list(csv_files)),
    }


def experiment_stats_df(exps):
    df = pd.DataFrame(columns=["video_count", "image_count", "csv_count"])
    vids = []
    imgs = []
    csvs = []

    for exp_dir in exps.dir:
        stats = experiment_stats(exp_dir)
        vids.append(stats["video_count"])
        imgs.append(stats["image_count"])
        csvs.append(stats["csv_count"])
    df.video_count = vids
    df.image_count = imgs
    df.csv_count = csvs

    return df


def experiment_info(exp_dir):
    exp_dir = Path(exp_dir)
    info = {}

    ts_paths = []
    videos = list(exp_dir.glob("*.mp4")) + list(exp_dir.glob("*.avi"))
    info["videos"] = {}

    for vid_path in videos:
        name, dt = split_name_datetime(vid_path)
        ts_path = exp_dir / (vid_path.stem + ".csv")
        if not ts_path.exists():
            ts_path = None
            duration = None
        else:
            ts_paths.append(ts_path)

            tdf = pd.read_csv(ts_path, parse_dates=True)
            duration = ((tdf.iloc[-1, 0] - tdf.iloc[0, 0]) * 1e09).astype(
                "timedelta64[ns]"
            )

        if dt not in info["videos"]:
            info["videos"][dt] = {}

        info["videos"][dt][name] = {
            "path": vid_path,
            "timestamps": ts_path,
            "frame_count": tdf.shape[0],
            "duration": duration,
        }

    for csv_path in filter(lambda p: p not in ts_paths, exp_dir.glob("*.csv")):
        if "events.csv" in csv_path.name:
            info["event_log"] = csv_path
        elif "head_bbox.csv" in csv_path.name:
            info["head_bbox"] = csv_path
        else:
            if "csvs" not in info:
                info["csvs"] = []

            info["csvs"].append(csv_path)   

    info["images"] = list(exp_dir.glob("*.jpg")) + list(exp_dir.glob("*.png"))

    return info


def read_event_log(exp_info):
    events = pd.read_csv(exp_info["event_log"])
    events.time = pd.to_datetime(events.time, unit='s')
    return events
