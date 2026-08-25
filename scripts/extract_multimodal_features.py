#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/extract_multimodal_features.py
======================================
MentalGuard v2.0 多模态特征提取脚本

功能：从 GitHub 发布的 mentalguard_v2.0.json 中读取多模态节点 URL，
     下载/抓取对应图片/视频关键帧，通过 Chinese-CLIP 编码为 768 维语义向量，
     并将结果写入 multimodal_features.json。

用法：
    # 1. 仅提取图像节点特征
    python extract_multimodal_features.py --mode image

    # 2. 仅提取视频节点关键帧特征
    python extract_multimodal_features.py --mode video

    # 3. 仅提取传播节点特征（基于 URL 元数据文本）
    python extract_multimodal_features.py --mode propagation

    # 4. 提取全部三种节点
    python extract_multimodal_features.py --mode all

    # 5. 跳过 Chinese-CLIP（仅做下载/元数据提取，不编码）
    python extract_multimodal_features.py --mode all --skip-clip

    # 6. 指定自定义数据集路径
    python extract_multimodal_features.py --input ../data/mentalguard_v2.0.json --output ../data/multimodal_features.json

依赖：
    pip install torch transformers pillow opencv-python requests beautifulsoup4 tqdm
    # 中文 CLIP（自动从 HuggingFace 下载，约 1.2 GB）
    # 首次运行需要网络访问 HuggingFace
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
import warnings
from pathlib import Path
from typing import Any, Optional

import requests

# ─────────────────────────────────────────────
# 全局常量
# ─────────────────────────────────────────────

# Chinese-CLIP 模型标识（基础版 ≈ 370 MB 参数量，推理友好）
# 备选: "OFA-Sys/chinese-clip-vit-large-patch14" (更大，精度更高)
CHINESE_CLIP_MODEL = "OFA-Sys/chinese-clip-vit-base-patch16"
CHINESE_CLIP_DIM  = 768          # 输出向量维度
DOWNLOAD_TIMEOUT  = 30            # 单文件下载超时（秒）
REQUEST_DELAY     = 1.0           # 两次 HTTP 请求间最小间隔（秒），防封禁
MAX_RETRIES       = 2             # HTTP 请求最大重试次数
FALLBACK_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ─────────────────────────────────────────────
# CLI 参数解析
# ─────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MentalGuard v2.0 多模态特征提取脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="mentalguard_v2.0.json 路径（默认：自动查找 data/ 目录）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出特征文件路径（默认：与 input 同目录的 multimodal_features.json）"
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["all", "image", "video", "propagation"],
        default="all",
        help="提取模式：all=全部节点；image/video/propagation=仅特定节点"
    )
    parser.add_argument(
        "--skip-clip",
        action="store_true",
        help="跳过 Chinese-CLIP 编码（仅下载/提取文本，不生成向量）"
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cuda", "cpu"],
        help="推理设备（默认：自动检测 cuda > cpu）"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="批处理大小（默认：4）"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="减少日志输出"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="HuggingFace 模型缓存目录"
    )
    return parser.parse_args()


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def log(*msg: Any, quiet: bool = False) -> None:
    if not quiet:
        print(*msg, flush=True)


def safe_request(
    url: str,
    method: str = "GET",
    timeout: int = DOWNLOAD_TIMEOUT,
    stream: bool = False,
    headers: Optional[dict] = None,
    **kwargs,
) -> Optional[requests.Response]:
    """带重试和异常处理的 HTTP 请求。"""
    default_headers = {"User-Agent": FALLBACK_USER_AGENT}
    if headers:
        default_headers.update(headers)
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.request(
                method, url,
                timeout=timeout,
                stream=stream,
                headers=default_headers,
                **kwargs,
            )
            resp.raise_for_status()
            return resp
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                time.sleep(REQUEST_DELAY * (attempt + 1))
            else:
                log(f"  [WARN] 请求失败 ({attempt+1}/{MAX_RETRIES}): {url}  →  {exc}")
                return None
    return None


