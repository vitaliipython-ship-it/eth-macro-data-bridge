from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import release_publisher as release

TAG = "d9-warm-release-policy-probe-v1"
ASSET = "policy-probe.json"


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def main() -> None:
    payload = {
        "schema_version": "d9-warm-release-policy-probe/1.0.0",
        "purpose": "NON_PRODUCTION_RELEASE_POLICY_QUALIFICATION",
        "repository": "vitaliipython-ship-it/eth-macro-data-bridge",
    }
    raw = compact(payload)
    expected = hashlib.sha256(raw).hexdigest()
    current = release.release_by_tag(TAG)
    if current is None:
        current = release.gh(
            "/releases",
            method="POST",
            payload={
                "tag_name": TAG,
                "target_commitish": os.environ.get("GITHUB_SHA", "main"),
                "name": TAG,
                "body": "NON-PRODUCTION D9 WARM Release policy qualification. No market data authority.",
                "draft": True,
                "prerelease": True,
            },
        )
        temp = Path(os.environ.get("RUNNER_TEMP", ".tmp")) / ASSET
        temp.parent.mkdir(parents=True, exist_ok=True)
        temp.write_bytes(raw)
        asset = {"asset_name": ASSET, "local_path": str(temp), "size_bytes": len(raw), "sha256": expected}
        release.upload_verified(current, asset)
        current = release.gh(
            f"/releases/{current['id']}",
            method="PATCH",
            payload={"draft": False, "prerelease": True},
        )
    current = release.gh(f"/releases/{current['id']}")
    assets = {item["name"]: item for item in release.list_assets(current["id"])}
    found = assets.get(ASSET)
    if found is None:
        raise RuntimeError("WARM release policy probe asset missing")
    remote = release.download_release_asset(found["id"])
    if len(remote) != len(raw):
        raise RuntimeError("WARM release policy probe remote size mismatch")
    if hashlib.sha256(remote).hexdigest() != expected:
        raise RuntimeError("WARM release policy probe remote SHA mismatch")
    immutable = bool(current.get("immutable"))
    print("WARM_RELEASE_POLICY_PROBE=PASS")
    print("WARM_RELEASE_PRERELEASE=true")
    print(f"WARM_RELEASE_PUBLISHED_IMMUTABLE={'true' if immutable else 'false'}")
    print(f"WARM_RELEASE_MUTABLE_IN_PLACE={'NO' if immutable else 'POTENTIALLY_YES_REQUIRES_MUTATION_TEST'}")
    print("REMOTE_BINARY_READBACK=PASS")
    print("REMOTE_SIZE_MATCH=PASS")
    print("REMOTE_SHA256_MATCH=PASS")
    print("MARKET_DATA_AUTHORITY_CHANGED=false")


if __name__ == "__main__":
    main()
