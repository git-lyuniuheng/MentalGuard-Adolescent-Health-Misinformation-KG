#!/usr/bin/env python3
"""
GitHub API Uploader for MentalGuard Dataset
Uses GitHub Contents API to upload files (bypasses git push, only needs api.github.com)

Usage:
    python upload_to_github.py <PAT_TOKEN>

Steps:
    1. Creates GitHub repository via API
    2. Uploads all files via Contents API
    3. Creates a release with tag v1.0
"""

import sys
import os
import base64
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# === Configuration ===
GITHUB_USERNAME = "git-lyuniuheng"
REPO_NAME = "MentalGuard-Adolescent-Health-Misinformation-KG"
REPO_DESC = "Chinese Adolescent Health Misinformation Knowledge Graph - First multi-modal KG for adolescent health rumors (ICDM 2026)"
REPO_DIR = Path(__file__).resolve().parent.parent  # Repository root directory

API_BASE = "https://api.github.com"

def api_call(method, endpoint, token, data=None, content_type="application/json"):
    """Make an authenticated GitHub API request."""
    url = f"{API_BASE}{endpoint}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "MentalGuard-Uploader",
    }
    body = None
    if data is not None:
        if content_type == "application/json":
            body = json.dumps(data).encode("utf-8")
        else:
            body = data
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            status = resp.getcode()
            if resp_body:
                return status, json.loads(resp_body)
            return status, {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        return e.code, json.loads(err_body) if err_body else {}
    except Exception as e:
        return 0, {"error": str(e)}


def create_repo(token):
    """Create a new GitHub repository."""
    print(f"\n[1/3] Creating repository: {REPO_NAME}")
    data = {
        "name": REPO_NAME,
        "description": REPO_DESC,
        "private": False,
        "has_issues": True,
        "has_wiki": True,
        "auto_init": False,
    }
    status, resp = api_call("POST", "/user/repos", token, data)
    if status == 201:
        print(f"  [OK] Repository created: {resp.get('html_url', 'N/A')}")
        return True
    elif status == 422 and "already exists" in json.dumps(resp).lower():
        print(f"  [INFO] Repository already exists, continuing...")
        return True
    else:
        print(f"  [FAIL] Failed to create repo (HTTP {status}): {resp}")
        return False


def upload_file(token, file_path, repo_path):
    """Upload a single file via GitHub Contents API."""
    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    data = {
        "message": f"Add {repo_path}",
        "content": content,
        "branch": "main",
    }

    # Check if file already exists (need SHA to update)
    status, resp = api_call("GET", f"/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{repo_path}", token)
    if status == 200:
        data["sha"] = resp.get("sha")

    status, resp = api_call(
        "PUT",
        f"/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{repo_path}",
        token,
        data,
    )
    return status, resp


def upload_all_files(token):
    """Upload all files from the local repository to GitHub."""
    print(f"\n[2/3] Uploading files from: {REPO_DIR}")

    # Collect all files to upload
    files_to_upload = []
    for root, dirs, files in os.walk(REPO_DIR):
        # Skip .git directory
        if ".git" in root:
            continue
        for fname in files:
            full_path = Path(root) / fname
            rel_path = full_path.relative_to(REPO_DIR)
            # Convert to forward slashes for GitHub API
            repo_path = str(rel_path).replace("\\", "/")
            files_to_upload.append((full_path, repo_path))

    print(f"  Found {len(files_to_upload)} files to upload")

    success_count = 0
    fail_count = 0

    for i, (full_path, repo_path) in enumerate(files_to_upload, 1):
        file_size = full_path.stat().st_size
        print(f"  [{i}/{len(files_to_upload)}] Uploading: {repo_path} ({file_size} bytes)...", end=" ")

        status, resp = upload_file(token, str(full_path), repo_path)

        if status in (200, 201):
            print("[OK]")
            success_count += 1
        else:
            print(f"[FAIL] (HTTP {status})")
            if "errors" in resp:
                for err in resp["errors"]:
                    print(f"      Error: {err.get('message', err)}")
            fail_count += 1

        # Rate limiting: GitHub API allows 5000 requests/hour, but be nice
        time.sleep(0.5)

    print(f"\n  Summary: {success_count} succeeded, {fail_count} failed")
    return fail_count == 0


def create_release(token):
    """Create a GitHub release with tag v1.0."""
    print(f"\n[3/3] Creating release: v1.0")
    data = {
        "tag_name": "v1.0",
        "target_commitish": "main",
        "name": "MentalGuard v1.0 - Initial Release",
        "body": (
            "## MentalGuard v1.0 - Chinese Adolescent Health Misinformation Knowledge Graph\n\n"
            "### Contents\n"
            "- 61 misconception-fact pairs across 9 adolescent health domains\n"
            "- 12-field structured annotation with T1-T3 source hierarchy\n"
            "- 100% dual-source cross-verification (73.8% with T1 government/WHO sources)\n"
            "- 20 multi-modal nodes (10 images + 5 videos + 5 propagation) with traceable URLs\n"
            "- CC BY-NC-SA 4.0 license\n\n"
            "### Citation\n"
            "If you use this dataset, please cite as specified in CITATION.cff\n\n"
            "### Contact\n"
            "67747441@qq.com\n"
        ),
        "draft": False,
        "prerelease": False,
    }
    status, resp = api_call("POST", f"/repos/{GITHUB_USERNAME}/{REPO_NAME}/releases", token, data)
    if status == 201:
        print(f"  [OK] Release created: {resp.get('html_url', 'N/A')}")
        return True
    else:
        print(f"  [FAIL] Failed to create release (HTTP {status}): {resp}")
        return False


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("MentalGuard GitHub Uploader")
        print("=" * 60)
        print(f"\nUsage: python upload_to_github.py <PAT_TOKEN>")
        print(f"\nTo create a PAT:")
        print(f"  1. Open https://github.com/settings/tokens?type=beta")
        print(f"  2. Click 'Generate new token'")
        print(f"  3. Token name: MentalGuard-Upload")
        print(f"  4. Expiration: 30 days")
        print(f"  5. Repository permissions → Contents: Read and write")
        print(f"  6. Generate and copy the token")
        print(f"\nThen run:")
        print(f"  python upload_to_github.py github_pat_xxxxxxxxxxxx")
        sys.exit(1)

    token = sys.argv[1].strip()

    print("=" * 60)
    print("MentalGuard GitHub Uploader")
    print(f"  Username: {GITHUB_USERNAME}")
    print(f"  Repo:     {REPO_NAME}")
    print(f"  Source:   {REPO_DIR}")
    print("=" * 60)

    # Verify token
    print("\n[0/3] Verifying token...")
    status, resp = api_call("GET", "/user", token)
    if status != 200:
        print(f"  [FAIL] Invalid token (HTTP {status}): {resp}")
        print(f"  Please check your PAT and try again.")
        sys.exit(1)
    print(f"  [OK] Authenticated as: {resp.get('login', 'unknown')}")

    # Step 1: Create repo
    if not create_repo(token):
        print("\nFailed to create repository. Aborting.")
        sys.exit(1)

    # Step 2: Upload files
    if not upload_all_files(token):
        print("\nSome files failed to upload. Check errors above.")

    # Step 3: Create release
    create_release(token)

    # Done
    print("\n" + "=" * 60)
    print("DONE!")
    print(f"  Repository: https://github.com/{GITHUB_USERNAME}/{REPO_NAME}")
    print(f"  Release:    https://github.com/{GITHUB_USERNAME}/{REPO_NAME}/releases/tag/v1.0")
    print("=" * 60)
    print("\nNext steps:")
    print(f"  1. Upload to HuggingFace Datasets for DOI")
    print(f"  2. Connect Zenodo for backup DOI")
    print(f"  3. Add DOIs to your paper citations")


if __name__ == "__main__":
    main()
