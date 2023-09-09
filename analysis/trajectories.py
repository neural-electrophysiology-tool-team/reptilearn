import numpy as np
import kleinberg_burst
import matplotlib.pyplot as plt
import pandas as pd
import analysis
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
from scipy.special import logsumexp
import scipy.signal as sig
from scipy import stats
from sklearn.decomposition import PCA


def compute_zigzagity(seq_data):
    """
    :param seq_data: 3D sequence array
    :return: mean "Zigzagity", which is the angle difference between consecutive velocity vectors in the sequence
    """
    vecs = seq_data[:, 1:] - seq_data[:, :-1]
    u = vecs[:, 1:]
    v = vecs[:, :-1]
    u_norm = np.linalg.norm(u, axis=2)
    v_norm = np.linalg.norm(v, axis=2)
    dotprods = np.einsum(
        "ij,ij->i", u.reshape(-1, u.shape[2]), v.reshape(-1, v.shape[2])
    ).reshape(u.shape[0], u.shape[1])
    angles = np.arccos(dotprods / (u_norm * v_norm))
    return angles.mean(axis=1)


def mask_zgzg(min_zgzg, max_zgzg, by_X=True, by_Y=True):
    def f(X, Y):
        zgzgs_X = compute_zigzagity(X[:, :, :2])
        zgzgs_Y = compute_zigzagity(Y[:, :, :2])

        ret_mask = np.array([True] * X.shape[0])

        if by_X:
            ret_mask = ret_mask & ((zgzgs_X > min_zgzg) & (zgzgs_X < max_zgzg))
        if by_Y:
            ret_mask = ret_mask & ((zgzgs_Y > min_zgzg) & (zgzgs_Y < max_zgzg))
        return ret_mask

    return f


def sliding_window(
    data,
    seq_size,
    keep_nans=False,
    mask_fn=None,
):
    """
    :param df: dataframe with the trial's detections
    :param labels: list of str, features to be used in the input sequence (xyxy for example)
    :param seq_size: int, length of the X sequence
    :param keep_nans: bool, whether to keep sequences with NaN
    :param mask_fn: boolean bask function, to filter data before creating the tensor
    :return: tuple X, 3D tensors of sequences
    """

    arrays_2d = []
    inds_range = data.shape[0] - seq_size + 1

    for i in range(inds_range):
        seq = data[i : i + seq_size]

        if (not keep_nans) and np.any(np.isnan(seq)):
            continue

        arrays_2d.append(seq)

    if len(arrays_2d) == 0:
        return None

    X = np.stack(arrays_2d)

    if mask_fn is not None:
        mask = mask_fn(X)
        X = X[mask]

    return X


def kleinberg_to_idxs(intervals, n, hierarchy=1):
    arr = np.zeros(n, dtype=bool)
    for interval in intervals:
        if interval[0] == hierarchy:
            for i in range(interval[1], interval[2]):
                if i < len(arr):
                    arr[i] = True
    return arr


def tag_motion_simple(cent_vals, max_slow_speed=2, kleinberg_s=2, kleinberg_gamma=1):
    """
    Find fast/slow time intervals based on speed thresholding and kleinberg's burst algorithm
    """
    diffs = np.diff(cent_vals, axis=0, prepend=np.nan)
    speeds = np.linalg.norm(diffs, axis=1)

    fast_cents = speeds > max_slow_speed
    offsets = fast_cents.nonzero()[0]
    print("sumfast", fast_cents.sum(), offsets[-1])

    if len(offsets) > 0:
        fast_intervals = kleinberg_burst.kleinberg(
            offsets, s=kleinberg_s, gamma=kleinberg_gamma
        )
    else:
        fast_intervals = []

    return fast_intervals


def tag_motion(
    cent_vals,
    max_slow_speed=2,
    min_slow_Z=1.7,
    kleinberg_s=2,
    kleinberg_gamma=1,
    Z_win_size=100,
):

    diffs = np.diff(cent_vals, axis=0, prepend=np.nan)
    speeds = np.linalg.norm(diffs, axis=1)
    seqs = sliding_window(cent_vals, Z_win_size, keep_nans=True)

    Z = compute_zigzagity(seqs)

    fast_cents = (speeds[: -Z_win_size + 1] > max_slow_speed) & (
        (Z < min_slow_Z) | np.isnan(Z)
    )

    offsets = fast_cents.nonzero()[0]

    if len(offsets) > 0:
        fast_intervals = kleinberg_burst.kleinberg(
            offsets, s=kleinberg_s, gamma=kleinberg_gamma
        )
    else:
        fast_intervals = []

    return fast_intervals, speeds, Z, fast_cents


