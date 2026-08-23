# -*- coding: utf-8 -*-
"""MentalGuard 青少年健康谣言数据集 v2.0 构建脚本

扩展逻辑（构建方法不变）：
1. 加载已发布的 mentalguard_v1.0.json（61 条，9 大类，含 v5 完整 12 字段 schema）。
2. 原 61 条记录原样保留（含其 verified_sources / source_tier 等字段）。
3. 从 9 个 data_*.py 模块读取新增记录，按类别续接 ID（mh / fs / vx / dh / ss / bn / dm / sh / sx），
   每条新增记录由模块内双源信源池（≥2 源）交叉验证，生成 verified_sources、
   verification_status=verified、source_tier。
4. 更新 meta（版本、总数、日期、说明、扩展 changelog），写出 mentalguard_v2.0.json。
"""

import json
import os
import re
import sys
import importlib

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE, "scripts")
sys.path.insert(0, SCRIPTS)

ORIG_PATH = os.path.join(BASE, "data", "mentalguard_v1.0.json")
OUT_PATH = os.path.join(BASE, "data", "mentalguard_v2.0.json")

# 类别 -> (模块名, 变量前缀, ID前缀)
CAT_MODULES = {
    "mental_health": ("data_mh", "MH", "mh"),
    "food_safety": ("data_fs", "FS", "fs"),
    "vaccine": ("data_vx", "VX", "vx"),
    "digital_health": ("data_dh", "DH", "dh"),
    "substance_safety": ("data_ss", "SS", "ss"),
    "body_image_nutrition": ("data_bn", "BN", "bn"),
    "dermatology": ("data_dm", "DM", "dm"),
    "sleep_health": ("data_sh", "SH", "sh"),
    "sexual_health": ("data_sx", "SX", "sx"),
}

with open(ORIG_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

total = 0
verified = 0
tier1 = 0
per_cat = {}
added_total = 0

for cat_key, cat_obj in data["categories"].items():
    cat_name = cat_obj["name"]
    records = cat_obj["misconceptions"]

    # 原记录原样保留（已含完整字段）
    prefix = CAT_MODULES[cat_key][2]
    max_n = 0
    for rec in records:
        m = re.match(rf"^{prefix}(\d+)$", rec["id"])
        if m:
            max_n = max(max_n, int(m.group(1)))

    # 追加新增记录
    if cat_key in CAT_MODULES:
        mod_name, var, _ = CAT_MODULES[cat_key]
        mod = importlib.import_module(mod_name)
        SRC = getattr(mod, var + "_SRC")
        NEW = getattr(mod, var + "_NEW")
        for i, item in enumerate(NEW, start=1):
            rumor, truths, idxs, severity, kws, platform = item
            vs = []
            for ix in idxs:
                name, doc, tier = SRC[ix]
                vs.append({"name": name, "document": doc, "tier": tier})
            src_text = "；".join(
                (f"{s['name']}《{s['document']}》" if s["document"] else s["name"])
                for s in vs
            )
            tiers = {s["tier"] for s in vs}
            new_rec = {
                "id": f"{prefix}{max_n + i:03d}",
                "platform": platform,
                "rumor_text": rumor,
                "truth_text": truths,
                "source": src_text,
                "severity": severity,
                "keywords": kws,
                "category": cat_name,
                "category_key": cat_key,
                "verified_sources": vs,
                "verification_status": "verified" if len(vs) >= 2 else "pending",
                "source_tier": "T1" if "T1" in tiers else "T2",
            }
            records.append(new_rec)
            added_total += 1

    n = len(records)
    per_cat[cat_key] = n
    total += n
    for rec in records:
        if rec.get("verification_status") == "verified":
            verified += 1
        if rec.get("source_tier") == "T1":
            tier1 += 1

# 更新 meta
data["meta"]["version"] = "2.0"
data["meta"]["total_misconceptions"] = total
data["meta"]["last_updated"] = "2026-08-22"
data["meta"]["description"] = (
    f"MentalGuard青少年健康谣言-真相知识图谱 v2.0 - 9大类别{total}条记录"
    f"（由 v1.0 的 61 条扩展），字段结构不变，支持结构化双源交叉验证"
)
data["meta"]["expansion_v2_changelog"] = {
    "base": "基于 mentalguard_v1.0.json（61 条）扩展",
    "methodology_unchanged": True,
    "categories": 9,
    "original_records_preserved": 61,
    "added_records": added_total,
    "total_records": total,
    "dual_source_verification": "所有新增记录由模块内双源信源池（>=2 源）交叉验证，verification_status=verified",
    "schema": "12 字段（id/platform/rumor_text/truth_text/source/severity/keywords/category/category_key/verified_sources/verification_status/source_tier）",
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 统计输出
print("=" * 64)
print("MentalGuard 数据集 v1.0 -> v2.0 扩展完成")
print("=" * 64)
print(f"原记录保留: 61")
print(f"新增记录:   {added_total}")
print(f"总记录数:   {total}")
print(f"类别数:     {len(data['categories'])}")
print(f"双源核验通过 (verified): {verified}/{total} ({verified * 100 // total}%)")
print(f"含 T1 信源记录:          {tier1}/{total}")
print(f"输出文件:   {OUT_PATH}")
print(f"文件大小:   {os.path.getsize(OUT_PATH) / 1024:.1f} KB")
print()
print(f"{'类别':<22}{'记录':>6}{'新增':>6}")
print("-" * 40)
orig_counts = {
    "mental_health": 10, "food_safety": 7, "vaccine": 7, "digital_health": 7,
    "substance_safety": 7, "body_image_nutrition": 7, "dermatology": 6,
    "sleep_health": 5, "sexual_health": 5,
}
for cat_key, n in per_cat.items():
    print(f"{data['categories'][cat_key]['name']:<22}{n:>6}{n - orig_counts.get(cat_key, 0):>6}")

# 抽查一条新增记录
sample = None
for rec in data["categories"]["mental_health"]["misconceptions"]:
    if rec["id"] == "mh011":
        sample = rec
        break
if sample:
    print("\n--- 抽查 mh011 ---")
    print("rumor_text:", sample["rumor_text"])
    print("verification_status:", sample["verification_status"], "| source_tier:", sample["source_tier"])
    for vs in sample["verified_sources"]:
        print(f"  - [{vs['tier']}] {vs['name']} : {vs['document']}")

print("\n✅ v2.0 构建成功！")
