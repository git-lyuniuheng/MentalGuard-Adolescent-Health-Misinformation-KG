# MentalGuard 数据集开源与归属证明 — 完整操作指南

> **目标**：通过 GitHub + HuggingFace + Zenodo 三平台联动，实现数据集开源发布与学术归属闭环。

---

## 当前状态

| 项目 | 状态 |
|------|------|
| 本地 Git 仓库 | ✅ 已初始化，已提交（1次 commit，10个文件） |
| GitHub 推送 | ⏳ 需要 PAT + 网络畅通 |
| HuggingFace 上传 | ⏳ 待操作 |
| Zenodo DOI | ⏳ 待 GitHub Release 后联动 |
| 论文引用 | ⏳ 待 DOI 生成后补入 |

### 网络诊断结果

- `api.github.com` → ✅ 可达（HTTP 200）
- `github.com` → ❌ 不可达（连接超时）
- 本地代理 → ❌ 未检测到运行中的代理

**解决方案**：使用 `upload_to_github.py` 脚本通过 GitHub API 上传（只需 `api.github.com` 可达，绕过 git push）。

---

## 第一步：GitHub 上传（获取 Git 提交历史 = 归属证据）

### 1.1 创建 Personal Access Token (PAT)

> GitHub 自 2021 年起不再接受账号密码认证，必须使用 PAT。

**方式 A：通过浏览器创建（推荐）**

如果你的浏览器能访问 GitHub（即使命令行不能）：

1. 打开 https://github.com/settings/tokens?type=beta
2. 登录账号 `git-lyuniuheng`
3. 点击 **"Generate new token"**
4. 填写：
   - Token name: `MentalGuard-Upload`
   - Expiration: `30 days`
   - Repository access: `All repositories`
   - Permissions → Repository permissions → **Contents: Read and write**
5. 点击 **Generate token**
6. 复制生成的 Token（格式如 `github_pat_xxxxxxxxxxxx`）

**方式 B：通过 VPN 创建**

如果浏览器也无法访问 GitHub：
1. 开启 VPN / 代理
2. 按上述步骤创建 PAT
3. 创建完成后可关闭 VPN（后续上传走 api.github.com，不需要 VPN）

### 1.2 运行上传脚本

```powershell
cd "c:\Users\Administrator\WorkBuddy\20260731090758\MentalGuard-Adolescent-Health-Misinformation-KG"
python scripts\upload_to_github.py <你的PAT>
```

脚本会自动完成：
1. ✅ 创建 GitHub 仓库（`MentalGuard-Adolescent-Health-Misinformation-KG`）
2. ✅ 上传所有 10 个文件（通过 Contents API，逐文件上传）
3. ✅ 创建 v1.0 Release（带发布说明）

上传完成后，仓库地址：
```
https://github.com/git-lyuniuheng/MentalGuard-Adolescent-Health-Misinformation-KG
```

### 1.3 验证归属证据

Git 提交历史即为创作时间证明：
- 提交时间戳：由 GitHub 服务器记录
- 提交者：`git-lyuniuheng <67747441@qq.com>`
- 提交哈希：唯一标识，不可篡改

---

## 第二步：HuggingFace Datasets 上传（获取学术 DOI）

### 2.1 创建 HuggingFace 账号

1. 打开 https://huggingface.co/join
2. 注册账号（建议使用 67747441@qq.com）

### 2.2 创建数据集仓库

1. 登录后访问 https://huggingface.co/new-dataset
2. 填写：
   - Owner: 你的用户名
   - Dataset name: `Chinese-Adolescent-Health-Rumor-KG`
   - License: `CC BY-NC-SA 4.0`
   - Visibility: Public
3. 点击 **Create dataset**

### 2.3 上传数据文件

**方式 A：Web 界面上传（简单）**

1. 进入数据集页面 → **Files and versions** → **Add file** → **Upload file**
2. 上传以下文件：
   - `data/mentalguard_v1.0.json`（主数据文件）
   - `data/schema.json`（字段说明）
   - `README.md`（数据集说明）
   - `CITATION.cff`（引用信息）
   - `LICENSE`（开源协议）

**方式 B：命令行上传**

```powershell
pip install huggingface_hub
huggingface-cli login  # 输入 HuggingFace Token

# 克隆数据集仓库（空仓库）
git clone https://huggingface.co/datasets/<你的用户名>/Chinese-Adolescent-Health-Rumor-KG

# 复制文件
Copy-Item "data\*" "Chinese-Adolescent-Health-Rumor-KG\"
Copy-Item "README.md" "Chinese-Adolescent-Health-Rumor-KG\"
Copy-Item "CITATION.cff" "Chinese-Adolescent-Health-Rumor-KG\"
Copy-Item "LICENSE" "Chinese-Adolescent-Health-Rumor-KG\"

# 提交并推送
cd Chinese-Adolescent-Health-Rumor-KG
git add -A
git commit -m "Initial release: MentalGuard v1.0"
git push
```

