"""
GAIA 评估脚本
=====================================

运行 TOMAS-AGI (via DeepSeek API) against GAIA benchmark.

用法：
  python gaia_eval.py --data-path data/gaia.json --output results/gaia.csv
  python gaia_eval.py --dry-run  # 测试前 3 个实例
"""

import json
import csv
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Optional

import requests


# ── .env 加载 ─────────────────────────────────────────────────────
def _load_env():
    """从 sim/.env 加载环境变量（不依赖 python-dotenv）"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, val = line.partition('=')
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val

_load_env()


# ── 配置 ────────────────────────────────────────────────────────────
GAIA_URL = "https://huggingface.co/datasets/gaia-benchmark/GAIA"
DEFAULT_OUTPUT_DIR = "results"
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
# ────────────────────────────────────────────────────────────────────────


def _get_api_key() -> str:
    key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not key:
        print("[GAIA] ❌ DEEPSEEK_API_KEY 未配置（请在 .env 或环境变量中设置）")
        sys.exit(1)
    return key


def call_deepseek(question: str,
                  api_key: str,
                  model: str = DEEPSEEK_MODEL,
                  system_prompt: str = "",
                  timeout: int = 300) -> str:
    """调用 DeepSeek Chat API，返回回答文本。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": question})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2048,
        "stream": False,
    }

    resp = requests.post(
        f"{DEEPSEEK_API_BASE}/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def download_gaia(output_path: str) -> str:
    """检查 GAIA 数据集是否存在。"""
    if os.path.exists(output_path):
        return output_path
    print(f"[GAIA] 数据集不存在: {output_path}")
    print(f"[GAIA] 请手动下载: {GAIA_URL}")
    print(f"[GAIA] 然后放置到: {output_path}")
    sys.exit(1)


def load_instances(data_path: str, max_instances: int = 0) -> List[Dict]:
    """加载 GAIA 实例。"""
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    instances = data if isinstance(data, list) else data.get('instances', [])
    if max_instances > 0:
        instances = instances[:max_instances]
    print(f"[GAIA] 加载了 {len(instances)} 个实例")
    return instances


def evaluate_instance(instance: Dict, api_key: str) -> Dict:
    """评估单个 GAIA 实例：调用 DeepSeek API 回答问题，与标准答案比较。"""
    instance_id = instance.get('task_id', 'unknown')
    question = instance.get('Question', '')
    answer = instance.get('Answer', '')
    level = instance.get('Level', 0)

    result = {
        'task_id': instance_id,
        'level': level,
        'has_answer': bool(answer),
        'prediction': None,
        'correct': None,
        'error': None,
        'duration_sec': 0.0,
    }

    start = time.time()
    try:
        system_prompt = (
            "You are a knowledgeable AI assistant. Answer the user's question "
            "as concisely and accurately as possible. If the answer is a single "
            "word or short phrase, provide just that. Do not add explanations "
            "unless asked."
        )
        prediction = call_deepseek(question, api_key, system_prompt=system_prompt)
        result['prediction'] = prediction

        # 简单匹配：答案是否出现在预测中（不区分大小写）
        if answer and prediction:
            ans_lower = answer.lower().strip()
            pred_lower = prediction.lower()
            result['correct'] = ans_lower in pred_lower

    except Exception as e:
        result['error'] = str(e)

    result['duration_sec'] = round(time.time() - start, 2)
    return result


def run_evaluation(instances: List[Dict], output_path: str, api_key: str) -> None:
    """运行完整评估并写入 CSV。"""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    fieldnames = ['task_id', 'level', 'has_answer', 'prediction', 'correct', 'error', 'duration_sec']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        correct_count = 0
        for i, instance in enumerate(instances, 1):
            task_id = instance.get('task_id', '')
            print(f"[GAIA] 评估实例 {i}/{len(instances)}: {task_id}")
            result = evaluate_instance(instance, api_key)
            writer.writerow(result)
            f.flush()

            status = "✅" if result.get('correct') else "❌"
            pred_short = (result.get('prediction') or '')[:60]
            print(f"    {status} 预测: {pred_short}...")
            if result.get('correct'):
                correct_count += 1

    print(f"\n[GAIA] 评估完成，结果写入: {output_path}")
    print(f"[GAIA] 正确: {correct_count}/{len(instances)}")


def main():
    parser = argparse.ArgumentParser(
        description="GAIA 评估脚本（DeepSeek API）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 干跑前 3 个实例（测试脚本逻辑）
  python gaia_eval.py --dry-run

  # 完整评估
  python gaia_eval.py --data-path data/gaia.json --output results/gaia.csv
"""
    )
    parser.add_argument('--data-path', '-i', type=str, default='data/gaia.json',
                        help='GAIA 数据集路径')
    parser.add_argument('--output', '-o', type=str, default='results/gaia.csv',
                        help='输出 CSV 路径')
    parser.add_argument('--max-instances', type=int, default=0,
                        help='最大评估实例数（0=全部）')
    parser.add_argument('--dry-run', action='store_true',
                        help='干跑前 3 个实例（测试脚本逻辑）')
    args = parser.parse_args()

    # 获取 API Key
    api_key = _get_api_key()
    print(f"[GAIA] API Key: {api_key[:8]}...")

    # 检查数据集
    data_path = args.data_path
    if not os.path.exists(data_path):
        print(f"[GAIA] ❌ 数据集不存在: {data_path}")
        sys.exit(1)

    # 加载实例
    max_inst = 3 if args.dry_run else args.max_instances
    instances = load_instances(data_path, max_inst)

    if args.dry_run:
        print("[GAIA] 干跑模式：测试前 3 个实例")

    # 运行评估
    run_evaluation(instances, args.output, api_key)

    print(f"\n{'='*60}")
    print("  GAIA 评估完成")
    print(f"{'='*60}")
    print(f"  结果文件: {args.output}")
    print(f"  实例数: {len(instances)}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
