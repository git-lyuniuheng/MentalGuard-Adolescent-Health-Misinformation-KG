#!/usr/bin/env python3
"""
Upload MentalGuard dataset to Zenodo via REST API.
Creates a deposit, uploads files, fills metadata, and publishes.
"""

import sys
import os
import json
import urllib.request
import urllib.error

ZENODO_API = "https://zenodo.org/api/deposit/depositions"

def api_request(url, method="GET", token=None, data=None, file_path=None, file_field="file"):
    """Make a Zenodo API request."""
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    
    if file_path:
        # Zenodo bucket upload: raw PUT with octet-stream
        with open(file_path, "rb") as f:
            body = f.read()
        headers["Content-Type"] = "application/octet-stream"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    elif data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = resp.read().decode("utf-8")
            status = resp.status
            if resp_data:
                return status, json.loads(resp_data)
            return status, {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
        except:
            err_json = err_body
        return e.code, err_json

def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_to_zenodo.py <ZENODO_TOKEN>")
        sys.exit(1)
    
    token = sys.argv[1]
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print("=" * 60)
    print("MentalGuard Zenodo Upload Script")
    print("=" * 60)
    
    # Step 1: Create a new deposit
    print("\n[Step 1] Creating new deposit...")
    status, resp = api_request(ZENODO_API, method="POST", token=token, data={})
    if status != 201:
        print("  [FAIL] Could not create deposit (HTTP {}): {}".format(status, resp))
        sys.exit(1)
    
    deposit_id = resp.get("id")
    prereserved_doi = resp.get("metadata", {}).get("prereserve_doi", {})
    doi = prereserved_doi.get("doi", "N/A") if prereserved_doi else "N/A"
    print("  [OK] Deposit created: ID={}".format(deposit_id))
    print("  [OK] Pre-reserved DOI: {}".format(doi))
    
    bucket_url = resp.get("links", {}).get("bucket")
    if not bucket_url:
        print("  [FAIL] No bucket URL found in response")
        sys.exit(1)
    
    # Step 2: Upload files
    print("\n[Step 2] Uploading files...")
    files_to_upload = [
        ("data/mentalguard_v1.0.json", "mentalguard_v1.0.json"),
        ("data/schema.json", "schema.json"),
        ("README.md", "README.md"),
        ("LICENSE", "LICENSE"),
        ("CITATION.cff", "CITATION.cff"),
    ]
    
    success_count = 0
    for rel_path, display_name in files_to_upload:
        file_path = os.path.join(base_dir, rel_path)
        if not os.path.exists(file_path):
            print("  [SKIP] {} (not found)".format(display_name))
            continue
        
        file_size = os.path.getsize(file_path)
        print("  Uploading {} ({} bytes)... ".format(display_name, file_size), end="", flush=True)
        
        upload_url = bucket_url + "/" + display_name
        status, resp = api_request(upload_url, method="PUT", token=token, file_path=file_path)
        
        if status in (200, 201):
            print("[OK]")
            success_count += 1
        else:
            print("[FAIL] (HTTP {})".format(status))
            if isinstance(resp, dict):
                print("         Error: {}".format(resp.get("message", resp)))
    
    print("\n  Uploaded {}/{} files".format(success_count, len(files_to_upload)))
    
    # Step 3: Update metadata
    print("\n[Step 3] Updating metadata...")
    metadata = {
        "metadata": {
            "title": "MentalGuard: A Chinese Adolescent Health Misinformation Knowledge Graph",
            "upload_type": "dataset",
            "description": (
                "<p>MentalGuard is the first multi-modal knowledge graph (KG) designed for "
                "Chinese adolescent health misinformation detection. It covers three critical "
                "domains: mental health, campus food safety, and vaccine-related rumors.</p>"
                "<p><strong>Key features:</strong></p>"
                "<ul>"
                "<li>24 verified rumor-truth pairs with multi-source validation</li>"
                "<li>T1-T3 tiered source hierarchy (NHC, WHO, China CDC)</li>"
                "<li>Four modality support (text, image, video, audio)</li>"
                "<li>Structured schema with 12+ annotation fields per entry</li>"
                "</ul>"
                "<p>GitHub: <a href=\"https://github.com/git-lyuniuheng/MentalGuard-Adolescent-Health-Misinformation-KG\">https://github.com/git-lyuniuheng/MentalGuard-Adolescent-Health-Misinformation-KG</a></p>"
            ),
            "creators": [
                {
                    "name": "Liu, Yuniuheng",
                    "affiliation": "ICDM 2026",
                    "orcid": ""
                }
            ],
            "keywords": [
                "adolescent health",
                "misinformation",
                "knowledge graph",
                "rumor detection",
                "mental health",
                "vaccine",
                "food safety",
                "Chinese",
                "multi-modal"
            ],
            "license": "CC-BY-NC-SA-4.0",
            "access_right": "open",
            "communities": [],
            "version": "1.0",
            "language": "eng",
            "subjects": [
                {"subject": "Health Misinformation"},
                {"subject": "Knowledge Graph"},
                {"subject": "Adolescent Health"},
            ]
        }
    }
    
    update_url = ZENODO_API + "/" + str(deposit_id)
    status, resp = api_request(update_url, method="PUT", token=token, data=metadata)
    if status in (200, 202):
        print("  [OK] Metadata updated")
        doi = resp.get("metadata", {}).get("prereserve_doi", {}).get("doi", doi)
    else:
        print("  [FAIL] Metadata update failed (HTTP {}): {}".format(status, resp))
    
    # Step 4: Publish
    print("\n[Step 4] Publishing deposit...")
    publish_url = ZENODO_API + "/" + str(deposit_id) + "/actions/publish"
    status, resp = api_request(publish_url, method="POST", token=token)
    if status in (200, 202):
        published_doi = resp.get("doi", "N/A")
        record_url = resp.get("links", {}).get("record_html", "N/A")
        print("  [OK] Published successfully!")
        print("  [OK] DOI: {}".format(published_doi))
        print("  [OK] Record URL: {}".format(record_url))
        print("\n" + "=" * 60)
        print("SUCCESS! Dataset published on Zenodo")
        print("DOI: " + published_doi)
        print("URL: " + record_url)
        print("=" * 60)
    else:
        print("  [FAIL] Publish failed (HTTP {}): {}".format(status, resp))
        print("  Deposit ID: {} (still in draft mode)".format(deposit_id))
        print("  You can edit and publish manually at: https://zenodo.org/deposit/{}".format(deposit_id))
    
    print("\nDone.")

if __name__ == "__main__":
    main()
