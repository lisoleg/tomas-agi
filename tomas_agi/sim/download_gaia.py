# -*- coding: utf-8 -*-
"""
download_gaia.py — GAIA 数据集下载脚本（支持多种方法）

方法 1: datasets 库（优先，支持镜像）
方法 2: hf_hub_download（直接下载，绕过 HF 数据集加载器）
方法 3: 生成模拟 GAIA 数据（离线回退）

用法：
  python download_gaia.py --method datasets   # 方法1（默认）
  python download_gaia.py --method hf_hub     # 方法2
  python download_gaia.py --method mock        # 方法3（模拟数据）
  python download_gaia.py --output data/gaia.jsonl
  python download_gaia.py --mirror tsinghua   # 使用清华镜像
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── 配置 ────────────────────────────────────────────────
DEFAULT_OUTPUT = "data/gaia.jsonl"
HF_DATASET_REPO = "gaia-benchmark/GAIA"
HF_TOKEN = os.environ.get("HUGGINGFACE_TOKEN", "")

# 清华镜像（如果 HuggingFace 官方不可用）
HUGGINGFACE_MIRRORS = {
    "official": "https://datasets-server.huggingface.co",
    "tsinghua": "https://hf-mirror.com",
    "modelscope": "https://www.modelscope.cn",  # ModelScope 镜像
}


# ─── 方法 1: datasets 库（支持镜像 + 超时配置）────────────────────────────
def download_via_datasets(
    output_path: str,
    mirror: str = "official",
    timeout: int = 120,
    max_retries: int = 3,
) -> int:
    """
    使用 datasets 库下载 GAIA 数据集。

    Args:
        output_path: 输出文件路径
        mirror: 镜像源（official / tsinghua / modelscope）
        timeout: 超时时间（秒）
        max_retries: 最大重试次数

    Returns:
        下载样本数
    """
    print(f"[1/3] 使用 datasets 库下载（镜像: {mirror}）...")
    try:
        import datasets  # type: ignore
        from datasets import load_dataset, DownloadConfig
    except ImportError:
        print("  [ERROR] datasets 库未安装，请运行: pip install datasets")
        return -1

    # 设置镜像（如果可用）
    if mirror == "tsinghua":
        os.environ["HF_ENDPOINT"] = HUGGINGFACE_MIRRORS["tsinghua"]
        print(f"  已设置镜像: {HUGGINGFACE_MIRRORS['tsinghua']}")
    elif mirror == "modelscope":
        print("  [INFO] ModelScope 镜像需要 datasets >= 2.0，尝试中...")

    download_config = DownloadConfig(
        cache_dir=None,
        force_download=False,
        resume_download=True,
        max_retries=max_retries,
        timeout=timeout,
    )

    print(f"  正在加载数据集: {HF_DATASET_REPO}")
    print(f"  超时设置: {timeout}s, 最大重试: {max_retries}")

    try:
        dataset = load_dataset(
            HF_DATASET_REPO,
            split="validation",  # 或 "test"
            download_config=download_config,
            token=HF_TOKEN if HF_TOKEN.startswith("hf_") else None,
        )
        print(f"  [OK] 数据集加载成功，样本数: {len(dataset)}")

        # 保存为 JSONL
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for i, sample in enumerate(dataset):
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                if (i + 1) % 50 == 0:
                    print(f"  已写入 {i + 1} 条...")

        print(f"  [OK] 已保存 {len(dataset)} 条到: {output_path}")
        return len(dataset)

    except Exception as e:
        print(f"  [ERROR] datasets 加载失败: {e}")
        print(f"  尝试方法 2 (hf_hub_download)...")
        return -1


# ─── 方法 2: hf_hub_download（直接下载原始文件）─────────────────────
def download_via_hf_hub(
    output_dir: str,
    filename: str = "validation.jsonl",
    mirror: str = "official",
    timeout: int = 120,
) -> int:
    """
    使用 huggingface_hub 的 hf_hub_download 直接下载文件。

    绕过 datasets 库，直接下载原始 .jsonl 文件。
    """
    print(f"[2/3] 使用 hf_hub_download 直接下载...")
    try:
        from huggingface_hub import hf_hub_download, HfFileSystem
    except ImportError:
        print("  [ERROR] huggingface_hub 未安装，请运行: pip install huggingface_hub")
        return -1

    # 设置镜像
    if mirror == "tsinghua":
        os.environ["HF_ENDPOINT"] = HUGGINGFACE_MIRRORS["tsinghua"]
        print(f"  已设置镜像: {HUGGINGFACE_MIRRORS['tsinghua']}")

    try:
        print(f"  正在下载: {HF_DATASET_REPO}/{filename}")
        filepath = hf_hub_download(
            repo_id=HF_DATASET_REPO,
            filename=filename,
            repo_type="dataset",
            token=HF_TOKEN if HF_TOKEN.startswith("hf_") else None,
            cache_dir=None,
        )
        print(f"  [OK] 下载成功: {filepath}")

        # 复制到目标路径
        import shutil
        os.makedirs(output_dir, exist_ok=True)
        target = os.path.join(output_dir, os.path.basename(filename))
        shutil.copy(filepath, target)
        print(f"  [OK] 已复制到: {target}")

        # 统计行数
        with open(target, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f)
        return count

    except Exception as e:
        print(f"  [ERROR] hf_hub_download 失败: {e}")
        print(f"  尝试方法 3 (模拟数据）...")
        return -1


# ─── 方法 3: 生成模拟 GAIA 数据（离线回退）─────────────────────
def generate_mock_gaia(output_path: str, num_samples: int = 100) -> int:
    """
    生成模拟 GAIA 数据用于测试。

    GAIA 格式（简化）：
      - task_id: 任务 ID
      - question: 问题文本
      - answer: 参考答案（字符串或列表）
      - level: 难度等级（1-3）
      - file_name: 附件文件名（可选）
    """
    print(f"[3/3] 生成模拟 GAIA 数据（离线模式）...")

    mock_questions = [
        "怎么计算一个圆柱的体积？请给出公式和计算步骤。",
        "解释量子纠缠的基本原理，并举例说明。",
        "编写一个 Python 函数，实现快速排序算法。",
        "分析全球变暖的主要原因和可能的影响。",
        "比较监督学习、无监督学习和强化学习的区别。",
        "如何设计一个高可用的分布式系统架构？",
        "解释区块链的工作原理，包括挖矿和共识机制。",
        "用中文回答：什么是费米悖论？",
        "给定一个包含 100 万个整数的数组，如何高效找到中位数？",
        "设计一个实验验证牛顿第二定律。",
    ]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i in range(num_samples):
            q = mock_questions[i % len(mock_questions)]
            sample = {
                "task_id": f"mock_gaia_{i:05d}",
                "question": q,
                "answer": f"[模拟答案] 这是对问题的模拟回答，用于 AEGIS 基准测试。",
                "level": (i % 3) + 1,
                "file_name": None,
                "mock": True,
            }
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"  [OK] 已生成 {num_samples} 条模拟数据: {output_path}")
    print(f"  [WARN] 这是模拟数据，仅用于测试 AEGIS 管道！")
    return num_samples


# ─── 方法 4: 直接 HTTP 下载（备用）─────────────────────────────
def download_via_http(
    output_path: str,
    url: str = "https://huggingface.co/datasets/gaia-benchmark/GAIA/resolve/main/validation.jsonl",
    timeout: int = 120,
    chunk_size: int = 8192,
) -> int:
    """
    直接使用 urllib 下载（最原始方法，可自定义 URL 和超时）。
    """
    print(f"[4/4] 使用 HTTP 直接下载...")
    print(f"  URL: {url}")

    # 设置清华镜像 URL（如果官方不可用）
    if "huggingface.co" in url:
        mirror_url = url.replace("huggingface.co", "hf-mirror.com")
        print(f"  镜像 URL: {mirror_url}")
        url = mirror_url

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TOMAS/1.0)",
                "Accept": "application/jsonlines",
            },
        )
        if HF_TOKEN.startswith("hf_"):
            req.add_header("Authorization", f"Bearer {HF_TOKEN}")

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "wb") as f:
                downloaded = 0
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (1024 * 1024) == 0:
                        print(f"  已下载 {downloaded // (1024*1024)} MB...")

        # 统计行数
        with open(output_path, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f)
        print(f"  [OK] 下载完成: {output_path} ({count} 条)")
        return count

    except Exception as e:
        print(f"  [ERROR] HTTP 下载失败: {e}")
        return -1


# ─── 主流程 ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="GAIA 数据集下载脚本（支持多种方法）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python download_gaia.py --method datasets        # 使用 datasets 库（默认）
  python download_gaia.py --method hf_hub          # 使用 hf_hub_download
  python download_gaia.py --method mock             # 生成模拟数据（离线）
  python download_gaia.py --method http             # HTTP 直接下载
  python download_gaia.py --mirror tsinghua      # 使用清华镜像
  python download_gaia.py --timeout 300          # 设置超时 300s
  python download_gaia.py --output data/gaia.jsonl
""",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["datasets", "hf_hub", "mock", "http"],
        default="datasets",
        help="下载方法（默认: datasets）",
    )
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="输出文件路径")
    parser.add_argument(
        "--mirror",
        type=str,
        choices=["official", "tsinghua", "modelscope"],
        default="official",
        help="镜像源（默认: official）",
    )
    parser.add_argument("--timeout", type=int, default=120, help="超时时间（秒，默认 120）")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数（默认 3）")
    parser.add_argument("--num-mock", type=int, default=100, help="模拟数据条数（默认 100）")
    args = parser.parse_args()

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print("=" * 60)
    print("  GAIA 数据集下载脚本")
    print(f"  方法: {args.method}")
    print(f"  输出: {output_path}")
    print(f"  镜像: {args.mirror}")
    print(f"  超时: {args.timeout}s")
    print("=" * 60)

    count = -1

    if args.method == "datasets":
        count = download_via_datasets(
            output_path=output_path,
            mirror=args.mirror,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )
        if count <= 0:
            print("\n[WARN] 方法 1 失败，尝试方法 2...")
            count = download_via_hf_hub(
                output_dir=os.path.dirname(output_path) or ".",
                filename="validation.jsonl",
                mirror=args.mirror,
                timeout=args.timeout,
            )

    elif args.method == "hf_hub":
        count = download_via_hf_hub(
            output_dir=os.path.dirname(output_path) or ".",
            filename="validation.jsonl",
            mirror=args.mirror,
            timeout=args.timeout,
        )

    elif args.method == "http":
        url = "https://huggingface.co/datasets/gaia-benchmark/GAIA/resolve/main/validation.jsonl"
        count = download_via_http(
            output_path=output_path,
            url=url,
            timeout=args.timeout,
        )

    elif args.method == "mock":
        count = generate_mock_gaia(
            output_path=output_path,
            num_samples=args.num_mock,
        )

    # 汇总
    print("\n" + "=" * 60)
    if count > 0:
        print(f"  [OK] 共 {count} 条数据已保存到: {output_path}")
        print(f"  可用于 AEGIS 基准测试：")
        print(f"    python bench_aegis.py --gaia-data {output_path}")
    else:
        print(f"  [ERROR] 所有下载方法均失败！")
        print(f"  建议：")
        print(f"    1. 检查网络连接")
        print(f"    2. 使用模拟数据: --method mock")
        print(f"    3. 手动下载后放到: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