def intervals_to_segments(intervals, cent_df, hierarchy=1):
    slow_segments = []
    fast_segments = []

    last_end = 0

    fast_intervals = list(filter(lambda i: i[0] == hierarchy, intervals))

    for i, (_, start, end) in enumerate(fast_intervals):
        slow_segments.append(cent_df.iloc[last_end:start])
        fast_segments.append(cent_df.iloc[start:end])
        last_end = end

    slow_segments.append(cent_df.iloc[last_end:])

    return slow_segments, fast_segments


def plot_stations(
    info,
    slow_segments,
    fast_segments,
    ax=None,
    station_radius="sd",
    draw_text=True,
    draw_fast_segs=True,
):
    if ax is None:
        _, ax = plt.subplots()

    for i, seg in enumerate(slow_segments):
        sd = np.nanstd(seg[["x", "y"]].values, axis=0)
        mean = np.nanmean(seg[["x", "y"]].values, axis=0)

        r = sum(sd) if station_radius == "sd" else station_radius
        c = mean

        dur = seg.index[-1] - seg.index[0] if len(seg) > 0 else pd.Timedelta(0)
        ax.add_patch(plt.Circle(c, r, color="orange", alpha=0.8, zorder=2, linewidth=0))
        if draw_text:
            if station_radius == "sd":
                textx, texty = c[0], c[1]
            else:
                textx, texty = c[0] + station_radius * 2, c[1] - station_radius * 2
            ax.text(textx, texty, f"{i}|{dur.total_seconds():.0f}s", c="r")

        ax.scatter(seg.x, seg.y, s=10, alpha=0.5, marker=".", color="blue")

    if draw_fast_segs:
        for i, seg in enumerate(fast_segments):
            dur = seg.index[-1] - seg.index[0] if len(seg) > 0 else pd.Timedelta(0)

            # kf = create_kalman_filter([seg.x[0], 0, seg.y[0], 0])
            # k_x = pd.Series(dtype=np.float)
            # k_y = pd.Series(dtype=np.float)
            # for idx, row in seg.iloc[1:].iterrows():
            #    kf.predict()
            #    loc = row[["x", "y"]]
            #    if np.isnan(loc.values).any():
            #        kf.update([kf.x[0], kf.x[2]])
            #    else:
            #        kf.update(loc)
            #
            #    k_x[idx] = kf.x[0]
            #    k_y[idx] = kf.x[2]

            # ax.plot(k_x, k_y, c='yellow')
            ax.plot(seg.x, seg.y, c="green")
            # seg_nona = seg.dropna()
            # posx = seg_nona.x[len(seg_nona)//2]
            # posy = seg_nona.y[len(seg_nona)//2]
            # ax.text(posx, posy, f"{i}|{dur.total_seconds():.0f}s", c='blue')

    ax.axes.set_aspect("equal")
    ax.set_xlim(0, 1440)
    ax.set_ylim(0, 1080)
    ax.invert_yaxis()


# experiment runs (consider putting in analysis.py)
def get_experiment_runs(info):
    run_events = info.event_log[info.event_log.event == "session/run"]
    stop_events = info.event_log[info.event_log.event == "session/stop"]
    if len(run_events) == 0 and len(stop_events) == 0:
        run_events = info.event_log[info.event_log.event == "experiment/run"]
        stop_events = info.event_log[info.event_log.event == "experiment/end"]
    runs = []
    for i, run in enumerate(run_events.index):
        events = stop_events[run:]
        if len(events) != 0:
            stop = events.index[0]
        else:
            print("WARNING: could not find matching stop event")
            break

        if len(run_events.index) > i + 1:
            if stop < run_events.index[i + 1]:
                runs.append((run, stop))
        else:
            runs.append((run, stop))
    return runs


