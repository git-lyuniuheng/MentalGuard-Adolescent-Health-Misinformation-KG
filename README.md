# Chinese Adolescent Health Misinformation Knowledge Graph (MentalGuard)

<p align="center">
  <strong>首个面向青少年的中文多模态健康谣言知识图谱</strong>
</p>

---

## 📋 数据集简介

**MentalGuard** 是一个专门面向 12-18 岁青少年群体的中文健康谣言知识图谱，旨在解决社交媒体平台上青少年健康信息污染问题。数据集覆盖 9 大青少年高频健康领域，包含 738 条高质量谣言-真相配对（由 v1.0 的 61 条扩展 12 倍），采用 12 字段结构化标注体系，并融合文本、图像、视频、传播特征四模态**元数据**（多模态节点为外部 URL 引用，未附媒体二进制；详见下方「数据集限制」）。构建方法（双源交叉验证）保持不变。

该数据集为可用于多模态健康谣言检测、知识图谱增强的事实核查、以及青少年健康教育智能助手等场景。

---

## 📊 数据规模与统计

| 统计项 | 数值 |
|--------|------|
| **版本** | v2.0 (由 v1.0 的 61 条扩展至 738 条) |
| **谣言-真相配对数** | 738 |
| **覆盖类别数** | 9 |
| **标注字段数** | 12 |
| **双源验证覆盖率** | 100% (738/738) |
| **T1 信源覆盖率** | 78.9% (582/738) |
| **URL 可回溯率** | 95% (HTTP 200) |
| **危险等级分布** | critical: 34 / high: 148 / medium: 261 / low: 295 |
| **信源层级** | T1（9 个政府/国际机构）、T2（6 个学术团体）、T3（3 个社交媒体平台） |
| **传播平台覆盖** | 微博 / 抖音 / 小红书 / B站 |
| **语言** | 中文（简体） |
| **许可证** | CC BY-NC-SA 4.0 |

### 9 大类别分布

| 序号 | 类别名称 | 英文标识 | 记录数 |
|------|---------|---------|--------|
| 1 | 青少年心理健康 | mental_health | 81 |
| 2 | 校园食品安全 | food_safety | 86 |
| 3 | 疫苗与健康 | vaccine | 77 |
| 4 | 数字健康与近视防控 | digital_health | 83 |
| 5 | 成瘾物质与功能饮品 | substance_safety | 84 |
| 6 | 饮食与身体形象 | body_image_nutrition | 81 |
| 7 | 青春期皮肤健康 | dermatology | 81 |
| 8 | 睡眠与昼夜节律 | sleep_health | 81 |
| 9 | 青春期生理健康 | sexual_health | 84 |

---

## 📚 数据来源

### Tier 1 — 政府与国际机构（9 个）

| 信源名称 | URL | 内容类型 |
|---------|-----|---------|
| 国家卫健委健康科普辟谣平台 | nhc.gov.cn/kppypt | 健康谣言专题辟谣 |
| 全国教育辟谣平台 | jypy.jyb.cn | 教育领域辟谣 |
| 科学辟谣平台（中国科协） | piyao.kepuchina.cn | 多领域辟谣文章 |
| 中国互联网联合辟谣平台 | piyao.org.cn | 年度辟谣报告 |
| 科普中国 | kepuchina.cn | 科普文章和视频 |
| 中国疾控中心 | chinacdc.cn | 控烟/传染病/近视防控 |
| WHO 中文站 | who.int/zh/news-room/fact-sheets | 青少年健康专题 |
| 国家药监局 | nmpa.gov.cn | 药品/化妆品科普 |
| 中国政府网 | gov.cn | 食品安全国家标准 |

### Tier 2 — 学术团体与专业学会（6 个）

中华医学会各分会、中国心理学会、中国营养学会、中国睡眠研究会、中华预防医学会、中国计划生育协会

### Tier 3 — 社交媒体与公众平台（3 个）

新浪微博不实信息举报平台、抖音健康辟谣专项、科普中国视频库

---

## 🏷️ 标注规范

### 12 字段标准标注体系

| 字段名 | 类型 | 含义 | 示例 |
|--------|------|------|------|
| `id` | string | 唯一标识符 | `dh001` |
| `rumor_text` | string | 谣言原始表述 | "近视可以治愈、可以逆转" |
| `truth_text` | string[] | 科学真相（多条款项数组） | ["真性近视是眼轴变长…不可逆转", ...] |
| `source` | string | 证据来源原文 | "教育部《近视防控20问答》；中华医学会…" |
| `category` | string | 所属类别（中文） | "数字健康与近视防控" |
| `category_key` | string | 类别英文标识 | `digital_health` |
| `severity` | enum | 危险等级 | `critical` / `high` / `medium` / `low` |
| `keywords` | string[] | 关键词标签数组 | ["近视", "伪科学", "虚假广告"] |
| `platform` | string | 主要传播平台 | 抖音 / 小红书 / B站 / 微博 |
| `verified_sources` | object[] | 交叉验证信源数组 | `[{name, document, tier}]` |
| `verification_status` | enum | 核验状态 | `verified` / `pending` |
| `source_tier` | string | 最高信源层级 | `T1` / `T2` |

