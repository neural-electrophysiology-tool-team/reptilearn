import numpy as np
import kleinberg_burst
import matplotlib.pyplot as plt
import pandas as pd
import analysis


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


def tag_motion(cent_vals,
               max_slow_speed=2, 
               min_slow_Z=1.7, 
               kleinberg_s=2,
               kleinberg_gamma=1,
               Z_win_size=100):
    
    diffs = np.diff(cent_vals, axis=0, prepend=np.nan)
    speeds = np.linalg.norm(diffs, axis=1)
    seqs = sliding_window(cent_vals, Z_win_size, keep_nans=True)

    Z = compute_zigzagity(seqs)

    fast_cents = (speeds[:-Z_win_size+1] > max_slow_speed) & ((Z < min_slow_Z) | np.isnan(Z))

    offsets = fast_cents.nonzero()[0]

    if len(offsets) > 0:
        fast_intervals = kleinberg_burst.kleinberg(offsets, s=kleinberg_s, gamma=kleinberg_gamma)
    else:
        fast_intervals = []
        
    return fast_intervals, speeds, Z, fast_cents


def intervals_to_segments(intervals, cent_df, hierarchy=1):    
    slow_segments = []
    fast_segments = []
    
    last_end = 0
    
    fast_intervals = list(filter(lambda i: i[0] == hierarchy, intervals))

    for i, (_, start, end) in enumerate(fast_intervals):
        slow_segments.append(cent_df.iloc[last_end : start])
        fast_segments.append(cent_df.iloc[start : end])
        last_end = end
        
    slow_segments.append(cent_df.iloc[last_end:])

    return slow_segments, fast_segments


def plot_stations(info, slow_segments, fast_segments, ax=None):
    if ax is None:
        _, ax = plt.subplots()
        
    for i, seg in enumerate(slow_segments):
        sd = np.nanstd(seg[["x", "y"]].values, axis=0)
        mean = np.nanmean(seg[["x", "y"]].values, axis=0)

        r = sum(sd)
        c = mean
        
        dur = seg.index[-1] - seg.index[0] if len(seg) > 0 else pd.Timedelta(0)
        ax.add_patch(plt.Circle(c, r, color='orange', alpha=0.8, zorder=2))
        ax.text(c[0], c[1], f"{i}|{dur.total_seconds():.0f}s", c='r')
        ax.scatter(seg.x, seg.y, s=10, alpha=0.5, marker='>', color='blue')
    
    for i, seg in enumerate(fast_segments):
        dur = seg.index[-1] - seg.index[0] if len(seg) > 0 else pd.Timedelta(0)
        
        #kf = create_kalman_filter([seg.x[0], 0, seg.y[0], 0])
        #k_x = pd.Series(dtype=np.float)
        #k_y = pd.Series(dtype=np.float)
        #for idx, row in seg.iloc[1:].iterrows():
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
        ax.plot(seg.x, seg.y, c='green')
        #seg_nona = seg.dropna()
        #posx = seg_nona.x[len(seg_nona)//2]
        #posy = seg_nona.y[len(seg_nona)//2]
        #ax.text(posx, posy, f"{i}|{dur.total_seconds():.0f}s", c='blue')
    ax.axes.set_aspect('equal')
    ax.set_xlim(0, 1440)
    ax.set_ylim(0, 1080)
    ax.invert_yaxis()    

    
# experiment runs (consider putting in analysis.py)
def get_experiment_runs(info):
    try:
        event_log = info.event_log
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return []
        
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

        if len(run_events.index) > i+1:
            if stop < run_events.index[i+1]:
                runs.append((run, stop))
        else:
            runs.append((run, stop))
    return runs


