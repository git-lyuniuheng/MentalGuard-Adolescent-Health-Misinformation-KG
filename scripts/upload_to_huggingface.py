#!/usr/bin/env python3
"""
HuggingFace Dataset Uploader for MentalGuard
Uploads dataset files to HuggingFace Datasets via API

Usage:
    python upload_to_huggingface.py <HF_TOKEN>

Prerequisites:
    - HuggingFace account created at https://huggingface.co/join
    - Access token created at https://huggingface.co/settings/tokens
"""

import sys
import os
import json
import time
from pathlib import Path

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    print("ERROR: huggingface_hub not installed")
    print("Run: pip install huggingface_hub")
    sys.exit(1)

# === Configuration ===
HF_DATASET_NAME = "Chinese-Adolescent-Health-Rumor-KG"
HF_DESC = "Chinese Adolescent Health Misinformation Knowledge Graph (MentalGuard) - First multi-modal KG for adolescent health rumor detection (ICDM 2026)"
REPO_DIR = Path(__file__).resolve().parent.parent  # Repository root directory

LICENSE = "cc-by-nc-sa-4.0"
TAGS = [
    "health", "misinformation", "knowledge-graph",
    "adolescent-health", "rumor-detection", "chinese",
    "multimodal", "public-health", "fact-checking"
]


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("MentalGuard HuggingFace Uploader")
        print("=" * 60)
        print(f"\nUsage: python upload_to_huggingface.py <HF_TOKEN>")
        print(f"\nTo create a HF token:")
        print(f"  1. Register at https://huggingface.co/join")
        print(f"  2. Go to https://huggingface.co/settings/tokens")
        print(f"  3. Create new token (type: Write)")
        print(f"  4. Copy the token (starts with hf_...)")
        sys.exit(1)

    token = sys.argv[1].strip()
    
    print("=" * 60)
    print("MentalGuard HuggingFace Uploader")
    print(f"  Dataset: {HF_DATASET_NAME}")
    print(f"  Source:  {REPO_DIR}")
    print("=" * 60)

    # Initialize API
    api = HfApi(token=token)

    # Verify token
    print("\n[0/3] Verifying token...")
    try:
        whoami = api.whoami()
        username = whoami.get("name", "unknown")
        print(f"  [OK] Authenticated as: {username}")
    except Exception as e:
        print(f"  [FAIL] Token verification failed: {e}")
        sys.exit(1)

    # Step 1: Create dataset repository
    print(f"\n[1/3] Creating dataset: {HF_DATASET_NAME}")
    try:
        repo_url = create_repo(
            repo_id=f"{username}/{HF_DATASET_NAME}",
            repo_type="dataset",
            private=False,
            token=token,
        )
        print(f"  [OK] Dataset created: {repo_url}")
    except Exception as e:
        err_str = str(e).lower()
        if "already exists" in err_str or "409" in err_str:
            print(f"  [INFO] Dataset already exists, continuing...")
        else:
            print(f"  [FAIL] Failed to create dataset: {e}")
            # Try to continue anyway
    
    dataset_id = f"{username}/{HF_DATASET_NAME}"

    # Step 2: Upload all files
    print(f"\n[2/3] Uploading files from: {REPO_DIR}")
    
    files_to_upload = []
    for root, dirs, files in os.walk(REPO_DIR):
        if ".git" in root:
            continue
        for fname in files:
            full_path = Path(root) / fname
            rel_path = full_path.relative_to(REPO_DIR)
            repo_path = str(rel_path).replace("\\", "/")
            files_to_upload.append((full_path, repo_path))

    print(f"  Found {len(files_to_upload)} files to upload")

    success_count = 0
    fail_count = 0

    for i, (full_path, repo_path) in enumerate(files_to_upload, 1):
        file_size = full_path.stat().st_size
        print(f"  [{i}/{len(files_to_upload)}] Uploading: {repo_path} ({file_size} bytes)...", end=" ", flush=True)

        try:
            api.upload_file(
                path_or_fileobj=str(full_path),
                path_in_repo=repo_path,
                repo_id=dataset_id,
                repo_type="dataset",
                token=token,
            )
            print("[OK]")
            success_count += 1
        except Exception as e:
            print(f"[FAIL] {e}")
            fail_count += 1

        time.sleep(0.5)

    print(f"\n  Summary: {success_count} succeeded, {fail_count} failed")

    # Step 3: Update dataset metadata
    print(f"\n[3/3] Updating dataset metadata...")
    
    # Create README with HF metadata
    readme_content = """---
language:
  - zh
license: cc-by-nc-sa-4.0
task_categories:
  - text-classification
  - fact-checking
tags:
  - health
  - misinformation
  - knowledge-graph
  - adolescent-health
  - rumor-detection
  - chinese
  - multimodal
  - public-health
size_categories:
  - n<1K
---

# Chinese Adolescent Health Misinformation Knowledge Graph (MentalGuard)

## Description

The first multi-modal Knowledge Graph dataset specifically designed for adolescent health misinformation detection in Chinese. 
Covers 9 adolescent health domains with 61 verified misconception-fact pairs.

## Key Features

- **61 misconception-fact pairs** across 9 adolescent health domains
- **12-field structured annotation** with T1-T3 source hierarchy
- **100% dual-source cross-verification** (73.8% with T1 government/WHO sources)
- **20 multi-modal nodes** (10 images + 5 videos + 5 propagation) with traceable URLs
- **CC BY-NC-SA 4.0** license

## Citation

If you use this dataset, please cite as specified in CITATION.cff

## Contact

67747441@qq.com

## Related Links

- GitHub: https://github.com/git-lyuniuheng/MentalGuard-Adolescent-Health-Misinformation-KG
"""

    readme_path = REPO_DIR / "README_HF.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    try:
        api.upload_file(
            path_or_fileobj=str(readme_path),
            path_in_repo="README.md",
            repo_id=dataset_id,
            repo_type="dataset",
            token=token,
        )
        print(f"  [OK] README with metadata uploaded")
    except Exception as e:
        print(f"  [FAIL] README upload failed: {e}")

    # Clean up temp file
    readme_path.unlink(missing_ok=True)

    # Done
    print("\n" + "=" * 60)
    print("DONE!")
    print(f"  Dataset: https://huggingface.co/datasets/{dataset_id}")
    print("=" * 60)
    print("\nNext steps:")
    print(f"  1. Connect Zenodo to GitHub for backup DOI")
    print(f"  2. Add all DOIs to your paper citations")


if __name__ == "__main__":
    main()