def auto_device() -> str:
    """自动选择推理设备。"""
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def find_dataset_path(input_arg: Optional[str]) -> Path:
    """自动查找 mentalguard_v2.0.json 路径。"""
    if input_arg:
        p = Path(input_arg).resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"指定路径不存在: {p}")

    # 常见相对路径
    candidates = [
        Path(__file__).parent.parent / "data" / "mentalguard_v2.0.json",
        Path(__file__).parent.parent.parent / "data" / "mentalguard_v2.0.json",
        Path("data/mentalguard_v2.0.json"),
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()

    raise FileNotFoundError(
        "未找到 mentalguard_v2.0.json。"
        " 请通过 --input 参数指定路径，"
        "或将文件放置于 data/mentalguard_v2.0.json"
    )


# ─────────────────────────────────────────────
# Chinese-CLIP 加载器
# ─────────────────────────────────────────────

class ChineseCLIPEncoder:
    """
    Chinese-CLIP 编码器封装。

    优先尝试加载 OFA-Sys/chinese-clip-vit-base-patch16。
    若 HuggingFace 网络不通或模型不可用，自动降级为：
      1. 本地文本向量（基于结巴分词 + TF-IDF）
      2. 全零向量（并记录 warning）
    """

    def __init__(
        self,
        model_name: str = CHINESE_CLIP_MODEL,
        device: Optional[str] = None,
        cache_dir: Optional[str] = None,
        quiet: bool = False,
    ):
        self.model_name = model_name
        self.device    = device or auto_device()
        self.cache_dir = cache_dir
        self.quiet     = quiet
        self.mode      = "unavailable"   # 最终生效的编码模式
        self.model     = None
        self.processor = None

        self._load()

    # ── 私有：尝试加载 Chinese-CLIP ──────────────────────

    def _load(self) -> None:
        try:
            import torch
            from transformers import AutoTokenizer, AutoModel

            log(f"[INFO] 正在加载 Chinese-CLIP: {self.model_name}  (device={self.device})", quiet=self.quiet)
            load_kwargs = {"trust_remote_code": True}
            if self.cache_dir:
                load_kwargs["cache_dir"] = self.cache_dir

            self.processor = AutoProcessor.from_pretrained(self.model_name, **load_kwargs)
            self.model = AutoModel.from_pretrained(self.model_name, **load_kwargs)
            self.model = self.model.to(self.device).eval()

            # 注册缺失的 AutoProcessor（HuggingFace 旧版本兼容）
            if self.processor is None:
                from transformers import ChineseCLIPProcessor
                self.processor = ChineseCLIPProcessor.from_pretrained(self.model_name)

            self.mode = "chinese_clip"
            log("[INFO] Chinese-CLIP 加载成功！", quiet=self.quiet)

        except ImportError as exc:
            log(f"[WARN] 缺少依赖库: {exc}", quiet=self.quiet)
            self.mode = "fallback"

        except Exception as exc:
            log(f"[WARN] Chinese-CLIP 加载失败: {exc}", quiet=self.quiet)
            log("[INFO] 将使用降级方案：文本 TF-IDF 向量", quiet=self.quiet)
            self.mode = "fallback"

    # ── 图像编码 ─────────────────────────────────────────

    def encode_image(self, image_path: str) -> list[float]:
        """将本地图像文件编码为 768 维向量（list[float]）。"""
        if self.mode == "unavailable":
            return [0.0] * CHINESE_CLIP_DIM

        if self.mode == "fallback":
            return self._encode_image_fallback(image_path)

        # Chinese-CLIP 路径
        try:
            from PIL import Image
            import torch
            from transformers import AutoProcessor

            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)

            # L2 归一化
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            return image_features.cpu().tolist()[0]

        except Exception as exc:
            log(f"  [WARN] 图像编码失败 ({image_path}): {exc}")
            return self._encode_image_fallback(image_path)

    def _encode_image_fallback(self, image_path: str) -> list[float]:
        """降级：提取图像基础特征（像素统计） + 文件名文本。"""
        try:
            from PIL import Image
            import numpy as np

            img = Image.open(image_path).convert("RGB")
            arr = np.array(img, dtype=np.float32) / 255.0

            # 空间统计特征（RGB 均值、标准差、亮度）
            feat = []
            for c in range(3):
                channel = arr[:, :, c]
                feat.append(float(channel.mean()))
                feat.append(float(channel.std()))
            feat.append(float(arr.mean()))  # 整体亮度

            # 调整到 768 维（补零）
            feat += [0.0] * (CHINESE_CLIP_DIM - len(feat))
            return feat[:CHINESE_CLIP_DIM]

        except Exception:
            return [0.0] * CHINESE_CLIP_DIM

    # ── 视频关键帧编码（需要 yt-dlp） ─────────────────────

    def encode_video_url(self, video_url: str, output_dir: str) -> list[float]:
        """
        下载视频关键帧（yt-dlp）并编码。

        参数:
            video_url: 视频页面 URL（如 B站 / 抖音）
            output_dir: 帧图片保存目录

        返回:
            768 维向量 list[float]
        """
        try:
            import cv2
        except ImportError:
            log("  [WARN] opencv-python 未安装，无法提取视频帧", quiet=self.quiet)
            return self._encode_text_fallback(f"video: {video_url}")

        frame_path = self._download_video_frame(video_url, output_dir)
        if frame_path and os.path.exists(frame_path):
            return self.encode_image(frame_path)
        return [0.0] * CHINESE_CLIP_DIM

    def _download_video_frame(self, video_url: str, output_dir: str) -> Optional[str]:
        """使用 yt-dlp 提取视频单个帧图片。"""
        frame_hash = hashlib.md5(video_url.encode()).hexdigest()[:8]
        frame_path = os.path.join(output_dir, f"frame_{frame_hash}.jpg")

        if os.path.exists(frame_path):
            return frame_path  # 命中缓存

        try:
            import subprocess
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--quiet", "--no-warnings",
                "--skip-download",
                "--write-thumbnail",
                "--convert-thumbnails", "jpg",
                "-o", os.path.join(output_dir, f"thumb_{frame_hash}.%(ext)s"),
                video_url,
            ]
            subprocess.run(cmd, capture_output=True, timeout=DOWNLOAD_TIMEOUT + 15)
            # 查找生成的缩略图
            for ext in ["jpg", "jpeg", "png", "webp"]:
                candidate = os.path.join(output_dir, f"thumb_{frame_hash}.{ext}")
                if os.path.exists(candidate):
                    # 转为标准 jpg
                    from PIL import Image
                    img = Image.open(candidate).convert("RGB")
                    img.save(frame_path, "JPEG")
                    os.remove(candidate)
                    return frame_path
        except Exception as exc:
            log(f"  [WARN] 视频帧下载失败 ({video_url}): {exc}")

        # 备选：直接请求 video_url 看能否拿到内容
        resp = safe_request(video_url, stream=True)
        if resp is None:
            return None
        # 写入临时文件
        tmp = os.path.join(output_dir, f"raw_{frame_hash}.mp4")
        try:
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            # 用 OpenCV 读第一帧
            cap = cv2.VideoCapture(tmp)
            ret, frame = cap.read()
            cap.release()
            if ret:
                cv2.imwrite(frame_path, frame)
                return frame_path
        except Exception:
            pass
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return None

    # ── 文本编码 ─────────────────────────────────────────

    def encode_text(self, text: str) -> list[float]:
        """将文本编码为 768 维向量。"""
        if self.mode == "unavailable":
            return [0.0] * CHINESE_CLIP_DIM

        if self.mode == "fallback":
            return self._encode_text_fallback(text)

        try:
            import torch
            from transformers import AutoTokenizer

            inputs = self.tokenizer(
                [text], return_tensors="pt", padding=True, truncation=True, max_length=77
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            return text_features.cpu().tolist()[0]

        except Exception as exc:
            log(f"  [WARN] 文本编码失败: {exc}")
            return self._encode_text_fallback(text)

    def _encode_text_fallback(self, text: str) -> list[float]:
        """
        降级文本编码：基于结巴分词 + 预定义词向量均值的 TF-IDF 简化版。
        输出向量非语义级，但保留了文本长度特征。
        """
        try:
            import jieba
            import numpy as np
            from collections import Counter

            words = list(jieba.cut(text))
            words = [w for w in words if len(w) > 1]  # 过滤单字
            if not words:
                words = list(jieba.cut(text))

            counter = Counter(words)
            tf = {w: c / len(words) for w, c in counter.items()}

            # 简化为词频向量（取高频 50 词，截断到 CHINESE_CLIP_DIM）
            sorted_words = sorted(tf.items(), key=lambda x: -x[1])[:min(50, CHINESE_CLIP_DIM)]
            vec = [v for _, v in sorted_words]
            vec += [0.0] * (CHINESE_CLIP_DIM - len(vec))
            feat = np.array(vec[:CHINESE_CLIP_DIM], dtype=np.float32)
            # L2 归一化
            norm = np.linalg.norm(feat)
            if norm > 1e-8:
                feat = feat / norm
            return feat.tolist()

        except ImportError:
            # 完全没有库：返回文本长度编码的确定性向量
            vec = [len(text) / 1000.0] + [0.0] * (CHINESE_CLIP_DIM - 1)
            return vec

    @property
    def tokenizer(self):
        """懒加载 tokenizer（兼容旧版 transformers）。"""
        if not getattr(self, "_tokenizer", None):
            from transformers import AutoTokenizer
            kwargs = {"trust_remote_code": True}
            if self.cache_dir:
                kwargs["cache_dir"] = self.cache_dir
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, **kwargs)
        return self._tokenizer


