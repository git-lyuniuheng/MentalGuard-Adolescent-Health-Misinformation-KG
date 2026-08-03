#!/usr/bin/env python3
"""验证多模态节点的URL是否可访问"""
import json
import urllib.request
import urllib.error
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def check_url(url, timeout=10):
    """检查URL是否可访问，返回HTTP状态码"""
    if not url:
        return "EMPTY"
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return str(e)[:50]

def main():
    json_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "misconceptions_v5_full.json"
    )
    json_path = os.path.abspath(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    multimodal = data.get("multimodal_kg_extensions", {})
    
    results = {"accessible": [], "error": [], "empty": []}

    print("=" * 70)
    print("图像节点 URL 验证")
    print("=" * 70)
    for img in multimodal.get("image_nodes", []):
        url = img.get("url", "")
        desc = img.get("desc", "")
        mid = img.get("misconception_id", "")
        result = check_url(url)
        status_icon = "✅" if isinstance(result, int) and result < 400 else "❌"
        print(f"  {status_icon} [{mid}] {desc[:30]}... → {result}")
        if not url:
            results["empty"].append(f"image:{mid}")
        elif isinstance(result, int) and result < 400:
            results["accessible"].append(f"image:{mid}")
        else:
            results["error"].append(f"image:{mid} → {result}")

    print("\n" + "=" * 70)
    print("视频节点 URL 验证")
    print("=" * 70)
    for vid in multimodal.get("video_nodes", []):
        url = vid.get("url", "")
        desc = vid.get("desc", "")
        mid = vid.get("misconception_id", "")
        result = check_url(url)
        status_icon = "✅" if isinstance(result, int) and result < 400 else "❌"
        print(f"  {status_icon} [{mid}] {desc[:30]}... → {result}")
        if not url:
            results["empty"].append(f"video:{mid}")
        elif isinstance(result, int) and result < 400:
            results["accessible"].append(f"video:{mid}")
        else:
            results["error"].append(f"video:{mid} → {result}")

    print("\n" + "=" * 70)
    print("传播节点 URL 验证")
    print("=" * 70)
    for prop in multimodal.get("propagation_nodes", []):
        url = prop.get("source_url", "")
        mid = prop.get("misconception_id", "")
        platform = prop.get("platform", "")
        result = check_url(url)
        status_icon = "✅" if isinstance(result, int) and result < 400 else "❌"
        print(f"  {status_icon} [{mid}] {platform} → {result}")
        if not url:
            results["empty"].append(f"propagation:{mid}")
        elif isinstance(result, int) and result < 400:
            results["accessible"].append(f"propagation:{mid}")
        else:
            results["error"].append(f"propagation:{mid} → {result}")

    print("\n" + "=" * 70)
    print("汇总")
    print("=" * 70)
    print(f"  可访问:   {len(results['accessible'])} 个")
    print(f"  错误:     {len(results['error'])} 个")
    print(f"  空URL:    {len(results['empty'])} 个")
    if results["error"]:
        print(f"\n  详细错误:")
        for e in results["error"]:
            print(f"    - {e}")


if __name__ == "__main__":
    main()