### 2.4 获取 DOI

HuggingFace 会自动为数据集分配一个永久标识符（在数据集页面右侧 "Cite this dataset" 区域查看）。

引用格式示例：
```bibtex
@dataset{chinese_adolescent_health_rumor_kg,
  title={Chinese Adolescent Health Misinformation Knowledge Graph},
  author={git-lyuniuheng},
  year={2026},
  publisher={HuggingFace},
  url={https://huggingface.co/datasets/<你的用户名>/Chinese-Adolescent-Health-Rumor-KG}
}
```

---

## 第三步：Zenodo 集成（版本化 DOI 备份）

### 3.1 关联 GitHub 账号

1. 打开 https://zenodo.org/
2. 注册/登录（可用 GitHub 账号直接登录）
3. 进入 Settings → GitHub → 授权连接 `git-lyuniuheng` 账号

### 3.2 启用仓库归档

1. 在 Zenodo GitHub 页面，找到 `MentalGuard-Adolescent-Health-Misinformation-KG`
2. 将开关切到 **ON**

### 3.3 触发 DOI 生成

当你在 GitHub 创建 Release（上传脚本已自动创建 v1.0 Release），Zenodo 会自动：
1. 抓取该 Release 的所有文件
2. 生成永久 DOI（格式如 `10.5281/zenodo.xxxxxxx`）
3. 在 Zenodo 上创建归档记录

> **注意**：由于 github.com 从命令行不可达，Zenodo 的自动归档需要在 GitHub Release 成功创建后由 Zenodo 服务器端自动触发。如果你的 Release 已通过 API 创建成功，等待几分钟即可在 Zenodo 看到。

### 3.4 获取 Zenodo DOI

访问 https://zenodo.org/account/settings/github/ 查看已归档的 Release 及其 DOI。

---

## 第四步：论文中引用 DOI（学术归属闭环）

### 4.1 收集所有 DOI

完成前三步后，你将拥有：

| 平台 | DOI/标识 | 用途 |
|------|----------|------|
| GitHub | 仓库 URL + Commit Hash | 创作时间证明 |
| HuggingFace | 数据集页面 URL | 学术引用标识 |
| Zenodo | `10.5281/zenodo.xxxxxxx` | 永久存档 DOI |

### 4.2 在论文中引用

在论文的 **Data Availability** 或 **Dataset** 章节添加：

```latex
\section{Data Availability}

The Chinese Adolescent Health Misinformation Knowledge Graph (MentalGuard) 
dataset is publicly available under the CC BY-NC-SA 4.0 license through 
the following platforms:

\begin{itemize}
    \item GitHub: \url{https://github.com/git-lyuniuheng/MentalGuard-Adolescent-Health-Misinformation-KG}
    \item HuggingFace: \url{https://huggingface.co/datasets/<username>/Chinese-Adolescent-Health-Rumor-KG}
    \item Zenodo: \url{https://doi.org/10.5281/zenodo.xxxxxxx}
\end{itemize}

The dataset was developed as part of the ICDM 2026 Teen Research Symposium.
```

在 **References** 中添加 BibTeX 引用：

```bibtex
@dataset{mentalguard2026,
  title={Chinese Adolescent Health Misinformation Knowledge Graph (MentalGuard)},
  author={Lyuniu Heng},
  year={2026},
  publisher={Zenodo},
  doi={10.5281/zenodo.xxxxxxx},
  url={https://doi.org/10.5281/zenodo.xxxxxxx}
}
```

---

## 归属证明体系

```
Git 提交历史（时间戳 + 哈希）
        │
        ├──→ GitHub Release（v1.0 公开发布）
        │           │
        │           ├──→ HuggingFace DOI（学术引用标识）
        │           │
        │           └──→ Zenodo DOI（永久存档备份）
        │
        └──→ 论文引用 DOI → 学术归属闭环
```

**三重证明**：
1. **Git 历史**：证明创作时间（不可篡改的提交记录）
2. **HuggingFace DOI**：学术界可引用的稳定标识
3. **Zenodo DOI**：永久存档，即使 GitHub 关闭也不会丢失

---

## 快速操作清单

- [ ] 1. 在浏览器中创建 GitHub PAT（https://github.com/settings/tokens?type=beta）
- [ ] 2. 运行 `python scripts\upload_to_github.py <PAT>` 上传到 GitHub
- [ ] 3. 在 HuggingFace 创建数据集并上传文件
- [ ] 4. 在 Zenodo 关联 GitHub 仓库
- [ ] 5. 确认 Zenodo DOI 已生成
- [ ] 6. 将所有 DOI 添加到论文中

---

## 联系方式

- Email: 67747441@qq.com
- GitHub: https://github.com/git-lyuniuheng