def between_rewards_segs(info):
    runs = get_experiment_runs(info)
    if len(runs) == 0:
        print(f"WARNING: Could not find experiment runs in session ({info.dir})")
        return []

    rewards = info.event_log[
        (info.event_log.event == "dispensing_reward")
        | (info.event_log.event == "dispencing_reward")
    ]

    if len(rewards) == 0:
        rewards = info.event_log[
            (info.event_log.event == "('session', 'cur_trial')")
            & (info.event_log.value != "0")
        ]
    if len(rewards) == 0:
        rewards = info.event_log[
            (info.event_log.event == "('experiment', 'cur_trial')")
            & (info.event_log.value != "0")
        ]
    if len(rewards) == 0:
        rewards = info.event_log[(info.event_log.event == "arena/dispense_reward")]
    if len(rewards) == 0:
        print(info.dir, "(could not find rewards)")

    rewards_per_run = []

    for run in runs:
        rewards_per_run.append(rewards[run[0] : run[1]])

    segs = []
    for run_rewards in rewards_per_run:
        for i in range(len(run_rewards.index) - 1):
            segs.append((run_rewards.index[i], run_rewards.index[i + 1]))
    return segs


def plot_trajectories(info, seg, outpath, idx, hierarchy=1, station_radius="sd"):
    if seg[1] - seg[0] == pd.Timedelta(0):
        raise ValueError("Invalid segment start or end")

    partial_cents = info.head_centroids[seg[0] : seg[1]].copy()
    cent_vals = partial_cents[["x", "y"]].values
    sseg = " - ".join([t.strftime("%H:%M:%S") for t in seg])
    print(sseg, "\n", "==============")
    if len(cent_vals) == 0:
        return

    intervals, speeds, Z, fast_cents = tag_motion(
        cent_vals, min_slow_Z=1.8, max_slow_speed=3
    )
    slow_segments, fast_segments = intervals_to_segments(
        intervals, partial_cents, hierarchy=hierarchy
    )

    background = analysis.background_for_ts(info, seg[0], "area")

    fig = plt.figure()
    ax = fig.gca()

    if background is not None:
        ax.imshow(background)

    plot_stations(
        info, slow_segments, fast_segments, ax=ax, station_radius=station_radius
    )

    if len(partial_cents) > 0:
        dur = partial_cents.index[-1] - partial_cents.index[0]
    else:
        dur = 0

    total_stationary = pd.Series(
        [seg.index[-1] - seg.index[0] for seg in slow_segments if len(seg) > 0]
    ).sum()
    percent_stationary = total_stationary.total_seconds() / dur.total_seconds()
    ax.set_title(f"{sseg}, {100 * percent_stationary:.2f}% stationary")
    plt.tick_params(
        left=False, right=False, labelleft=False, labelbottom=False, bottom=False
    )
    fig.tight_layout()
    fig.savefig(str(outpath) + f"_traj_ir{idx}.pdf", dpi=200)
    fig.clear()
    plt.close()
    plt.cla()
    plt.clf()


def motion_stats(
    df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, columns=["x", "y"]
):
    start_idx = analysis.idx_for_time(df, start)
    end_idx = analysis.idx_for_time(df, end)
    partial_cents = df[columns].iloc[start_idx:end_idx].copy()
    sseg = " - ".join([t.strftime("%H:%M:%S") for t in (start, end)])
    print(sseg, "\n", "==============")
    if len(partial_cents) <= 2:
        return 0, 0, 0, np.nan

    intervals, speeds, Z, fast_cents = tag_motion(
        partial_cents.values, min_slow_Z=1.8, max_slow_speed=3
    )
    slow_segments, fast_segments = intervals_to_segments(
        intervals, partial_cents, hierarchy=1
    )
    fsum = 0
    flen = 0
    for fs in fast_segments:
        fs["diffx"] = fs.x.diff()
        fs["diffy"] = fs.y.diff()
        fs["dist"] = np.sqrt(fs.diffx**2 + fs.diffy**2)
        fsum += fs.dist.sum()
        flen += len(fs)

    total_stationary = pd.Series(
        [seg.index[-1] - seg.index[0] for seg in slow_segments if len(seg) > 0]
    ).sum()
    fraction_stationary = (
        total_stationary.total_seconds() / (end - start).total_seconds()
    )

    return fsum, flen, len(slow_segments), fraction_stationary


