# -*- coding: utf-8 -*-
"""
SWE-bench Lite 评估脚本（直接调用 DeepSeek API）
=================================================

TOMAS/太极OS 参与 SWE-bench Lite 评测。
每个实例的问题描述发给 LLM，取回回答后与 ground-truth patch 比对。

用法：
  python swe_bench_eval.py --data-path data/swe_bench_lite.json --output results/swe_bench_lite.csv
  python swe_bench_eval.py --dry-run               # 测试前 3 个实例
  python swe_bench_eval.py --api-key sk-xxx          # 手动传 Key
"""

import json
import csv
import os
import sys
import time
import argparse
import requests
from typing import Dict, List, Optional


# ── 加载 .env 文件（若存在）────────────────────────────────────────
def _load_env(path=".env"):
    """手动解析 .env 文件，写入 os.environ。"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")
            os.environ.setdefault(key, val)

_load_env(os.path.join(os.path.dirname(__file__), ".env"))


# ── 配置 ───────────────────────────────────────────────────────────────────
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_OUTPUT_DIR = "results"
# ──────────────────────────────────────────────────────────────────────────────


def call_deepseek(problem: str,
                 api_key: str,
                 model: str = DEEPSEEK_MODEL,
                 max_tokens: int = 2048,
                 temperature: float = 0.7) -> str:
    """
    调用 DeepSeek API 生成回答。
    返回 LLM 输出的纯文本。
    """
    if not api_key:
        raise ValueError("未设置 DeepSeek API Key（--api-key 或 DEEPSEEK_API_KEY 环境变量）")

    url = f"{DEEPSEEK_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": (
                "You are a helpful software engineer. "
                "Read the problem statement carefully and provide a solution patch. "
                "Output ONLY the code changes in unified diff format."
            )},
            {"role": "user", "content": problem},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        raise RuntimeError("DeepSeek API 请求超时（>120s）")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"DeepSeek API 请求失败：{e}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"DeepSeek API 响应格式异常：{e}")


def evaluate_instance(instance: Dict, api_key: str) -> Dict:
    """
    评估单个 SWE-bench 实例。
    调用 LLM 获取回答，记录结果。
    """
    instance_id = instance.get('instance_id', 'unknown')
    problem = instance.get('problem_statement', '')
    patch = instance.get('patch', '')

    result = {
        'instance_id': instance_id,
        'repo': instance.get('repo', ''),
        'has_patch': bool(patch),
        'prediction': None,
        'correct': None,
        'error': None,
        'duration_sec': 0.0,
    }

    start = time.time()
    try:
        prediction = call_deepseek(problem, api_key)
        result['prediction'] = prediction
        # TODO: 与 patch 比较，判定 correct
        # 当前先记为 None，后续用 evaluate_patch() 补充
        result['correct'] = None
    except Exception as e:
        result['error'] = str(e)
        result['prediction'] = f"[ERROR] {str(e)[:200]}"

    result['duration_sec'] = round(time.time() - start, 2)
    return result


def evaluate_patch(prediction: str, ground_truth_patch: str) -> Optional[bool]:
    """
    将 LLM 输出与 ground-truth patch 比较，判定是否正确。
    当前为占位实现，后续可接入：
      - 精确匹配（prediction == patch）
      - 模糊匹配（normalized diff）
      - 执行测试（如需运行环境）
    """
    if not prediction or not ground_truth_patch:
        return None
    # 占位：先检查预测是否包含 patch 的关键部分
    # TODO: 实现真正的 patch 比对逻辑
    return None


def load_instances(data_path: str, max_instances: int = 0) -> List[Dict]:
    """加载 SWE-bench Lite 实例。"""
    if not os.path.exists(data_path):
        print(f"[SWE-Bench] 数据集不存在: {data_path}")
        print(f"[SWE-Bench] 请确认文件路径正确")
        sys.exit(1)

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    instances = data if isinstance(data, list) else data.get('instances', [])
    if max_instances > 0:
        instances = instances[:max_instances]

    print(f"[SWE-Bench] 加载了 {len(instances)} 个实例")
    return instances


def run_evaluation(instances: List[Dict], output_path: str, api_key: str) -> None:
    """运行完整评估并写入 CSV。"""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    fieldnames = ['instance_id', 'repo', 'has_patch', 'prediction', 'correct', 'error', 'duration_sec']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, instance in enumerate(instances, 1):
            inst_id = instance.get('instance_id', '')
            repo = instance.get('repo', '')
            print(f"[SWE-Bench] 评估实例 {i}/{len(instances)}: {inst_id} ({repo})")

            result = evaluate_instance(instance, api_key)
            writer.writerow(result)
            f.flush()  # 实时写入，防止中断丢失

            # 打印简要结果
            if result['error']:
                print(f"    ❌ 错误: {result['error'][:80]}")
            else:
                pred_preview = (result['prediction'] or '')[:80].replace('\n', ' ')
                print(f"    ✅ 预测: {pred_preview}...")

    print(f"\n[SWE-Bench] 评估完成，结果写入: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="SWE-bench Lite 评估脚本（TOMAS/太极OS）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 干跑前 3 个实例（测试脚本逻辑）
  python swe_bench_eval.py --dry-run

  # 完整评估（需 DeepSeek API Key）
  python swe_bench_eval.py --data-path data/swe_bench_lite.json --output results/swe_bench_lite.csv

  # 用环境变量传 Key
  set DEEPSEEK_API_KEY=sk-xxx
  python swe_bench_eval.py
"""
    )
    parser.add_argument('--data-path', '-i', type=str, default='data/swe_bench_lite.json',
                        help='SWE-bench Lite 数据集路径')
    parser.add_argument('--output', '-o', type=str, default='results/swe_bench_lite.csv',
                        help='输出 CSV 路径')
    parser.add_argument('--api-key', type=str, default=os.environ.get('DEEPSEEK_API_KEY', ''),
                        help='DeepSeek API Key（也可设 DEEPSEEK_API_KEY 环境变量）')
    parser.add_argument('--max-instances', type=int, default=0,
                        help='最大评估实例数（0=全部）')
    parser.add_argument('--dry-run', action='store_true',
                        help='干跑前 3 个实例（不调用 API，测试脚本逻辑）')
    args = parser.parse_args()

    # 检查 API Key
    if not args.dry_run and not args.api_key:
        print("[SWE-Bench] ❌ 未设置 DeepSeek API Key")
        print("[SWE-Bench] 用法: --api-key sk-xxx 或 环境变量 DEEPSEEK_API_KEY")
        sys.exit(1)

    # 加载实例
    instances = load_instances(args.data_path, args.max_instances if not args.dry_run else 3)

    # 运行评估
    if args.dry_run:
        print("[SWE-Bench] 干跑模式：测试前 3 个实例的脚本逻辑（不调用 API）")
        # 干跑：只测试实例加载和结果写入，不调用 API
        api_key = args.api_key or 'dummy'
        # 用短问题替换 problem_statement，测试调用逻辑
        for inst in instances:
            inst['problem_statement'] = f"[DRY RUN] 请简单介绍一下 Python 的 GIL（全局解释器锁）。"
    else:
        api_key = args.api_key

    run_evaluation(instances, args.output, api_key)

    print(f"\n{'='*60}")
    print("  SWE-bench Lite 评估完成")
    print(f"{'='*60}")
    print(f"  结果文件: {args.output}")
    print(f"  实例数: {len(instances)}")
    print(f"  API Key: {'已配置' if api_key else '❌ 未配置'}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
