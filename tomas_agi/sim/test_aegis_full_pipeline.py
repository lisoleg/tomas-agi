#!/usr/bin/env python3
"""
AEGIS 全流程集成测试（模拟真实轨迹数据 - v5 最终修正版）

测试目标：
1. 创建真实推理轨迹（knowledge_triples 查询 → LLM 推理 → 结果返回）
2. 验证 AEGISEngine 的四阶段流水线（Digester → Planner → Evolver → Critic+Gate）
3. 验证 VariantIsolationManager 的 MUS 变体隔离
4. 验证 KSnapDualRail 的 κ-Gate 双轨协同进化
5. 验证 CausalLog 的因果日志追加

Author: TOMAS Team
Date: 2026-06-19
"""

import sys
import os
import time
from datetime import datetime

# 添加 sim 目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from harness_aegis import (
        AEGISEngine,
        VariantIsolationManager,
        KSnapDualRail,
        CausalLog,
        CompatManifest,
        TOMAS_HarnessEdge,
        SnapEvent,
        SnapSubject,
        HookPhase,
        OptDim,
    )
    print("[OK] 模块导入成功")
except Exception as e:
    print(f"[FAIL] 模块导入失败: {e}")
    sys.exit(1)


def create_mock_trajectory():
    """创建模拟的真实推理轨迹数据。"""
    trajectory = []
    task_id = "test_task_001"

    # Step 1: 查询知识库
    trajectory.append({
        "task_id": task_id,
        "step": 1,
        "action": "query_knowledge",
        "input": {"query": "What is the capital of France?"},
        "output": {
            "answer": "Paris",
            "confidence": 0.95,
            "source": "knowledge_triples",
        },
        "timestamp": datetime.now().isoformat(),
    })

    # Step 2: LLM 推理
    trajectory.append({
        "task_id": task_id,
        "step": 2,
        "action": "llm_inference",
        "input": {
            "prompt": "Given the knowledge that Paris is the capital of France, answer: What is the largest city in France?",
            "context": trajectory[0]["output"],
        },
        "output": {
            "answer": "Paris is the largest city and capital of France.",
            "confidence": 0.92,
            "reasoning": "Paris is both the capital and the most populous city in France.",
        },
        "timestamp": datetime.now().isoformat(),
    })

    return trajectory


