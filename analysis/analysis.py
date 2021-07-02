from pathlib import Path
from dynamic_loading import load_module
import pandas as pd
import re
import os
import copy
import moviepy.editor as mpy
import moviepy.tools
import moviepy.config
import json
import undistort
import bbox


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

    exp_state_json = exp_dir / "exp_state.json"
    if exp_state_json.exists():
        with open(exp_state_json, "r") as f:
            info["exp_state"] = json.load(f)
    else:
        info["exp_state"] = None

    return info


def find_src_videos(exp_info, src_id):
    vids = {}

    for vid_ts in exp_info["videos"]:
        for vid_name in exp_info["videos"][vid_ts].keys():
            if vid_name.endswith(src_id):
                vids[vid_ts] = copy.deepcopy(exp_info["videos"][vid_ts][vid_name])

    return vids


def load_timestamps(info):
    info = copy.deepcopy(info)

    if "timestamps" in info:
        #  vid_info
        tdf = pd.read_csv(info["timestamps"])
        tdf.timestamp = pd.to_datetime(tdf.timestamp, unit="s")
        info["timestamps"] = tdf
    elif "videos" in info:
        # experiment info
        info["videos"] = load_timestamps(info["videos"])
    else:
        # exp_info["videos"]
        for ts in info:
            info[ts] = load_timestamps(info[ts])

    return info


def is_timestamp_contained(tdf, timestamp):
    beginning = tdf.timestamp.iloc[0]
    end = tdf.timestamp.iloc[-1]
    return beginning < timestamp < end


def timestamp_to_frame(tdf, timestamp):
    return (tdf.timestamp - timestamp).abs().argmin()


def find_video_position(info, timestamp):
    if "videos" in info:
        info = info["videos"]

    res = []

    def maybe_append_position(vid_info):
        tdf = vid_info["timestamps"]

        if is_timestamp_contained(tdf, timestamp):
            res.append(
                {
                    "vid_info": vid_info,
                    "frame": timestamp_to_frame(tdf, timestamp),
                    "timestamp": timestamp,
                }
            )

    for ts, vids in info.items():
        if type(vids) is dict:
            if "timestamps" in vids:
                maybe_append_position(vids)
            else:
                for k, vid_info in vids.items():
                    maybe_append_position(vid_info)
    return res


def read_event_log(exp_info):
    events = pd.read_csv(exp_info["event_log"])
    events.time = pd.to_datetime(events.time, unit="s")
    return events


def ffmpeg_extract_subclip(filename, t1, t2, targetname=None):
    """Makes a new video file playing video file ``filename`` between
    the times ``t1`` and ``t2``.

    from: https://zulko.github.io/moviepy/_modules/moviepy/video/io/ffmpeg_tools.html"""
    name, ext = os.path.splitext(filename)
    if not targetname:
        T1, T2 = [int(1000 * t) for t in [t1, t2]]
        targetname = "%sSUB%d_%d.%s" % (name, T1, T2, ext)

    cmd = [
        moviepy.config.get_setting("FFMPEG_BINARY"),
        "-y",
        "-ss",
        "%0.2f" % t1,
        "-i",
        filename,
        "-t",
        "%0.2f" % (t2 - t1),
        "-map",
        "0",
        "-vcodec",
        "copy",
        "-acodec",
        "copy",
        targetname,
    ]

    moviepy.tools.subprocess_call(cmd, logger=None)


def extract_clip(vid_path, start_frame, end_frame, output_path):
    fps = mpy.VideoFileClip(str(vid_path)).fps
    start_time = start_frame / fps
    end_time = end_frame / fps

    ffmpeg_extract_subclip(vid_path, int(start_time), int(end_time), output_path)


def extract_event_clips(
    events_df, output_dir, file_prefix="event", pre_secs=60, post_secs=60
):
    clip_paths = []
    for i, r in events_df.iterrows():
        fps = mpy.VideoFileClip(str(r.path)).fps
        pre_frames = pre_secs * fps
        post_frames = post_secs * fps

        start_frame = max(int(r.frame - pre_frames), 0)
        end_frame = int(r.frame + post_frames)

        relative_ts = r.timestamp - r.video_start
        total_secs = int(relative_ts.total_seconds())
        hrs = total_secs // 3600
        mins = (total_secs % 3600) // 60
        secs = (total_secs % 3600) % 60
        fts = f"{hrs:02}{mins:02}{secs:02}"

        clip_path = output_dir / f"{file_prefix}{i}_{fts}_{start_frame}_{end_frame}.mp4"
        clip_paths.append(clip_path)

        print(f"\t{clip_path}")

        ffmpeg_extract_subclip(r.path, start_frame, end_frame, clip_path)

    return clip_paths


def create_video_event_df(info, events):
    event_positions = [find_video_position(info, ts) for ts in events.time.values]

    return pd.DataFrame(  # taking only the 1st image source for each event
        {
            "path": [r[0]["vid_info"]["path"] for r in event_positions if len(r) > 0],
            "frame": [r[0]["frame"] for r in event_positions if len(r) > 0],
            "timestamp": [r[0]["timestamp"] for r in event_positions if len(r) > 0],
            "video_start": [
                r[0]["vid_info"]["timestamps"].timestamp.values[0]
                for r in event_positions
                if len(r) > 0
            ],
        }
    )


def get_head_centroids(info, cam_undist=None):
    pos_df = pd.read_csv(info["head_bbox"])
    bboxes = pos_df[["x1", "y1", "x2", "y2"]]

    if cam_undist is not None:
        bboxes = undistort.undistort_data(bboxes, 1440, 1080, cam_undist)
    centroids = bbox.xyxy_to_centroid(bboxes.to_numpy())
    return centroids


def is_in_reinforced_area(info):
    if "reinforced_area" not in info["exp_state"]:
        raise Exception("Experiment state does not contain a 'reinforced_area' key")

    area = info["exp_state"]["reinforced_area"]
