from pathlib import Path
from dataclasses import dataclass
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
import experiment as exp

# TODO:
# - option to choose locale
# - docstrings

events_log_filename = "events.csv"
session_state_filename = "session_state.json"
name_locale = "Asia/Jerusalem"


def load_config(config_name):
    config, _ = load_module(Path(f"config/{config_name}.py"))
    return config


def is_timestamp_contained(tdf, timestamp):
    beginning = tdf.time.iloc[0]
    end = tdf.time.iloc[-1]
    return beginning < timestamp < end


def idx_for_time(tdf: pd.DataFrame, timestamp: pd.Timestamp):
    return (tdf.time - timestamp).abs().argmin()


def extract_clip(vid_path, start_frame, end_frame, output_path):
    fps = mpy.VideoFileClip(str(vid_path)).fps
    start_time = start_frame / fps
    end_time = end_frame / fps

    ffmpeg_extract_subclip(vid_path, int(start_time), int(end_time), output_path)


def ffmpeg_extract_subclip(filename, t1, t2, targetname=None):
    """
    Makes a new video file playing video file ``filename`` between
    the times ``t1`` and ``t2``.

    from: https://zulko.github.io/moviepy/_modules/moviepy/video/io/ffmpeg_tools.html
    """
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


def list_sessions(session_data_root: Path):
    exp_dirs = list(filter(lambda p: p.is_dir(), session_data_root.glob("*")))
    dts = []
    names = []
    for exp_dir in exp_dirs:
        name, dt = exp.split_name_datetime(exp_dir.stem)
        dts.append(dt)
        names.append(name)

    df = pd.DataFrame(columns=["name", "dir"], index=dts)
    df.name = names
    df.dir = exp_dirs
    return df.sort_index()


def session_stats(exp_dir):
    exp_path = Path(exp_dir)
    video_files = list(exp_path.glob("*.mp4")) + list(exp_path.glob("*.avi"))
    image_files = list(exp_path.glob("*.png")) + list(exp_path.glob("*.jpg"))
    csv_files = list(exp_path.glob("*.csv"))

    return {
        "video_count": len(list(video_files)),
        "image_count": len(list(image_files)),
        "csv_count": len(list(csv_files)),
    }


def sessions_stats_df(sessions):
    df = pd.DataFrame(columns=["video_count", "image_count", "csv_count"])
    vids = []
    imgs = []
    csvs = []

    for dir in sessions.dir:
        stats = session_stats(dir)
        vids.append(stats["video_count"])
        imgs.append(stats["image_count"])
        csvs.append(stats["csv_count"])
    df.video_count = vids
    df.image_count = imgs
    df.csv_count = csvs

    return df


class VideoInfo:
    name: str
    time: pd.Timestamp
    path: Path
    timestamp_path: Path
    timestamps: pd.DataFrame
    frame_count: int
    duration: int
    src_id: str

    def __init__(self, path: Path):
        self.name, self.time = exp.split_name_datetime(path.stem)
        self.time = self.time.tz_localize(name_locale).tz_convert("utc")

        self.timestamp_path = path.parent / (path.stem + ".csv")
        if not self.timestamp_path.exists():
            self.timestamp_path = None
            self.duration = None
        else:
            self.timestamps = pd.read_csv(self.timestamp_path, parse_dates=True)
            self.timestamps.rename(columns={"timestamp": "time"}, inplace=True)
            self.timestamps.time = pd.to_datetime(
                self.timestamps.time, unit="s"
            ).dt.tz_localize("utc")

            self.duration = self.timestamps.time.iloc[-1] - self.timestamps.time.iloc[0]

        self.path = path
        self.frame_count = self.timestamps.shape[0]
        split = self.name.split("_")
        if len(split) == 1:
            self.src_id = self.name
        else:
            self.src_id = split[
                -1
            ]  # NOTE: what happens when both src_id and name has underscores?

    def __repr__(self):
        return f"\nVideoInfo(name: {self.name},\n\ttime: {self.time},\n\tpath: {self.path},\n\ttimestamp_path: {self.timestamp_path},\n\tframe_count: {self.frame_count},\n\tduration: {self.duration})"


