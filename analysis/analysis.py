from pathlib import Path
from dataclasses import dataclass
import pandas as pd

import os
import moviepy.editor as mpy
import moviepy.tools
import moviepy.config
import json
import bbox
import experiment as exp

# TODO:
# - option to choose locale
# - docstrings
# - support for undistort

events_log_filename = "events.csv"
session_state_filename = "session_state.json"
name_locale = "Asia/Jerusalem"


def read_timeseries_csv(path: Path, time_col="time", tz="utc") -> pd.DataFrame:
    """
    Read csv file into a pandas DataFrame. Creates a DatetimeIndex and sets
    the timezone to the specified one.

    path: csv file path
    time_col: The name of the column to be used as a DatetimeIndex
    tz: The timezone of the time column (see DatetimeIndex.tz_localize)
    """
    df = pd.read_csv(path)

    if hasattr(time_col, "__getitem__"):
        for col in time_col:
            if col in df.columns:
                time_col = col
                break

    df.index = pd.to_datetime(df[time_col], unit="s").dt.tz_localize(tz)
    df.drop(columns=[time_col], inplace=True)
    return df


def is_timestamp_contained(
    tdf: pd.DataFrame, timestamp: pd.Timestamp, time_col=None
) -> bool:
    """
    Return True if the timestamp is contained within the time range of the
    supplied timeseries dataframe.

    tdf: Timeseries dataframe (pd.DataFrame) with a time column.
    timestamp: The timestamp to test
    time_col: The name of the time column. When equals None the dataframe index
              will be used.

    """
    if time_col is None:
        beginning = tdf.index[0]
        end = tdf.index[-1]
    else:
        beginning = tdf[time_col].iloc[0]
        end = tdf[time_col].iloc[-1]
    return beginning < timestamp < end


def idx_for_time(df: pd.DataFrame, timestamp: pd.Timestamp, time_col=None) -> int:
    """
    Return the closest row index to the supplied timestamp.

    df: The dataframe to search
    timestamp: The timestamp that will be used to find the index
    time_col: The name of the time column. When equals None the dataframe index
              will be used.
    """
    if time_col is None:
        return df.index.get_loc(timestamp, method="nearest")
    else:
        return (df[time_col] - timestamp).abs().argmin()


def format_timedelta(td: pd.Timedelta, use_colons=True):
    total_secs = int(td.total_seconds())
    hrs = total_secs // 3600
    mins = (total_secs % 3600) // 60
    secs = (total_secs % 3600) % 60
    if use_colons:
        return f"{hrs:02}:{mins:02}:{secs:02}"
    else:
        return f"{hrs:02}{mins:02}{secs:02}"


def extract_clip(vid_path, start_frame: int, end_frame: int, output_path):
    """
    Extract a subclip of a video file without re-encoding it.

    vid_path: Path of the input video file (pathlib.Path or str).
    start_frame, end_frame: start and end of the subclip in frame numbers.
    output_path: Path for the output video file (pathlib.Path or str).
    """
    fps = mpy.VideoFileClip(str(vid_path)).fps
    start_time = start_frame / fps
    end_time = end_frame / fps

    ffmpeg_extract_subclip(vid_path, int(start_time), int(end_time), str(output_path))


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


def sessions_df(session_data_root: Path) -> pd.DataFrame:
    """
    Find all sessions under the supplied session_data_root argument.
    Return a pandas dataframe with columns `name` and `dir` and a
    DatetimeIndex containing the session start time.
    """
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


def session_stats(session_dir) -> dict:
    """
    Return a dictionary with statistics of the session in the supplied
    session_dir (Path or str) argument.
    """
    path = Path(session_dir)
    video_files = list(path.glob("*.mp4")) + list(path.glob("*.avi"))
    image_files = list(path.glob("*.png")) + list(path.glob("*.jpg"))
    csv_files = list(path.glob("*.csv"))

    return {
        "video_count": len(list(video_files)),
        "image_count": len(list(image_files)),
        "csv_count": len(list(csv_files)),
    }


def sessions_stats_df(sessions: pd.DataFrame) -> pd.DataFrame:
    """
    Return a dataframe containing statistics for each session in the supplied
    sessions argument.
    """
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


