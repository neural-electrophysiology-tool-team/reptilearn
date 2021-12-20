import os
import sys
from pathlib import Path
import pandas as pd

os.chdir('/Users/eisental/dev/lab/reptilearn/system')
sys.path.append('/Users/eisental/dev/lab/reptilearn/analysis')
sys.path.append('/Users/eisental/dev/lab/reptilearn/system')
import analysis
import trajectories as traj


session_data_root = Path("/Users/eisental/dev/lab/reptilearn_sessions/pv56")
sessions = analysis.sessions_df(session_data_root)
index = sessions.index
sessions = pd.concat([sessions.reset_index(drop=True), analysis.sessions_stats_df(sessions)], axis=1)
sessions.index = index

info = analysis.SessionInfo(sessions.iloc[0].dir)

segs = traj.between_rewards_segs(info)
print(len(segs))

for i, seg in enumerate(segs[214:]):
    print(f"Segment {i + 214} / {len(segs)}")
    traj.plot_trajectories(info, seg, Path('../analysis/figures') / f'{info.dir.stem}', i + 214)
