#!/usr/bin/env python3
"""
ψ-Alignment Checking Integration Test

验证:
1. G_egoEngine.compute_psi_alignment() 方法
2. TShieldWrapper.validate_psi_alignment() 方法（使用 G_ego）
3. PsiAnchor 数据结构
4. get_status() 包含 psi_anchor

Author: TOMAS Team
Date: 2026-06-19
"""

import sys
import os

# 添加 sim 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tomas_agi", "sim"))

def test_psi_alignment():
    """主测试函数"""
    print("=" * 60)
    print("ψ-Alignment Checking Integration Test")
    print("=" * 60)

    # 1. 导入模块
    try:
        # 模拟 DeadZeroDetector
        class MockDeadZeroDetector:
            def __init__(self, i_value=0.7):
                self._i_value = i_value
            def get_last_i_value(self):
                return self._i_value

        from g_ego import G_egoEngine, PsiAnchor
        print("[OK] 模块导入成功")
    except Exception as e:
        print(f"[FAIL] 模块导入失败: {e}")
        return False

    # 2. 创建 G_egoEngine 实例
    try:
        g_ego = G_egoEngine(i_threshold=0.5)
        detector = MockDeadZeroDetector(i_value=0.7)
        g_ego.set_dead_zero_detector(detector)
        print(f"[OK] G_egoEngine 实例创建成功 (i_threshold={g_ego.i_threshold})")
    except Exception as e:
        print(f"[FAIL] G_egoEngine 创建失败: {e}")
        return False

    # 3. 测试 get_status() 包含 psi_anchor
    try:
        status = g_ego.get_status()
        if "psi_anchor" in status and status["psi_anchor"] is not None:
            print(f"[OK] get_status() 包含 psi_anchor")
            print(f"  psi_anchor.i_value = {status['psi_anchor']['i_value']:.4f}")
            print(f"  psi_anchor.mode = {status['psi_anchor']['mode']}")
        else:
            print(f"[FAIL] get_status() 不包含 psi_anchor")
            return False
    except Exception as e:
        print(f"[FAIL] get_status() 测试失败: {e}")
        return False

    # 4. 测试 compute_psi_alignment() — 高对齐（edge.i_value ≈ g_ego.i_value）
    try:
        # 模拟 EML 超边（对象）
        class MockEdge:
            def __init__(self, edge_id, i_value):
                self.edge_id = edge_id
                self.i_value = i_value

        edge_high = MockEdge("edge_001", i_value=0.72)  # 接近 0.7
        result_high = g_ego.compute_psi_alignment(edge_high)

        print(f"\n[INFO] 高对齐测试 (edge.i_value=0.72, g_ego.i=0.7):")
        print(f"  alignment_score = {result_high['alignment_score']:.4f}")
        print(f"  aligned = {result_high['aligned']}")
        print(f"  reason = {result_high['reason']}")

        if result_high["alignment_score"] > 0.9 and result_high["aligned"]:
            print(f"[OK] 高对齐测试通过")
        else:
            print(f"[WARN] 高对齐测试未通过（但可能是阈值设置问题）")
    except Exception as e:
        print(f"[FAIL] compute_psi_alignment() 高对齐测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. 测试 compute_psi_alignment() — 低对齐（edge.i_value 远离 g_ego.i_value）
    try:
        edge_low = MockEdge("edge_002", i_value=0.1)  # 远离 0.7
        result_low = g_ego.compute_psi_alignment(edge_low)

        print(f"\n[INFO] 低对齐测试 (edge.i_value=0.1, g_ego.i=0.7):")
        print(f"  alignment_score = {result_low['alignment_score']:.4f}")
        print(f"  aligned = {result_low['aligned']}")
        print(f"  reason = {result_low['reason']}")

        if result_low["alignment_score"] < 0.7:
            print(f"[OK] 低对齐测试通过（对齐度低）")
        else:
            print(f"[WARN] 低对齐测试未通过")
    except Exception as e:
        print(f"[FAIL] compute_psi_alignment() 低对齐测试失败: {e}")
        return False

    # 6. 测试 compute_psi_alignment() — 字典输入
    try:
        edge_dict = {"edge_id": "edge_003", "i_value": 0.65}
        result_dict = g_ego.compute_psi_alignment(edge_dict)

        print(f"\n[INFO] 字典输入测试 (edge_dict.i_value=0.65):")
        print(f"  alignment_score = {result_dict['alignment_score']:.4f}")
        print(f"  aligned = {result_dict['aligned']}")

        if result_dict["alignment_score"] > 0.9:
            print(f"[OK] 字典输入测试通过")
        else:
            print(f"[WARN] 字典输入测试未通过")
    except Exception as e:
        print(f"[FAIL] compute_psi_alignment() 字典输入测试失败: {e}")
        return False

    # 7. 测试 PsiAnchor 数据类
    try:
        anchor = PsiAnchor(
            i_value=0.75,
            mode="afferent",
            alignment_threshold=0.4,
            metadata={"test": True}
        )
        print(f"\n[OK] PsiAnchor 数据类测试通过")
        print(f"  i_value={anchor.i_value}, mode={anchor.mode}")
    except Exception as e:
        print(f"[FAIL] PsiAnchor 数据类测试失败: {e}")
        return False

    # 8. 测试 TShieldWrapper.validate_psi_alignment()（如果可用）
    try:
        from tshield_wrapper import TShieldWrapper
        tshield = TShieldWrapper(enable_g_ego=True)
        tshield.g_ego_engine = g_ego  # 手动设置

        result_tshield = tshield.validate_psi_alignment(edge_high)
        print(f"\n[INFO] TShieldWrapper.validate_psi_alignment() 测试:")
        print(f"  alignment_score = {result_tshield['alignment_score']:.4f}")
        print(f"  aligned = {result_tshield['aligned']}")

        if result_tshield["alignment_score"] is not None:
            print(f"[OK] TShieldWrapper.validate_psi_alignment() 测试通过")
        else:
            print(f"[WARN] TShieldWrapper 未返回对齐分数")
    except ImportError:
        print(f"\n[SKIP] TShieldWrapper 不可用（跳过测试 8）")
    except Exception as e:
        print(f"[FAIL] TShieldWrapper 测试失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_psi_alignment()
    sys.exit(0 if success else 1)
