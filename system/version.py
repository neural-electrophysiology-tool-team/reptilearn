import os
from execute import execute
import requests


git = os.environ.get("GIT", "git")
repo = "neural-electrophysiology-tool-team/reptilearn"


def get_commit_hash(cwd=None):
    return execute(["git", "rev-parse", "HEAD"], cwd=cwd)


def get_latest_commit():
    commits = requests.get(
        f"https://api.github.com/repos/{repo}/branches/master"
    ).json()
    return commits["commit"]["sha"]


def version_check():
    try:
        commit = get_commit_hash()
    except Exception as e:
        if e.args[1] == 128:
            print("WARNING: Can't check version. Not inside a git repository")
            return

        print("WARNING: Error getting commit hash: ", e)
        return

    last_commit = get_latest_commit()
    if last_commit == commit:
        print(f"Installed version {commit[:7]} is up to date.")
    else:
        print(
            f"Installed version {commit[:7]} is outdated. You can update to version {last_commit[:7]} by running `git pull`"
        )
