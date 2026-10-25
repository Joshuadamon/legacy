#!/usr/bin/env python3
"""Replay local commits to GitHub via the git database API, preserving history.
Local git push is blocked: the egress proxy CONNECT-tunnels github.com, so the
credential surrogate never gets exchanged. This replays commits via the API.
Usage: python3 gh_replay.py  (replays origin/main..HEAD)"""
import sys, subprocess, json, base64
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request
import urllib.request, urllib.error

OWNER, REPO = "Joshuadamon", "legacy"
WORKDIR = "/home/hatch/workspace/repos/legacy"

def gh(method, path, data=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{OWNER}/{REPO}{path}",
        data=json.dumps(data).encode() if data else None,
        headers={"User-Agent": "Muse", "Accept": "application/vnd.github+json", "Content-Type": "application/json"},
        method=method)
    add_surrogate_to_request(req, "custom.github", entry_name="access_token", allowed_hosts=["api.github.com"])
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return resp.status, json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode(errors="replace")

def git(*args):
    return subprocess.run(["git", "-C", WORKDIR, *args], capture_output=True, text=True, check=True).stdout

lines = git("log", "origin/main..HEAD", "--reverse", "--format=%H|%an|%ae|%ad|%s", "--date=iso").strip().split("\n")
if lines == [""]:
    print("Nothing to push — local is in sync with origin/main.")
    sys.exit(0)
blob_cache = set()
parent_sha = git("rev-parse", "origin/main").strip()
print(f"Starting from origin/main={parent_sha[:8]}, replaying {len(lines)} commits")

for line in lines:
    sha, an, ae, ad, subject = line.split("|", 4)
    body = git("log", "-1", "--format=%B", sha).strip()
    entries = []
    for tline in git("ls-tree", "-r", sha).strip().split("\n"):
        meta, path = tline.split("\t")
        mode, typ, osha = meta.split()
        if typ == "blob" and osha not in blob_cache:
            status, _ = gh("GET", f"/git/blobs/{osha}")
            if status == 404:
                content = subprocess.run(["git", "-C", WORKDIR, "cat-file", "-p", osha], capture_output=True, check=True).stdout
                status, r = gh("POST", "/git/blobs", {"content": base64.b64encode(content).decode(), "encoding": "base64"})
                if status not in (200, 201):
                    print(f"  BLOB FAIL {osha[:8]}: {status} {r}"); sys.exit(1)
            blob_cache.add(osha)
        entries.append({"path": path, "mode": mode, "type": typ, "sha": osha})
    status, tree_r = gh("POST", "/git/trees", {"tree": entries})
    if status not in (200, 201):
        print(f"  TREE FAIL: {status} {tree_r}"); sys.exit(1)
    dpart, tpart, tz = ad.split(" ")
    cdate = f"{dpart}T{tpart}{tz[:3]}:{tz[3:]}"
    status, commit_r = gh("POST", "/git/commits", {
        "message": body, "tree": tree_r["sha"], "parents": [parent_sha],
        "author": {"name": an, "email": ae, "date": cdate},
        "committer": {"name": an, "email": ae, "date": cdate}})
    if status not in (200, 201):
        print(f"  COMMIT FAIL: {status} {commit_r}"); sys.exit(1)
    parent_sha = commit_r["sha"]
    print(f"  {sha[:8]} -> {parent_sha[:8]}  {subject[:60]}")

status, r = gh("PATCH", "/git/refs/heads/main", {"sha": parent_sha})
print(f"Ref update: {status}")
if status == 200:
    print(f"DONE. main now at {parent_sha[:8]}")
else:
    print(f"REF FAIL: {r}"); sys.exit(1)