# ─────────────────────────────────────────────
# AutoProcessor 兼容补丁
# （某些 transformers 版本没有 OFA-Sys 的 Processor 类）
# ─────────────────────────────────────────────

def _patch_auto_processor():
    try:
        from transformers import AutoProcessor
        from transformers.models.auto.processing_auto import PROCESSING_MAPPING
        # 如果已有 Processor 类则跳过
        if "chinese_clip" in str(PROCESSING_MAPPING).lower():
            return
        # 尝试直接导入
        from transformers import ChineseCLIPProcessor
        # 手动注册
        from transformers.models.auto.configuration_auto import CONFIG_MAPPING
        from transformers.models.auto.processing_auto import PROCESSOR_MAPPING
        if "chinese_clip" not in PROCESSOR_MAPPING:
            PROCESSOR_MAPPING["chinese_clip"] = ChineseCLIPProcessor
    except Exception:
        pass  # 降级方案已在 ChineseCLIPEncoder 中处理


# ─────────────────────────────────────────────
# 特征提取流程
# ─────────────────────────────────────────────

def extract_image_features(
    nodes: list[dict],
    encoder: ChineseCLIPEncoder,
    output_dir: str,
    quiet: bool = False,
) -> list[dict]:
    """从图像节点列表提取特征。"""
    results = []
    log(f"\n[IMAGE] 共 {len(nodes)} 个图像节点", quiet=quiet)

    for i, node in enumerate(nodes):
        mid     = node.get("misconception_id", f"img_{i}")
        ntype   = node.get("type", "")
        url     = node.get("url", "")
        desc    = node.get("desc", "")
        src     = node.get("source", "")
        status  = node.get("status", "unknown")

        entry = {
            "node_type":   "image",
            "misconception_id": mid,
            "type":        ntype,
            "desc":        desc,
            "source":      src,
            "url":         url,
            "url_status":  status,
            "feature_vector": None,
            "feature_mode": encoder.mode,
            "encoding_status": "pending",
        }

        if not url:
            entry["encoding_status"] = "skipped: no_url"
            results.append(entry)
            continue

        # 下载图片
        image_hash = hashlib.md5((url or mid).encode()).hexdigest()[:12]
        img_ext    = "jpg"
        if ".png" in url.lower():
            img_ext = "png"
        img_path = os.path.join(output_dir, f"img_{image_hash}.{img_ext}")

        downloaded = False
        if not os.path.exists(img_path):
            resp = safe_request(url)
            if resp:
                try:
                    with open(img_path, "wb") as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                    downloaded = True
                    time.sleep(REQUEST_DELAY)
                except Exception as exc:
                    log(f"  [WARN] 图片下载失败 ({url}): {exc}", quiet=quiet)
                    entry["encoding_status"] = f"error: download_failed"
            else:
                entry["encoding_status"] = "error: request_failed"
        else:
            downloaded = True

        # 编码
        if downloaded and os.path.exists(img_path):
            try:
                vec = encoder.encode_image(img_path)
                entry["feature_vector"] = vec
                entry["encoding_status"] = "success"
            except Exception as exc:
                entry["encoding_status"] = f"error: {exc}"
        else:
            if entry["encoding_status"] == "pending":
                entry["encoding_status"] = "skipped"

        results.append(entry)
        if not quiet and (i + 1) % 5 == 0:
            log(f"  进度: {i+1}/{len(nodes)}", quiet=quiet)

    success = sum(1 for r in results if r["encoding_status"] == "success")
    log(f"[IMAGE] 完成: {success}/{len(nodes)} 成功", quiet=quiet)
    return results


