"""
E2E 冒烟测试 — 验证 TOMAS V3 推理链路端到端可用
=====================================================
覆盖：EML 加载 → φ-Gate 检查 → 推理路由 → 创造性引擎
"""
import sys
import os
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sim"))

from token_bridge import (
    TokenBridge,
    InferenceEngine,
    CreativeEngine,
    PhiGate,
    EMLFileLoader,
    text_to_octonion,
)


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def test_eml_loading():
    """1. EML 文件加载 → 验证知识图谱结构"""
    eml_files = [
        ("物理", "physics_distilled.eml"),
        ("化学", "chemistry_distilled.eml"),
        ("医学", "medicine_distilled.eml"),
    ]

    passed = 0
    for domain, fname in eml_files:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            print(f"  ⏭  EML '{fname}' 不存在，跳过")
            continue

        loader = EMLFileLoader()
        loader.load_file(path)
        v_count = len(loader.vertices)
        e_count = len(loader.edges)
        assert v_count > 0, f"{domain} EML 无顶点"
        assert e_count > 0, f"{domain} EML 无边"
        print(f"  ✅ {domain}: {v_count} 顶点, {e_count} 边")
        passed += 1

    assert passed > 0, "至少需加载一个 EML 文件"
    return True


def test_phi_gate():
    """2. φ-Gate 概念提取与一致性检查"""
    bridge = TokenBridge()

    # 加载一个 EML 以提供上下文
    phys_path = os.path.join(DATA_DIR, "physics_distilled.eml")
    if os.path.exists(phys_path):
        bridge.load_eml(phys_path)
        print(f"  ✅ φ-Gate 已加载 EML: {len(bridge.loader.vertices)} 顶点")
    else:
        print("  ⚠️  无 EML 可用，φ-Gate 回退模式")

    gate = PhiGate(bridge)

    # 测试概念提取
    text = "物理是研究物质运动的科学，牛顿提出了万有引力定律。"
    concepts = gate.extract_concepts(text)
    assert len(concepts) > 0, "未提取到概念"
    print(f"  ✅ 概念提取: {concepts[:5]}")

    # 测试一致性检查
    llm_output = "水在标准大气压下的沸点是100摄氏度。"
    dummy_query = {
        "matched_concepts": [],
        "subgraph": {"vertices": []},
    }
    result = gate.check(llm_output, dummy_query)
    assert isinstance(result, dict)
    assert "consistency" in result
    assert "hallucinated" in result
    print(f"  ✅ 一致性检查: score={result['consistency']:.2f}, hallucinated={result['hallucinated']}")

    return True


def test_inference_engine():
    """3. 推理引擎 → 验证 φ 编码 + 概念匹配 + 置信度计算"""
    bridge = TokenBridge()

    # 加载 EML
    phys_path = os.path.join(DATA_DIR, "physics_distilled.eml")
    if os.path.exists(phys_path):
        bridge.load_eml(phys_path)
        print(f"  ✅ 推理引擎已加载 EML")
    else:
        print("  ⚠️  无 EML 可用，推理引擎回退模式")

    engine = InferenceEngine(bridge=bridge)

    # 事实性查询
    result = engine.query("水的沸点是多少度？")
    assert "confidence" in result
    assert "matched_concepts" in result
    assert "subgraph" in result
    assert "input_text" in result
    confidence = result["confidence"]
    n_matched = len(result["matched_concepts"])
    n_verts = result["subgraph"]["size"] if isinstance(result["subgraph"], dict) else 0
    print(f"  ✅ 推理引擎: conf={confidence:.3f}, matched={n_matched}, subgraph_size={n_verts}")

    return True


def test_creative_engine():
    """4. 创造性引擎 → 构造函数和基本属性（不需 API key）"""
    engine = CreativeEngine(api_key=None)
    assert engine.model == "deepseek-chat"
    assert engine.temperature == 0.7
    assert engine.max_tokens == 1024
    print(f"  ✅ CreativeEngine: model={engine.model}, temp={engine.temperature}")

    # 有 API key 时测试实际生成
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        env_path = os.path.join(os.path.dirname(__file__), "..", "sim", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")

    if api_key:
        engine = CreativeEngine(api_key=api_key)
        result = engine.generate("什么是物理？", "")
        assert result and len(result) > 0
        print(f"  ✅ LLM 生成: {len(result)} 字符 — {result[:80]}...")
    else:
        print("  ⏭  无 API Key，跳过 LLM 调用")

    return True


def test_ownthink_db():
    """5. OwnThink 数据库连接验证"""
    db_path = "D:/tomas-data/tomas.db"
    if not os.path.exists(db_path):
        print(f"  ⏭  OwnThink DB 不存在 ({db_path})，跳过")
        return True

    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(rowid) FROM knowledge_triples")
    count = cursor.fetchone()[0] or 0
    cursor.execute(
        "SELECT subject, predicate, object FROM knowledge_triples LIMIT 3"
    )
    rows = cursor.fetchall()
    conn.close()

    assert count > 0, "knowledge_triples 表为空"
    print(f"  ✅ OwnThink DB: ~{count:,} 三元组 (rowid 估算)")
    for r in rows:
        print(f"    {r[0][:25]} → {r[1]} → {r[2][:35]}")
    return True


def main():
    print("=" * 60)
    print("  TOMAS-AGI V3 E2E 冒烟测试")
    print("=" * 60)
    print()

    tests = [
        ("EML 加载", test_eml_loading),
        ("φ-Gate", test_phi_gate),
        ("推理引擎", test_inference_engine),
        ("创造性引擎", test_creative_engine),
        ("OwnThink DB", test_ownthink_db),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        print(f"\n📋 {name}:")
        try:
            if test_fn():
                passed += 1
                print(f"  ✅ 通过")
        except Exception as e:
            print(f"  ❌ 失败: {type(e).__name__}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"  结果: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
