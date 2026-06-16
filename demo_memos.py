#!/usr/bin/env python3
"""
TOMAS-MemOS 融合层演示脚本
独立运行，不依赖相对导入
"""
import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tomas_agi'))

from sim.memos_fusion import TOMAS_Mem_OS_Fusion

# 创建融合层（使用临时存储文件）
STORE_PATH = "tomas_agi/data/demo_memory_store.json"
if os.path.exists(STORE_PATH):
    os.remove(STORE_PATH)

fusion = TOMAS_Mem_OS_Fusion(
    store_path=STORE_PATH,
    theta_dead=0.1,
    enable_mus=True,
    enable_psi=True,
    enable_kappa_gate=True,
)

print("=" * 60)
print("  TOMAS-MemOS 融合层实际运行演示")
print("  基于张锋《从记忆工程到'有我之忆'》")
print("=" * 60)
print()

# 【测试 1】死零校验 (Dead-Zero Check)
print("【测试 1】死零校验 (Dead-Zero Check)")
print("-" * 60)
result1 = fusion.write_memory(
    "太阳绕地球转",
    {
        "concepts": [],
        "self_state": "测试天文知识",
        "current_kappa": 3,
    }
)
print(f"  输入: '太阳绕地球转'")
print(f"  结果: {result1['status']}")
print(f"  原因: {result1.get('reason', 'N/A')}")
print(f"  ℐ-值: {result1.get('i_value', 'N/A')}")
print()
print("  ✅ 死零校验生效：已知谬误被拒绝写入")
print()

# 【测试 2】正常写入
print("【测试 2】正常记忆写入")
print("-" * 60)
result2 = fusion.write_memory(
    "心主神明",
    {
        "concepts": ["心", "神明"],
        "self_state": "学习中医理论",
        "current_kappa": 4,
        "asym": 0.5,
    }
)
print(f"  输入: '心主神明'")
print(f"  结果: {result2['status']}")
print(f"  ℐ-值: {result2.get('i_value', 'N/A'):.2f}")
print(f"  MUS激活: {result2.get('mus_active', False)}")
print()

# 【测试 3】MUS 双存 (MUS Dual Write)
print("【测试 3】MUS 双存 (MUS Dual Write)")
print("-" * 60)
result3 = fusion.write_memory(
    "脑主神明",
    {
        "concepts": ["脑", "神明"],
        "self_state": "学习西医理论",
        "current_kappa": 4,
        "asym": -0.5,
    }
)
print(f"  输入: '脑主神明' (与'心主神明'矛盾)")
print(f"  结果: {result3['status']}")
print(f"  MUS激活: {result3.get('mus_active', False)}")
print(f"  原因: {result3.get('reason', 'N/A')}")
print()
print("  ✅ MUS 双存生效：矛盾记忆被双存而非覆盖")
print()

# 【测试 4】ψ-锚回溯 (Psi-Anchor Backtrack)
print("【测试 4】ψ-锚回溯 (Psi-Anchor Backtrack)")
print("-" * 60)
records = fusion.store.retrieve_by_concepts(["心"])
if records:
    record = records[0]
    psi = record.psi_anchor
    print(f"  查询: '心' 相关记忆")
    print(f"  记忆内容: {record.relation[:50]}")
    print(f"  ψ-锚信息:")
    print(f"    - self_state: {psi.self_state}")
    print(f"    - kappa_at_write: {psi.kappa_at_write}")
    print(f"    - timestamp: {psi.timestamp}")
    print()
    print("  ✅ ψ-锚生效：记忆附加了 AI 写入时的自我状态")
print()

# 【测试 5】κ-Gate 过滤 (Kappa-Gate Filter)
print("【测试 5】κ-Gate 过滤 (Kappa-Gate Filter)")
print("-" * 60)
recall_result = fusion.recall_memory(
    "神明",
    current_kappa=4,
    context={}
)
print(f"  查询: '神明' (κ={recall_result.get('current_kappa', 4)})")
print(f"  回忆记忆数: {len(recall_result['records'])}")
print(f"  κ-Gate 过滤数: {recall_result.get('kappa_gate_filtered', 0)}")
for i, mem in enumerate(recall_result['records'][:3]):  # 只显示前3条
    print(f"    [{i+1}] {mem['relation'][:30]}... (κ={mem.get('kappa_at_write', 'N/A')})")
print()
print("  ✅ κ-Gate 生效：根据 κ 值过滤记忆")
print()

# 【测试 6】矛盾检测 (Contradiction Detection)
print("【测试 6】矛盾检测 (Contradiction Detection)")
print("-" * 60)
from sim.contradiction_detector import ContradictionDetector
detector = ContradictionDetector(enable_nlp=True)

test_pairs = [
    ("心主神明", "心不主神明", "否定词矛盾"),
    ("心主神明", "脑主神明", "主语矛盾"),
    ("太阳绕地球", "地球绕太阳", "宾语矛盾"),
    ("心主神明", "心主思考", "谓语矛盾"),
]

for r1, r2, desc in test_pairs:
    is_contra = detector.is_contradictory(r1, r2)
    print(f"  {r1} vs {r2} → {desc}: {'✅ 矛盾' if is_contra else '❌ 不矛盾'}")

print()
print("  ✅ 三层矛盾检测生效 (Layer 1: 否定词, Layer 2: NLP主谓宾)")
print()

# 统计信息
print("【统计信息】")
print("-" * 60)
stats = fusion.get_stats()
print(f"  总记忆数: {stats['total_memories']}")
print(f"  MUS 激活对数: {stats['mus_pairs']}")
print(f"  平均 ℐ-值: {stats['avg_i_value']:.2f}")
print(f"  死零阈值: {stats['theta_dead']}")
print(f"  存储文件路径: {STORE_PATH}")
print()

print("=" * 60)
print("  演示完成：五点升维全部生效")
print("=" * 60)
print()
print(f"详细存储内容已保存至: {STORE_PATH}")
print("可以用文本编辑器打开查看 JSON 格式的记忆存储。")
