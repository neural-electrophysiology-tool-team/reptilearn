import datetime
import os
from execute import execute
import requests
import dateutil


git = os.environ.get("GIT", "git")
repo = "neural-electrophysiology-tool-team/reptilearn"

installed_commit_hash = None
installed_commit_ts = None
latest_commit_hash = None
latest_commit_ts = None


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
    global installed_commit_ts, installed_commit_hash, latest_commit_hash, latest_commit_ts
    try:
        installed_commit_hash = _get_commit_hash()
        installed_commit_ts = _get_commit_date()
    except Exception as e:
        if e.args[1] == 128:
            print("WARNING: Can't check version. Not inside a git repository")
            return

        print("WARNING: Error getting commit hash during update check: ", e)
        return

    latest_commit_hash, latest_commit_ts = _get_latest_commit()

    installed_commit_ts = dateutil.parser.parse(installed_commit_ts).astimezone(datetime.timezone.utc)
    latest_commit_ts = dateutil.parser.parse(latest_commit_ts).astimezone(datetime.timezone.utc)

    if latest_commit_hash == installed_commit_hash:
        print(f"Installed version ({installed_commit_hash[:7]}, {installed_commit_ts}) is up to date.")
    else:
        if latest_commit_ts > installed_commit_ts:
            print(
                f"NOTE: Installed version ({installed_commit_hash[:7]}, {installed_commit_ts}) is outdated. Run `git pull` to update to the latest version ({latest_commit_hash[:7]}, {latest_commit_ts})"
            )
        else:
            print(
                f"WARNING: Installed version ({installed_commit_hash[:7]}, {installed_commit_ts}) is newer than the latest master version ({latest_commit_hash[:7]}, {latest_commit_ts})."
            )