def remove_dups(pts, thres=7):
    tindex = np.repeat(np.arange(pts.shape[0])[:, None], pts.shape[1], axis=1) * 100
    pts_ix = np.dstack([pts, tindex])
    tree = cKDTree(pts_ix.reshape(-1, 3))

    shape = (pts.shape[0], pts.shape[1])
    pairs = tree.query_pairs(thres)
    indices = [b for a, b in pairs]

    if len(pairs) == 0:
        return pts

    i0, i1 = np.unravel_index(indices, shape)
    pts_out = np.copy(pts)
    pts_out[i0, i1] = np.nan

    return pts_out


def viterbi_path(points, scores, n_back=3, thres_dist=30):
    n_frames = points.shape[0]

    points_nans = remove_dups(points, thres=5)
    # points_nans[scores < 0.01] = np.nan

    num_points = np.sum(~np.isnan(points_nans[:, :, 0]), axis=1)
    num_max = np.max(num_points)

    particles = np.zeros((n_frames, num_max * n_back + 1, 3), dtype="float64")
    valid = np.zeros(n_frames, dtype="int64")
    for i in range(n_frames):
        s = 0
        for j in range(n_back):
            if i - j < 0:
                break
            ixs = np.where(~np.isnan(points_nans[i - j, :, 0]))[0]
            n_valid = len(ixs)
            if n_valid > 0:
                particles[i, s : s + n_valid, :2] = points[i - j, ixs]
                particles[i, s : s + n_valid, 2] = scores[i - j, ixs] * np.power(
                    2.0, -j
                )
                s += n_valid
        if s == 0:
            particles[i, 0] = [-1, -1, 0.001]  # missing point
            s = 1
        valid[i] = s

    # viterbi algorithm
    n_particles = np.max(valid)

    T_logprob = np.zeros((n_frames, n_particles), dtype="float64")
    T_logprob[:] = -np.inf
    T_back = np.zeros((n_frames, n_particles), dtype="int64")

    T_logprob[0, : valid[0]] = np.log(particles[0, : valid[0], 2])
    T_back[0, :] = -1

    for i in range(1, n_frames):
        va, vb = valid[i - 1], valid[i]
        pa = particles[i - 1, :va, :2]
        pb = particles[i, :vb, :2]

        dists = cdist(pa, pb)
        cdf_high = stats.norm.logcdf(dists + 2, scale=thres_dist)
        cdf_low = stats.norm.logcdf(dists - 2, scale=thres_dist)
        cdfs = np.array([cdf_high, cdf_low])
        P_trans = logsumexp(cdfs.T, b=[1, -1], axis=2)

        P_trans[P_trans < -100] = -100

        # take care of missing transitions
        P_trans[pb[:, 0] == -1, :] = np.log(0.001)
        P_trans[:, pa[:, 0] == -1] = np.log(0.001)

        pflat = particles[i, :vb, 2]
        possible = T_logprob[i - 1, :va] + P_trans

        T_logprob[i, :vb] = np.max(possible, axis=1) + np.log(pflat)
        T_back[i, :vb] = np.argmax(possible, axis=1)

    out = np.zeros(n_frames, dtype="int")
    out[-1] = np.argmax(T_logprob[-1])

    for i in range(n_frames - 1, 0, -1):
        out[i - 1] = T_back[i, out[i]]

    trace = [particles[i, out[i]] for i in range(n_frames)]
    trace = np.array(trace)

    points_new = trace[:, :2]
    scores_new = trace[:, 2]
    # scores_new[out >= num_points] = 0

    return points_new, scores_new


def df_to_traj(df: pd.DataFrame):
    df = df[["x", "y", "confidence"]]
    df = df.interpolate(method="time").dropna()  # remove leading nans
    arr = df[["x", "y"]].values

    return arr


def median_filter(traj, winsize=51):
    traj = np.vstack(
        [sig.medfilt(traj[:, 0], winsize), sig.medfilt(traj[:, 1], winsize)]
    ).T