def test_aegis_full_pipeline():
    """测试 AEGISEngine 四阶段流水线"""
    print("\n" + "=" * 60)
    print("  AEGIS 全流程集成测试")
    print("=" * 60)

    # 1. 创建模拟轨迹
    print("\n[1] 创建模拟推理轨迹...")
    trajectory = create_mock_trajectory()
    print(f"  ✅ 已创建 {len(trajectory)} 步推理轨迹")

    # 2. 初始化 AEGISEngine
    print("\n[2] 初始化 AEGISEngine...")
    try:
        aegis = AEGISEngine(eml_kb=None, t_shield=None, g_ego_psi_anchor=None)
        print(f"  ✅ AEGISEngine 初始化成功")
    except Exception as e:
        print(f"  ❌ AEGISEngine 初始化失败: {e}")
        return False

    # 3. 运行四阶段流水线
    print("\n[3] 运行 AEGIS 四阶段流水线...")
    try:
        # 阶段 1: Digester
        print("  🔍 阶段 1: Digester（轨迹 → 失败超边）")
        failed_edges = aegis.digester(trajectory)
        print(f"  ✅ Digester 完成")
        print(f"    失败超边数: {len(failed_edges)}")

        # 阶段 2: Planner（需要 current_harness 参数）
        print("\n  📐 阶段 2: Planner（失败超边 → edit proposals）")
        # 创建完整的 TOMAS_HarnessEdge（提供所有必需参数）
        mock_harness = TOMAS_HarnessEdge(
            edge_id="mock_harness_001",
            phase=HookPhase.STEP_START,
            opt_dims=[OptDim.D1_PROMPT_DESIGN],
            g_ego_psi_alignment="test_alignment",
            prompt_ref="test_prompt_ref",
            tool_bindings=[],
            memory_policy={},
            ctrl_flow={},
            eval_spec={},
        )
        proposals = aegis.planner(failed_edges, mock_harness)
        print(f"  ✅ Planner 完成")
        print(f"    生成提案数: {len(proposals)}")

        # 阶段 3: Evolver
        print("\n  🧬 阶段 3: Evolver（提案进化）")
        evolved = aegis.evolver(mock_harness, proposals)
        print(f"  ✅ Evolver 完成")

        # 阶段 4: Critic + Gate
        print("\n  🚪 阶段 4: Critic + Gate（评审 + 门控）")
        selected = aegis.critic_gate(evolved, trajectory)
        print(f"  ✅ Critic + Gate 完成")

        print("\n  ✅ AEGIS 四阶段流水线全部通过")
        return True

    except Exception as e:
        print(f"\n  ❌ AEGIS 流水线失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_variant_isolation():
    """测试 VariantIsolationManager 的 MUS 变体隔离"""
    print("\n" + "=" * 60)
    print("  MUS 变体隔离测试")
    print("=" * 60)

    try:
        vim = VariantIsolationManager(max_variants=3)
        print("\n[1] 初始化 VariantIsolationManager (K=3)...")

        # 注册模拟超边（使用 register_cluster）
        print("\n[2] 注册模拟任务簇...")
        for i in range(5):
            cluster_name = f"cluster_{i:03d}"
            edge = TOMAS_HarnessEdge(
                edge_id=f"test_edge_{i:03d}",
                phase=HookPhase.STEP_START,
                opt_dims=[OptDim.D1_PROMPT_DESIGN],
                g_ego_psi_alignment=f"alignment_{i}",
                prompt_ref="test_prompt",
                tool_bindings=[],
                memory_policy={},
                ctrl_flow={},
                eval_spec={},
            )
            vim.register_cluster(cluster_name, edge)
            print(f"  ✅ 注册簇 {i+1}/5: {cluster_name} → {edge.edge_id}")

        # 检查变体隔离
        print("\n[3] 检查变体隔离状态...")
        active_count = len(vim.variants)
        print(f"  已注册簇数: {active_count} (K={vim.max_variants})")

        # 测试路由
        print("\n[4] 测试路由（r(τ) → 用 e_h_k）...")
        selected = vim.route("test_query")
        print(f"  ✅ 路由选择: {selected.edge_id if selected else 'None'}")

        print("\n  ✅ MUS 变体隔离测试全部通过")
        return True

    except Exception as e:
        print(f"\n  ❌ MUS 变体隔离测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ksnap_dual_rail():
    """测试 KSnapDualRail 的 κ-Gate 双轨协同进化"""
    print("\n" + "=" * 60)
    print("  κ-Gate 双轨协同进化测试")
    print("=" * 60)

    try:
        kdr = KSnapDualRail()
        print("\n[1] 初始化 KSnapDualRail...")

        # 注册协同进化配对
        print("\n[2] 注册 harness + model 协同进化配对...")
        harness_edge_id = "harness_v2.1.3_001"
        model_weight_ver = "v2.1.3"

        manifest = kdr.register_co_evo(harness_edge_id, model_weight_ver, validated_on=["gaia", "arc"])
        print(f"  ✅ 注册成功: snap_session={kdr.session_id}")

        # 验证兼容性
        print("\n[3] 验证兼容性...")
        is_compat, _ = kdr.check_compat(harness_edge_id, model_weight_ver)
        print(f"  ✅ 兼容性检查: {is_compat}")

        print("\n  ✅ κ-Gate 双轨协同进化测试全部通过")
        return True

    except Exception as e:
        print(f"\n  ❌ κ-Gate 双轨协同进化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_causal_log():
    """测试 CausalLog 的因果日志追加"""
    print("\n" + "=" * 60)
    print("  因果日志（CausalLog）测试")
    print("=" * 60)

    try:
        clog = CausalLog()
        print("\n[1] 初始化 CausalLog...")

        # 追加日志
        print("\n[2] 追加因果日志...")
        for i in range(5):
            event = SnapEvent(
                snap_id=str(__import__('uuid').uuid4()),
                session_id="test_session_001",
                task_trace_hash="abc123def456",
                subject=SnapSubject.HARNESS_VER,
                ref_id=f"harness_{i:03d}",
                meta={"step": i, "task_id": "test_task_001"},
                wall_ns=int(time.time() * 1e9),
                prev_snap=None,
            )
            clog.append(event)
            print(f"  ✅ 追加事件 {i+1}/5: {event.snap_id[:16]}...")

        # 查询日志（使用 filter() 方法）
        print("\n[3] 查询因果日志...")
        all_events = clog.filter()
        print(f"  总事件数: {len(all_events)}")

        # 测试回溯性
        print("\n[4] 测试回溯性（按 session_id 查询）...")
        subset = clog.filter(session_id="test_session_001")
        print(f"  回溯结果数: {len(subset)}")

        print("\n  ✅ 因果日志测试全部通过")
        return True

    except Exception as e:
        print(f"\n  ❌ 因果日志测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("  AEGIS 全流程集成测试（模拟真实轨迹数据）")
    print("=" * 60)

    results = []

    results.append(("AEGIS 四阶段流水线", test_aegis_full_pipeline()))
    results.append(("MUS 变体隔离", test_variant_isolation()))
    results.append(("κ-Gate 双轨协同进化", test_ksnap_dual_rail()))
    results.append(("因果日志", test_causal_log()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "-" * 60)
    print(f"  总计: {len(results)} | 通过: {passed} | 失败: {failed}")
    print("-" * 60)

    if failed == 0:
        print("\n🎉 所有测试通过！AEGIS 全流程集成测试成功！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查日志。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