@dataclass(init=False)
class VideoPosition:
    video: VideoInfo
    timestamp: pd.Timestamp
    frame: int = None

    def __init__(self, video, timestamp):
        self.video = video
        self.timestamp = timestamp
        if self.video.timestamps is not None:
            self.frame = idx_for_time(self.video.timestamps, timestamp)


@dataclass(init=False)
class SessionInfo:
    dir: Path
    videos: [VideoInfo]
    images: [Path]
    event_log_path: Path
    csvs: [Path]
    session_state_path: Path
    session_state: dict

    def __init__(self, session_dir):
        session_dir = Path(session_dir)
        if not session_dir.exists():
            raise ValueError(f"Session directory doesn't exist: {str(session_dir)}")

        self.dir = session_dir

        self.videos = [
            VideoInfo(p)
            for p in list(session_dir.glob("*.mp4")) + list(session_dir.glob("*.avi"))
        ]

        ts_paths = [v.timestamp_path for v in self.videos]
        self.csvs = []
        for csv_path in [p for p in session_dir.glob("*.csv") if p not in ts_paths]:
            if events_log_filename in csv_path.name:
                self.event_log_path = csv_path
            else:
                self.csvs.append(csv_path)

        self.images = list(session_dir.glob("*.jpg")) + list(session_dir.glob("*.png"))

        self.session_state_path = session_dir / "session_state.json"
        if not self.session_state_path.exists():
            # Legacy file name
            self.session_state_path = session_dir / "exp_state.json"
            if not self.session_state_path.exists():
                self.session_state_path = None

        self._session_state = None
        self._event_log = None
        self._head_bbox = None

    @property
    def session_state(self) -> dict:
        if self._session_state is not None:
            return self._session_state

        if self.session_state_path is None:
            self._session_state = None
        else:
            with open(self.session_state_path, "r") as f:
                self._session_state = json.load(f)

        return self._session_state

    @property
    def event_log(self) -> pd.DataFrame:
        if self._event_log is not None:
            return self._event_log

        events = pd.read_csv(self.event_log_path)
        events.time = pd.to_datetime(events.time, unit="s").dt.tz_localize("utc")
        self._event_log = events

        return self._event_log

    def filter_videos(
        self, videos=None, src_id: str = None, ts: pd.Timestamp = None
    ) -> [VideoInfo]:

        ret = []
        if videos is None:
            videos = self.videos

        for vid in videos:
            if src_id is not None and vid.src_id != src_id:
                continue
            if ts is not None and vid.time != ts:
                continue
            ret.append(vid)

        return ret

    def video_position_at_time(self, timestamp, videos=None):
        res = []
        if videos is None:
            videos = self.videos

        for vid in videos:
            if vid.timestamps is None:
                print(f"WARNING: Video {vid.name}, {vid.time} has no timestamps")
                return

            if is_timestamp_contained(vid.timestamps, timestamp):
                res.append(VideoPosition(vid, timestamp))

        return res

    def extract_clip(
        self,
        src_id: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        output_dir: Path,
        file_prefix: str,
    ):
        videos = self.filter_videos(src_id=src_id)
        start_pos = self.video_position_at_time(start_time, videos)
        end_pos = self.video_position_at_time(end_time, videos)

        if len(start_pos) != 1:
            raise ValueError("start_time matched multiple videos or no videos")
        if len(end_pos) != 1:
            raise ValueError("end_time matched multiple videos or no videos")
        if start_pos[0].video.path != end_pos[0].video.path:
            raise ValueError("start_time and end_time matched different videos")

        start_pos, end_pos = start_pos[0], end_pos[0]

        relative_ts = start_pos.timestamp - start_pos.video.time
        total_secs = int(relative_ts.total_seconds())
        hrs = total_secs // 3600
        mins = (total_secs % 3600) // 60
        secs = (total_secs % 3600) % 60
        fts = f"{hrs:02}{mins:02}{secs:02}"

        clip_path = (
            output_dir / f"{file_prefix}_{fts}_{start_pos.frame}_{end_pos.frame}.mp4"
        )
        extract_clip(start_pos.video.path, start_pos.frame, end_pos.frame, clip_path)

    @property
    def head_bbox(self):
        if self._head_bbox is not None:
            return self._head_bbox

        bbox_csvs = [p for p in self.csvs if p.name == "head_bbox.csv"]

        if len(bbox_csvs) == 0:
            return None

        self._head_bbox = pd.read_csv(bbox_csvs[0])
        self._head_bbox.index = pd.to_datetime(
            self._head_bbox.time, unit="s"
        ).dt.tz_localize("utc")
        self._head_bbox.drop(columns=["time"], inplace=True)
        return self._head_bbox

    @property
    def head_centroids(self):
        head_bbox = self.head_bbox
        centroids = bbox.xyxy_to_centroid(head_bbox[["x1", "y1", "x2", "y2"]].values)
        df = pd.DataFrame(centroids, columns=["x", "y"])
        df.index = head_bbox.index
        df["confidence"] = head_bbox.confidence
        return df