def gaussian_filter(traj, winsize=101):
    gaussian = sig.windows.gaussian(winsize, round(winsize / 3))
    return np.vstack(
        [
            sig.convolve(traj[:, 0], gaussian, mode="same") / sum(gaussian),
            sig.convolve(traj[:, 1], gaussian, mode="same") / sum(gaussian),
        ]
    ).T


# NEW MOTION SEGMENTATION ANALYSIS
# =================================

# https://stackoverflow.com/questions/48967169/time-delay-embedding-of-time-series-in-python
def time_delay_embedding(tr, w, g):
    """Return time delay embedding of tr with window size `w` and gap size `g`"""
    return tr[
        (np.arange(w) * (g + 1))
        + np.arange(np.max(tr.shape[0] - (w - 1) * (g + 1), 0)).reshape(-1, 1)
    ]


def comp_intervals_for(intervals, start, end):
    comp_intervals = []

    for i, (s, e) in enumerate(intervals):
        if i == 0 and s > start:
            comp_intervals.append((start, s))

        if i == len(intervals) - 1:
            if e < end:
                comp_intervals.append((e, end - 1))
        else:
            s_next = intervals[i + 1][0]
            comp_intervals.append((e, s_next))

    return comp_intervals


def grow_interval(interval, sig, rate_thresh=0.02):
    s, e = interval
    d = np.diff(sig)

    # back
    while True:
        if s <= 0:
            break
        if np.abs(d[s]) <= rate_thresh:
            break

        s -= 1

    # forward
    while True:
        if e >= len(d) - 1:
            break
        if np.abs(d[e]) <= rate_thresh:
            break

        e += 1

    return s, e


def kleinberg_segment_mask(mask, kleinberg_s=2, kleinberg_gamma=1):
    offsets = mask.nonzero()[0]

    if len(offsets) > 0:
        intervals = kleinberg_burst.kleinberg(
            offsets, s=kleinberg_s, gamma=kleinberg_gamma
        )
    else:
        intervals = []

    return intervals


def motion_segmentation(
    tr,
    n_pca_components=6,
    td_winsize=50,
    td_gap=2,
    pca_thresh=20,
    gauss_filter_winsize=51,
    kleinberg_s=10,
    kleinberg_gamma=1,
    start=0,
    end=None,
):
    print("Interpolating and filtering")

    tr = df_to_traj(tr)
    tr = gaussian_filter(tr, winsize=gauss_filter_winsize)

    print("Calculating delay embedding PCA")
    tr_wins = time_delay_embedding(tr, td_winsize, td_gap)
    tr_wins_diff = np.diff(tr_wins, axis=1)

    flat_wins_diff = tr_wins_diff.reshape(tr_wins_diff.shape[0], -1)
    pca_flat = PCA(n_components=n_pca_components)
    pca_flat.fit(flat_wins_diff)
    tr_pca_flat = pca_flat.transform(flat_wins_diff)

    pcanorms = np.linalg.norm(tr_pca_flat, axis=1)

    eps = 100
    prev_last_offset = None

    all_intervals = []
    s = start
    if end is None:
        end = pcanorms.shape[0]

    print(f"Segmenting trajectory. Total length: {len(pcanorms)}")

    while True:
        print("Starting:", s)
        intervals = kleinberg_segment_mask(
            pcanorms[s:] > pca_thresh, kleinberg_s, kleinberg_gamma
        )
        if len(intervals) == 0:
            break

        hier_intervals = [
            np.array([i for i in intervals if i[0] == h])
            for h in np.arange(intervals[:, 0].max() + 1)
        ]

        if len(hier_intervals) < 2:
            break

        hi = hier_intervals[1]
        hi[:, 1:] += s
        all_intervals.append(hi)
        last_offset = np.array(hi)[:, 2].max()
        print("End: ", last_offset)
        if last_offset == prev_last_offset:
            break

        if end - last_offset > eps:
            s = last_offset + 1
            prev_last_offset = last_offset
        else:
            break

    if len(all_intervals) > 0:
        samp_intervals = np.vstack(all_intervals)[:, 1:]
        grown_intervals = [grow_interval(i, pcanorms) for i in samp_intervals]
        comp_grown_intervals = comp_intervals_for(grown_intervals, start, end)
    else:
        print("No intervals found!")
        return [], []

    print("Done")

    return grown_intervals, comp_grown_intervals
