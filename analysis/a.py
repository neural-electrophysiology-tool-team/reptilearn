import pandas as pd
import numpy as np


# example of reading video timestamp csv file.
def date_parser(epoch_ns):
    return pd.to_datetime(epoch_ns).tz_localize("UTC").tz_convert("Asia/Jerusalem")


tdf = pd.read_csv(
    "videos/20349302_20210202-181027.csv",
    dtype={"timestamp": np.long},
    index_col="timestamp",
    parse_dates=True,
    date_parser=date_parser,
)

diff_secs = tdf.index.to_series().diff() / np.timedelta64(1, 's')
freq = 1 / diff_secs
fps = freq.mean()
sd_fps = freq.std()