def extract_video_features(
    nodes: list[dict],
    encoder: ChineseCLIPEncoder,
    output_dir: str,
    quiet: bool = False,
) -> list[dict]:
    """从视频节点列表提取关键帧特征。"""
    results = []
    log(f"\n[VIDEO] 共 {len(nodes)} 个视频节点", quiet=quiet)

    frames_dir = os.path.join(output_dir, "video_frames")
    os.makedirs(frames_dir, exist_ok=True)

    for i, node in enumerate(nodes):
        mid        = node.get("misconception_id", f"vid_{i}")
        platform   = node.get("platform", "")
        url        = node.get("url", "")
        desc       = node.get("desc", "")
        propagation = node.get("propagation", "")

        entry = {
            "node_type":     "video",
            "misconception_id": mid,
            "platform":      platform,
            "desc":          desc,
            "propagation":   propagation,
            "url":           url,
            "feature_vector": None,
            "feature_mode":  encoder.mode,
            "encoding_status": "pending",
        }

        if not url:
            entry["encoding_status"] = "skipped: no_url"
            results.append(entry)
            continue

        # 尝试下载关键帧并编码
        try:
            vec = encoder.encode_video_url(url, frames_dir)
            entry["feature_vector"] = vec
            entry["encoding_status"] = "success"
        except Exception as exc:
            entry["encoding_status"] = f"error: {exc}"
            entry["feature_vector"] = [0.0] * CHINESE_CLIP_DIM

        results.append(entry)
        if not quiet and (i + 1) % 5 == 0:
            log(f"  进度: {i+1}/{len(nodes)}", quiet=quiet)

    success = sum(1 for r in results if r["encoding_status"] == "success")
    log(f"[VIDEO] 完成: {success}/{len(nodes)} 成功", quiet=quiet)
    return results