### 危险等级分类标准

| 等级 | 判定标准 | 数量（v2.0） |
|------|---------|------------|
| `critical` | 可能导致死亡/永久残疾 | 34 |
| `high` | 可能导致严重健康损害 | 148 |
| `medium` | 可能导致中度损害/经济损失 | 261 |
| `low` | 主要为认知误区 | 295 |

### 多模态节点字段（字段定义以 data/schema.json 为准）

图像节点：`misconception_id`, `type`, `desc`, `source`, `url`, `local_path`, `format`, `status`, `url_type`, `url_desc`

视频节点：`misconception_id`, `platform`, `desc`, `propagation`, `url`, `local_path`, `keyframe_path`, `status`, `url_type`, `url_desc`

传播节点：`misconception_id`, `platform`, `metrics`, `source_url`, `status`, `url_type`, `url_desc`

详细标注规范请参阅 [docs/annotation_guidelines.md](docs/annotation_guidelines.md)。

**媒体二进制未嵌入**：多模态节点仅为**外部网页/视频页 URL 引用**，数据集**不包含**任何图像/视频文件，实际图/视频需从源页面获取，受版权未随包分发。

---


## 📁 仓库结构

```
MentalGuard-Adolescent-Health-Misinformation-KG/
├── README.md                          # 本文件
├── CITATION.cff                       # 引用信息
├── LICENSE                            # 开源协议 (CC BY-NC-SA 4.0)
├── .gitignore                         # Git 忽略规则
├── data/
│   ├── mentalguard_v1.0.json          # 历史版本主数据文件 (61 条，v1.0 发布)
│   ├── mentalguard_v2.0.json          # 主数据文件 (738 条谣言-真相配对 + 多模态节点)
│   └── schema.json                    # 字段说明与数据模式
├── scripts/
│   ├── build_dataset.py               # 数据集构建脚本（五阶段流水线，v1.0）
│   ├── build_dataset_v6.py            # v2.0 扩展构建脚本（合并 9 个 data_*.py 模块）
│   ├── data_mh.py / data_fs.py / data_vx.py / data_dh.py / data_ss.py / data_bn.py / data_dm.py / data_sh.py / data_sx.py  # 九类新增记录模块
│   ├── add_multimodal_urls.py         # 多模态节点 URL 填充脚本
│   ├── verify_urls.py                 # URL 可访问性验证脚本
│   └── verify_v2.py                   # v2.0 数据集完整性校验        
└── docs/
    └── annotation_guidelines.md       # 标注规范详细说明
```

### 加载数据集

```python
import json

with open("data/mentalguard_v2.0.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 查看元数据
print(f"版本: {data['meta']['version']}")
print(f"总记录数: {data['meta']['total_misconceptions']}")

# 遍历所有谣言-真相配对
for category_key, category_data in data["categories"].items():
    for item in category_data["misconceptions"]:
        print(f"[{item['id']}] 谣言: {item['rumor_text']}")
        print(f"  真相: {item['truth_text'][0]}")
        print(f"  危险等级: {item['severity']}")
        print(f"  验证状态: {item['verification_status']}")
```

## 📜 使用许可

本数据集采用 [**CC BY-NC-SA 4.0**](https://creativecommons.org/licenses/by-nc-sa/4.0/) (署名-非商业性使用-相同方式共享 4.0 国际) 许可协议。

- ✅ **允许**：分享、改编、用于学术研究
- ❌ **禁止**：商业用途
- ⚠️ **要求**：署名 + 衍生作品采用相同许可

---

## 📝 引用方式

如果本数据集对您的研究有帮助，请按以下格式引用：

### BibTeX

```bibtex
@dataset{mentalguard2026,
  title     = {Chinese Adolescent Health Misinformation Knowledge Graph (MentalGuard)},
  author    = {Lyu, Niuheng},
  year      = {2026},
  month     = {August},
  version   = {v2.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.21774699},
  url       = {https://github.com/git-lyuniuheng/MentalGuard-Adolescent-Health-Misinformation-KG}
}
```

### APA

```
Lyu, Niuheng. (2026). Chinese Adolescent Health Misinformation Knowledge Graph (MentalGuard) (v2.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21774699
```

---

## 📧 联系方式

- **邮箱**: 67747441@qq.com
- **GitHub**: [git-lyuniuheng](https://github.com/git-lyuniuheng)

---

## 🙏 致谢

感谢以下机构提供的公开数据资源：

- 国家卫生健康委员会健康科普辟谣平台
- 中国疾病预防控制中心
- 世界卫生组织 (WHO) 中文站
- 科普中国
- 中国互联网联合辟谣平台
- 中华医学会各分会
- 中国营养学会

---

<p align="center">
  <sub>© 2026 MentalGuard. Licensed under CC BY-NC-SA 4.0.</sub>
</p>