@dataclass(init=False, repr=False)
class VideoInfo:
    """
    Represents a single timestamped video file.
    Expects a timestamps csv file in the same directory with the same name
    as the video file but with a `.csv` suffix

    Attributes:
        name: Video name (without the start datetime)
        time: Video start time
        path: Video path
        timestamp_path: Timestamps csv path
        timestamps: The timestamps csv loaded using read_timeseries_csv()
        frame_count: Number of frames in the video (based on the timestamps file)
        duration: The total duration of the video (based on the timestamps file)
        src_id: The video image source id (based on the name attribute).
    """

    name: str
    time: pd.Timestamp
    path: Path
    timestamp_path: Path
    timestamps: pd.DataFrame
    frame_count: int
    duration: pd.Timestamp
    src_id: str

    def __init__(self, path: Path):
        """
        Return a new VideoInfo instance for the video file at the supplied path.
        """
        self.name, self.time = exp.split_name_datetime(path.stem)
        self.time = self.time.tz_localize(name_locale).tz_convert("utc")

        self.timestamp_path = path.parent / (path.stem + ".csv")
        if not self.timestamp_path.exists():
            self.timestamp_path = None
            self.duration = None
        else:
            self.timestamps = read_timeseries_csv(
                self.timestamp_path, time_col=["time", "timestamp"]
            )
            self.duration = self.timestamps.index[-1] - self.timestamps.index[0]

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
    """
    Represents a time position in a specific video.

    video: The VideoInfo representing the video matching this position
    timestamp: The time of the video position
    frame: The frame number of the video position (based on the timestamp)
    """

    video: VideoInfo
    timestamp: pd.Timestamp
    frame: int = None

    def __init__(self, video: VideoInfo, timestamp: pd.Timestamp):
        """
        Return a new instance with the supplied video and timestamp.
        """
        self.video = video
        self.timestamp = timestamp
        if self.video.timestamps is not None:
            self.frame = idx_for_time(self.video.timestamps, timestamp)


@dataclass(init=False)
class SessionInfo:
    """
    Represents a single session.

    Attributes:
        dir: The session directory
        session_state_path: The path of the session state json file
        session_state: The last recorded session state.
        videos: A list of all videos contained within the session
        images: A list of all image paths found in the session
        event_log_path: The path of the session event log
        event_log: A timeseries dataframe of the session event log
        head_bbox: A timeseries dataframe of the animal head bounding boxes
        head_centroids: A timeseries dataframe of the animal head centroids
        csvs: A list of paths to all other csvs found in the session.

    All of the dataframes in this class, as well as the session_state, are
    loaded on first access (lazily), except for VideoInfo.timestamps dataframe
    which is loaded when the object is created. To reload the data create a
    new object.
    """

    name: str
    time: pd.Timestamp
    dir: Path
    videos: [VideoInfo]
    images: [Path]
    event_log_path: Path
    csvs: [Path]
    session_state_path: Path
    session_state: dict

    def __init__(self, session_dir):
        """
        Instantiate a SessionInfo for the session at the supplied session_dir
        argument (Path or str).
        """
        session_dir = Path(session_dir)
        if not session_dir.exists():
            raise ValueError(f"Session directory doesn't exist: {str(session_dir)}")

        self.name, self.time = exp.split_name_datetime(session_dir.stem)
        self.time = self.time.tz_localize(name_locale).tz_convert("utc")        
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

        self._event_log = read_timeseries_csv(self.event_log_path)
        return self._event_log

    def filter_videos(
        self, videos=None, src_id: str = None, ts: pd.Timestamp = None
    ) -> [VideoInfo]:
        """
        Filter videos according to image source id or start time.

        videos: A list of VideoInfo objects to filter. When equals None, all
                session videos are used.
        src_id: When not None, return only videos recorded from this image
                source id.
        ts: When not None, return only videos with this start time.
        """
        if videos is None:
            videos = self.videos

        if src_id is not None:
            videos = filter(lambda v: v.src_id == src_id, videos)
        if ts is not None:
            videos = filter(lambda v: v.time == ts, videos)

        return list(videos)

    def video_position_at_time(
        self, timestamp: pd.Timestamp, videos=None
    ) -> [VideoPosition]:
        """
        Find all video files and frame numbers matching the supplied timestamp.
        Return a list of VideoPosition objects, one for each video that was
        recording during the time denoted by timestamp.

        videos: A list of VideoInfos that will be searched. When this is None,
                all of the videos in the session will be searched.
        """
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
        """
        Extract a clip from the session in this session.

        src_id: The image source id to use.
        start_time: Clip start time.
        end_time: Clip end time.
        output_dir: The directory that will contain the clip video file.
        file_prefix: An additional prefix for the output video filename.
        """
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
        fts = format_timedelta(relative_ts, use_colons=False)

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

        self._head_bbox = read_timeseries_csv(bbox_csvs[0])
        return self._head_bbox

    @property
    def head_centroids(self):
        head_bbox = self.head_bbox
        centroids = bbox.xyxy_to_centroid(head_bbox[["x1", "y1", "x2", "y2"]].values)
        df = pd.DataFrame(centroids, columns=["x", "y"])
        df.index = head_bbox.index
        df["confidence"] = head_bbox.confidence
        return df