def extract_propagation_features(
    nodes: list[dict],
    encoder: ChineseCLIPEncoder,
    quiet: bool = False,
) -> list[dict]:
    """
    从传播节点列表提取特征。

    策略：优先抓取 source_url 页面文本编码；
    若抓取失败则以节点元数据文本（platform + desc）编码。
    """
    results = []
    log(f"\n[PROPAGATION] 共 {len(nodes)} 个传播节点", quiet=quiet)

    for i, node in enumerate(nodes):
        mid       = node.get("misconception_id", f"prop_{i}")
        platform  = node.get("platform", "")
        metrics   = node.get("metrics", {})
        source_url = node.get("source_url", "")
        url_type  = node.get("url_type", "")
        url_desc  = node.get("url_desc", "")

        # 构造编码文本：优先 url_desc（权威来源描述），其次 source_url 页面内容
        text_to_encode = url_desc or source_url or f"{platform} {url_type}"
        vec = None
        status = "pending"

        if source_url and source_url.startswith("http"):
            # 尝试抓取页面文本
            try:
                resp = safe_request(source_url, timeout=15)
                if resp:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    page_text = soup.get_text(separator=" ", strip=True)
                    page_text = page_text[:2000]  # 截断防超长
                    if page_text.strip():
                        vec = encoder.encode_text(page_text)
                        status = "success"
                        time.sleep(REQUEST_DELAY)
            except Exception as exc:
                log(f"  [WARN] 页面抓取失败 ({source_url}): {exc}", quiet=quiet)

        # 降级：用 url_desc 元数据文本编码
        if vec is None and url_desc:
            try:
                vec = encoder.encode_text(url_desc)
                status = "success (fallback: url_desc)"
            except Exception:
                vec = [0.0] * CHINESE_CLIP_DIM
                status = "error"

        if vec is None:
            vec = [0.0] * CHINESE_CLIP_DIM
            status = "skipped: no_text"

        entry = {
            "node_type":     "propagation",
            "misconception_id": mid,
            "platform":      platform,
            "metrics":       metrics,
            "source_url":    source_url,
            "url_type":      url_type,
            "url_desc":      url_desc,
            "text_encoded":  text_to_encode[:200],
            "feature_vector": vec,
            "feature_mode":  encoder.mode,
            "encoding_status": status,
        }
        results.append(entry)

    success = sum(1 for r in results if "success" in r["encoding_status"])
    log(f"[PROPAGATION] 完成: {success}/{len(nodes)} 成功", quiet=quiet)
    return results


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    _patch_auto_processor()

    # ── 1. 定位数据集 ───────────────────────────────────
    log("[INFO] 查找 mentalguard_v2.0.json ...", quiet=args.quiet)
    dataset_path = find_dataset_path(args.input)
    output_path  = Path(args.output) if args.output else dataset_path.parent / "multimodal_features.json"
    output_path  = output_path.resolve()

    log(f"[INFO] 数据集: {dataset_path}", quiet=args.quiet)
    log(f"[INFO] 输出:   {output_path}", quiet=args.quiet)
    log(f"[INFO] 模式:   {args.mode}", quiet=args.quiet)

    # ── 2. 加载数据集 JSON ───────────────────────────────
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mm_ext = data.get("multimodal_kg_extensions", {})
    image_nodes = mm_ext.get("image_nodes", [])
    video_nodes = mm_ext.get("video_nodes", [])
    prop_nodes  = mm_ext.get("propagation_nodes", [])

    log(f"[INFO] 图像节点: {len(image_nodes)}", quiet=args.quiet)
    log(f"[INFO] 视频节点: {len(video_nodes)}", quiet=args.quiet)
    log(f"[INFO] 传播节点: {len(prop_nodes)}", quiet=args.quiet)

    # ── 3. 创建输出目录 ──────────────────────────────────
    output_dir = output_path.parent
    images_dir = output_dir / "multimodal_images"
    os.makedirs(images_dir, exist_ok=True)
    log(f"[INFO] 媒体缓存目录: {images_dir}", quiet=args.quiet)

    # ── 4. 初始化编码器 ──────────────────────────────────
    encoder = None
    if not args.skip_clip:
        encoder = ChineseCLIPEncoder(
            model_name=CHINESE_CLIP_MODEL,
            device=args.device,
            cache_dir=args.cache_dir,
            quiet=args.quiet,
        )
    else:
        log("[INFO] 已跳过 Chinese-CLIP 编码（--skip-clip）", quiet=args.quiet)

    # ── 5. 提取各类型节点特征 ────────────────────────────
    results: list[dict] = []
    metadata_summary = {
        "dataset_version":    data.get("meta", {}).get("version", "unknown"),
        "extraction_time":    time.strftime("%Y-%m-%dT%H:%M:%S"),
        "encoder_model":     CHINESE_CLIP_MODEL if encoder else None,
        "encoder_mode":      encoder.mode if encoder else "skipped",
        "chinese_clip_dim":  CHINESE_CLIP_DIM,
        "total_image_nodes": len(image_nodes),
        "total_video_nodes": len(video_nodes),
        "total_prop_nodes":  len(prop_nodes),
    }

    if args.mode in ("all", "image"):
        results += extract_image_features(image_nodes, encoder, str(images_dir), quiet=args.quiet)

    if args.mode in ("all", "video"):
        results += extract_video_features(video_nodes, encoder, str(images_dir), quiet=args.quiet)

    if args.mode in ("all", "propagation"):
        results += extract_propagation_features(prop_nodes, encoder, quiet=args.quiet)

    # ── 6. 统计汇总 ─────────────────────────────────────
    total   = len(results)
    success = sum(1 for r in results if "success" in r.get("encoding_status", ""))
    failed  = sum(1 for r in results if r.get("encoding_status", "").startswith("error"))
    skipped = sum(1 for r in results if r.get("encoding_status", "").startswith("skipped"))

    log(f"\n[完成] 成功 {success}/{total}，失败 {failed}，跳过 {skipped}", quiet=args.quiet)

    # ── 7. 写入输出文件 ──────────────────────────────────
    output_data = {
        "meta": metadata_summary,
        "stats": {
            "total": total,
            "success": success,
            "failed":  failed,
            "skipped": skipped,
        },
        "nodes": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    log(f"[完成] 特征文件已保存: {output_path}", quiet=args.quiet)

    # ── 8. 提示用户上传 Zenodo ───────────────────────────
    if not args.skip_clip:
        log(
            "\n[提示] 建议将 multimodal_features.json 上传到 Zenodo，"
            "以进一步提升可重现性：\n"
            "  Zenodo DOI: 10.5281/zenodo.21774699\n"
            "  文件大小约: " + _estimate_size(results) + " KB",
            quiet=args.quiet,
        )


def _estimate_size(results: list[dict]) -> str:
    """估算特征文件大小（字符串化后近似）。"""
    try:
        s = json.dumps(results)
        kb = len(s.encode("utf-8")) / 1024
        return f"{kb:.1f}"
    except Exception:
        return "~15"


# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()
