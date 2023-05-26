import os
from execute import execute
import requests
import dateutil


git = os.environ.get("GIT", "git")
repo = "neural-electrophysiology-tool-team/reptilearn"


def _get_commit_hash(cwd=None):
    return execute([git, "rev-parse", "HEAD"], cwd=cwd)


def _get_commit_date(cwd=None):
    return execute([git, "show", "-s", "--format=%ci", "HEAD"])


def _get_latest_commit():
    commits = requests.get(
        f"https://api.github.com/repos/{repo}/branches/master"
    ).json()
    return commits["commit"]["sha"], commits["commit"]["commit"]["author"]["date"]


def version_check():
    """
    Compare local git repo commit hash to latest commit hash on github
    """
    try:
        commit = _get_commit_hash()
        ts = _get_commit_date()
    except Exception as e:
        if e.args[1] == 128:
            print("WARNING: Can't check version. Not inside a git repository")
            return

        print("WARNING: Error getting commit hash during update check: ", e)
        return

    last_commit, last_ts = _get_latest_commit()

    ts = dateutil.parser.parse(ts).astimezone()
    last_ts = dateutil.parser.parse(last_ts).astimezone()

    if last_commit == commit:
        print(f"Installed version ({commit[:7]}, {ts}) is up to date.")
    else:
        if last_ts > ts:
            print(
                f"NOTE: Installed version ({commit[:7]}, {ts}) is outdated. Run `git pull` to update to the latest version ({last_commit[:7]}, {last_ts})"
            )
        else:
            print(f"WARNING: Installed version ({commit[:7]}, {ts}) is newer than the latest master version ({last_commit[:7]}, {last_ts}).")
