from __future__ import annotations

import sys

import release_publisher as publisher
from release_overlap_policy import verify_git_overlap


def publish():
    publisher.verify_git_overlap = lambda assets: verify_git_overlap(assets, publisher=publisher)
    publisher.publish()


COMMANDS = {
    "plan": publisher.plan,
    "canary": publisher.canary,
    "publish": publish,
    "install-manifest": publisher.install_manifest,
}


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit("usage: publish_deep_history.py plan|canary|publish|install-manifest")
    COMMANDS[sys.argv[1]]()