#### DEPRECATED ####

# deprecated
def split_name_datetime(fn):
    """
    Split a string formatted as {name}_%Y%m%d_%H%M%S into name and a datetime64 object.
    """
    match = re.search("(.*)_([0-9]*)[-_]([0-9]*)", fn.stem)
    dt = pd.to_datetime(match.group(2) + " " + match.group(3), format="%Y%m%d %H%M%S")
    name = match.group(1)
    return name, dt


# deprecated
def session_info(session_dir):
    session_dir = Path(session_dir)
    if not session_dir.exists():
        raise Exception(f"Session directory doesn't exist: {str(session_dir)}")

    info = {}

    ts_paths = []
    videos = list(session_dir.glob("*.mp4")) + list(session_dir.glob("*.avi"))
    info["videos"] = {}

    for vid_path in videos:
        name, dt = split_name_datetime(vid_path)
        ts_path = session_dir / (vid_path.stem + ".csv")
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

    for csv_path in filter(lambda p: p not in ts_paths, session_dir.glob("*.csv")):
        if "events.csv" in csv_path.name:
            info["event_log"] = csv_path
        elif "head_bbox.csv" in csv_path.name:
            info["head_bbox"] = csv_path
        else:
            if "csvs" not in info:
                info["csvs"] = []

            info["csvs"].append(csv_path)

    info["images"] = list(session_dir.glob("*.jpg")) + list(session_dir.glob("*.png"))

    session_state_json = session_dir / "session_state.json"
    if session_state_json.exists():
        with open(session_state_json, "r") as f:
            info["session_state"] = json.load(f)
    else:
        session_state_json = session_dir / "exp_state.json"
        if session_state_json.exists():
            with open(session_state_json, "r") as f:
                info["session_state"] = json.load(f)
        else:
            info["session_state"] = None

    return info


# deprecated
def find_src_videos(session_info, src_id):
    vids = {}

    for vid_ts in session_info["videos"]:
        for vid_name in session_info["videos"][vid_ts].keys():
            if vid_name.endswith(src_id):
                vids[vid_ts] = copy.deepcopy(session_info["videos"][vid_ts][vid_name])

    return vids


# deprecated
def load_timestamps(info):
    info = copy.deepcopy(info)

    if "timestamps" in info:
        #  vid_info
        tdf = pd.read_csv(info["timestamps"])
        tdf.timestamp = pd.to_datetime(tdf.timestamp, unit="s")
        info["timestamps"] = tdf
    elif "videos" in info:
        # session info
        info["videos"] = load_timestamps(info["videos"])
    else:
        # session_info["videos"]
        for ts in info:
            info[ts] = load_timestamps(info[ts])

    return info


# deprecated
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
                    "frame": idx_for_time(tdf, timestamp),
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


# deprecated
def read_event_log(session_info):
    events = pd.read_csv(session_info["event_log"])
    events.time = pd.to_datetime(events.time, unit="s")
    return events


# deprecated
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

        extract_clip(r.path, start_frame, end_frame, clip_path)

    return clip_paths


# deprecated
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


# deprecated
def get_head_centroids(info, cam_undist=None):
    pos_df = pd.read_csv(info["head_bbox"])
    bboxes = pos_df[["x1", "y1", "x2", "y2"]]

    if cam_undist is not None:
        bboxes = undistort.undistort_data(bboxes, 1440, 1080, cam_undist)
    centroids = bbox.xyxy_to_centroid(bboxes.to_numpy())
    return centroids


########