def between_rewards_segs(info):
    runs = get_experiment_runs(info)
    if len(runs) == 0:
        print(f"WARNING: Could not find experiment runs in session ({info.dir})")
        return []

    rewards = info.event_log[(info.event_log.event == "dispensing_reward") | (info.event_log.event == "dispencing_reward") ]

    if len(rewards) == 0:
        rewards = info.event_log[(info.event_log.event == "('session', 'cur_trial')") & (info.event_log.value != '0')]
    if len(rewards) == 0:
        rewards = info.event_log[(info.event_log.event == "('experiment', 'cur_trial')") & (info.event_log.value != '0')]
    if len(rewards) == 0:
        rewards = info.event_log[(info.event_log.event == "arena/dispense_reward")]
    if len(rewards) == 0:
        print(info.dir, "(could not find rewards)")

    rewards_per_run = []

    for run in runs:
        rewards_per_run.append(rewards[run[0]:run[1]])
    
    segs = []
    for run_rewards in rewards_per_run:
        for i in range(len(run_rewards.index)-1):
            segs.append((run_rewards.index[i], run_rewards.index[i+1]))    
    return segs


def plot_trajectories(info, seg, outpath, idx, hierarchy=1):
    if seg[1]-seg[0] == pd.Timedelta(0):
        return

    if seg[1]-seg[0] > pd.Timedelta(hours=3):
        return

    partial_cents = info.head_centroids.copy()[seg[0]:seg[1]]    
    cent_vals = partial_cents[["x", "y"]].values
    sseg = "-".join([t.strftime("%H:%M:%S") for t in seg])
    print(sseg, '\n', '==============')
    if len(cent_vals) == 0:
        return
    
    intervals, speeds, Z, fast_cents = tag_motion(cent_vals, min_slow_Z=1.8, max_slow_speed=3)
    slow_segments, fast_segments = intervals_to_segments(intervals, partial_cents, hierarchy=hierarchy)

    background = analysis.background_for_ts(info, seg[0], "area")
    
    fig = plt.figure()
    ax = fig.gca()

    if background is not None:
        ax.imshow(background)

    plot_stations(info, slow_segments, fast_segments, ax=ax)
    
    if len(partial_cents) > 0:
        dur = partial_cents.index[-1] - partial_cents.index[0]
    else:
        dur = 0
    
    total_stationary = pd.Series([seg.index[-1] - seg.index[0] for seg in slow_segments if len(seg) > 0]).sum()
    percent_stationary = total_stationary.total_seconds() / dur.total_seconds()
    ax.set_title(f"{sseg} dur: {dur} stationary: {100 * percent_stationary:.2f}%")    
    fig.tight_layout()
    fig.savefig(str(outpath) + f"_traj_ir{idx}.pdf")
    fig.clear()
    plt.close()
    plt.cla()
    plt.clf()


def motion_stats(info, start: pd.Timestamp, end: pd.Timestamp):
    start_idx = analysis.idx_for_time(info.head_centroids, start)
    end_idx = analysis.idx_for_time(info.head_centroids, end)
    partial_cents = info.head_centroids[["x", "y"]].iloc[start_idx:end_idx].copy()
    print(len(partial_cents), '<=len(partial_cents)')
    sseg = "-".join([t.strftime("%H:%M:%S") for t in (start, end)])
    print(sseg, '\n', '==============')
    if len(partial_cents) <= 2:
        return 0, 0, 0, np.nan
    
    intervals, speeds, Z, fast_cents = tag_motion(partial_cents.values, min_slow_Z=1.8, max_slow_speed=3)
    slow_segments, fast_segments = intervals_to_segments(intervals, partial_cents, hierarchy=1)
    fsum = 0
    flen = 0
    for fs in fast_segments:
        fs['diffx'] = fs.x.diff()
        fs['diffy'] = fs.y.diff()        
        fs['dist2'] = np.sqrt(fs.diffx**2 + fs.diffy**2)
        fsum += fs.dist2.sum()
        flen += len(fs)
    
    total_stationary = pd.Series([seg.index[-1] - seg.index[0] for seg in slow_segments if len(seg) > 0]).sum()
    fraction_stationary = total_stationary.total_seconds() / (end-start).total_seconds()
    
    return fsum, flen, len(slow_segments), fraction_stationary
