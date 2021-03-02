import pandas as pd
import numpy as np


# example of reading video timestamp csv file.
def date_parser(epoch_ns):
    return pd.to_datetime(epoch_ns).tz_localize("UTC").tz_convert("Asia/Jerusalem")


def analyze_timestamp_csv(csv_path):
    tdf = pd.read_csv(
        csv_path,
        dtype={"timestamp": np.long},
        index_col="timestamp",
        parse_dates=True,
        date_parser=date_parser,
    )

    diff_secs = tdf.index.to_series().diff() / np.timedelta64(1, 's')
    freq = 1 / diff_secs
    fps = freq.mean()
    sd_fps = freq.std()
    n = len(tdf)

    return n, diff_secs, freq, fps, sd_fps, tdf


csvs = {
    "20349310": "videos/20349310_20210222-133916.csv",
    "20349302": "videos/20349302_20210222-133916.csv",
    "0138A051": "videos/0138A051_20210222-133916.csv",
}
