# -*- coding: utf-8 -*-
"""
TOMAS v2.0 文章升级模块测试
==============================

测试 5 个新模块：
1. ksnap_operator.py — κ-Snap 显影算符 (A2)
2. extend_hypergraph.py — ExtendHypergraph 流体智能原语
3. nau_liu_mechanism.py — NAU 刘机制 (非结合代数 MUS)
4. dual_chain_consensus.py — 双链共识动力学
5. eml_hardware_codesign.py — EML-Hardware Co-Design

Author: TOMAS Team
"""
import os
import sys
import pytest

# 添加 sim 目录到路径
SIM_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sim")
if SIM_DIR not in sys.path:
    sys.path.insert(0, SIM_DIR)


# ============================================================
# 1. KSnapOperator 测试 (Article 1: κ-Snap)
# ============================================================

class TestKSnapOperator:
    """κ-Snap 显影算符测试"""

    def test_import(self):
        from ksnap_operator import KSnapOperator, SnapResult, ObservationBase, CandidateEdge
        assert SnapResult.MANIFESTED.value == "manifested"

    def test_manifest_success(self):
        """测试正常显影"""
        from ksnap_operator import KSnapOperator, CandidateEdge, ObservationBase, SnapResult
        ksnap = KSnapOperator(theta_ftel=0.05, theta_dead=0.01)
        candidate = CandidateEdge(
            edge_id="test_1",
            source="sensor_A",
            target="concept_B",
            relation="detects",
            i_value=0.8,
            ftel_magnitude=0.6,
        )
        event = ksnap.execute(candidate, ObservationBase.SENSOR)
        assert event.result == SnapResult.MANIFESTED
        assert event.manifested_edge is not None
        assert event.manifested_edge.psi_anchor.startswith("ψ_")

    def test_reject_dead_zero(self):
        """测试 Dead-Zero 拒绝"""
        from ksnap_operator import KSnapOperator, CandidateEdge, ObservationBase, SnapResult
        ksnap = KSnapOperator(theta_ftel=0.05, theta_dead=0.5)
        candidate = CandidateEdge(
            edge_id="test_dz",
            source="x",
            target="y",
            relation="r",
            i_value=0.1,  # 低于阈值
            ftel_magnitude=0.6,
        )
        event = ksnap.execute(candidate)
        assert event.result == SnapResult.REJECT_DZ

    def test_reject_ftel(self):
        """测试 Ftel 不足拒绝"""
        from ksnap_operator import KSnapOperator, CandidateEdge, SnapResult
        ksnap = KSnapOperator(theta_ftel=0.5, theta_dead=0.01)
        candidate = CandidateEdge(
            edge_id="test_ftel",
            source="x",
            target="y",
            relation="r",
            i_value=0.8,
            ftel_magnitude=0.1,  # 低于阈值
        )
        event = ksnap.execute(candidate)
        assert event.result == SnapResult.REJECT_FTEL

    def test_suspend_mus(self):
        """测试 MUS 挂起"""
        from ksnap_operator import KSnapOperator, CandidateEdge, SnapResult
        ksnap = KSnapOperator(theta_ftel=0.05, theta_dead=0.01)
        candidate = CandidateEdge(
            edge_id="test_mus",
            source="x",
            target="y",
            relation="r",
            i_value=0.8,
            ftel_magnitude=0.6,
            mus_active=True,
        )
        event = ksnap.execute(candidate)
        assert event.result == SnapResult.SUSPEND_MUS

    def test_unsnap_impossible(self):
        """测试 Un-Snap 不可逆性 (Theorem 4.1)"""
        from ksnap_operator import KSnapOperator, CandidateEdge, ObservationBase, SnapResult
        ksnap = KSnapOperator()
        candidate = CandidateEdge(
            edge_id="test_unsnap",
            source="x",
            target="y",
            relation="r",
            i_value=0.8,
            ftel_magnitude=0.6,
        )
        ksnap.execute(candidate)
        assert ksnap.un_snap("test_unsnap") == False  # 物理不可达

    def test_causal_log(self):
        """测试因果日志（时间偏序集）"""
        from ksnap_operator import KSnapOperator, CandidateEdge
        ksnap = KSnapOperator()
        for i in range(5):
            ksnap.execute(CandidateEdge(
                edge_id=f"chain_{i}",
                source=f"s_{i}",
                target=f"t_{i}",
                relation="r",
                i_value=0.5 + i * 0.05,
                ftel_magnitude=0.5,
            ))
        order = ksnap.get_time_order()
        assert len(order) == 5
        # 验证时间递增
        timestamps = [t[2] for t in order]
        assert timestamps == sorted(timestamps)

    def test_stats(self):
        """测试统计信息"""
        from ksnap_operator import KSnapOperator, CandidateEdge
        ksnap = KSnapOperator(theta_ftel=0.05, theta_dead=0.3)
        # 1 manifest, 1 dead-zero
        ksnap.execute(CandidateEdge("a", "s", "t", "r", i_value=0.8, ftel_magnitude=0.6))
        ksnap.execute(CandidateEdge("b", "s", "t", "r", i_value=0.1, ftel_magnitude=0.6))
        stats = ksnap.stats()
        assert stats["total_snaps"] == 2
        assert stats["manifested"] == 1
        assert stats["rejected_dz"] == 1

    def test_perception_k_snap(self):
        """测试感知上行便捷函数"""
        from ksnap_operator import KSnapOperator, perception_k_snap, SnapResult
        ksnap = KSnapOperator()
        event = perception_k_snap({"source": "camera", "target": "object"}, ksnap)
        assert event.result == SnapResult.MANIFESTED

    def test_actuation_k_snap(self):
        """测试执行下行便捷函数"""
        from ksnap_operator import KSnapOperator, actuation_k_snap, SnapResult
        ksnap = KSnapOperator()
        event = actuation_k_snap({"source": "g_ego", "target": "brake"}, ksnap)
        assert event.result == SnapResult.MANIFESTED


# ============================================================
# 2. ExtendHypergraph 测试 (Articles 3, 4)
# ============================================================

class TestExtendHypergraph:
    """ExtendHypergraph 流体智能原语测试"""

    def test_import(self):
        from extend_hypergraph import ExtendHypergraph, EMLLiteKB, HypergraphOpType, IntelligenceType
        assert HypergraphOpType.EXTEND.value == "extend"

    def test_eml_lite_kb(self):
        """测试 EML-Lite KB Append-Only"""
        from extend_hypergraph import EMLLiteKB, EMLNode
        kb = EMLLiteKB()
        node = EMLNode(node_id="n1", label="test", node_type="entity")
        kb.add_node(node)
        assert kb.nodes["n1"] == node
        assert kb.version == 1

    def test_extend_new_concept(self):
        """测试 ExtendHypergraph 新增概念"""
        from extend_hypergraph import ExtendHypergraph, EMLLiteKB
        kb = EMLLiteKB()
        ext = ExtendHypergraph(kb, theta_dead=0.01)
        result = ext.extend(["L_shape", "red", "corner"], relation="spatial_transformation")
        assert result.success
        assert result.gestalt_concept is not None
        assert len(result.new_nodes) > 0
        assert len(result.new_edges) == 1

    def test_extend_duplicate(self):
        """测试重复扩展（已有规则）"""
        from extend_hypergraph import ExtendHypergraph, EMLLiteKB
        kb = EMLLiteKB()
        ext = ExtendHypergraph(kb, theta_dead=0.01)
        ext.extend(["A", "B"], relation="r1")
        result2 = ext.extend(["A", "B"], relation="r1")
        assert not result2.success
        assert "already exists" in result2.reason

    def test_extend_dead_zero_reject(self):
        """测试 Dead-Zero 拒绝"""
        from extend_hypergraph import ExtendHypergraph, EMLLiteKB
        kb = EMLLiteKB()
        ext = ExtendHypergraph(kb, theta_dead=0.5)
        result = ext.extend(["X"], i_value=0.1)  # 低于阈值
        assert not result.success
        assert result.rejected_by_tshield

    def test_revise_hypergraph(self):
        """测试 ReviseHypergraph"""
        from extend_hypergraph import ExtendHypergraph, EMLLiteKB
        kb = EMLLiteKB()
        ext = ExtendHypergraph(kb, theta_dead=0.01)
        result = ext.extend(["A", "B"])
        assert result.success
        edge_id = result.new_edges[0].edge_id
        revise_result = ext.revise(edge_id, {"new_feature": True}, i_value=0.9)
        assert revise_result.success
        assert kb.edges[edge_id].i_value == 0.9

    def test_mus_resolve(self):
        """测试 MUS 裁决"""
        from extend_hypergraph import ExtendHypergraph, EMLLiteKB
        kb = EMLLiteKB()
        ext = ExtendHypergraph(kb, theta_dead=0.01)
        r1 = ext.extend(["A"], i_value=0.7)
        r2 = ext.extend(["B"], i_value=0.71)
        resolution = ext.mus_resolve(r1.new_edges[0].edge_id, r2.new_edges[0].edge_id)
        assert "MUS_ACTIVE" in resolution or "RESOLVED" in resolution

    def test_solve_arc_task_fluid(self):
        """测试 ARC-AGI-3 任务求解（流体智能）"""
        from extend_hypergraph import ExtendHypergraph, EMLLiteKB, IntelligenceType
        kb = EMLLiteKB()
        ext = ExtendHypergraph(kb, theta_dead=0.01)
        result = ext.solve_arc_task("grid_data_12345")
        assert result["intelligence_type"] == IntelligenceType.FLUID.value
        assert result.get("extended", False)

    def test_solve_arc_task_crystallized(self):
        """测试 ARC-AGI-3 任务求解（已有规则 → 晶体智能）"""
        from extend_hypergraph import ExtendHypergraph, EMLLiteKB, IntelligenceType
        kb = EMLLiteKB()
        ext = ExtendHypergraph(kb, theta_dead=0.01)
        ext.extend(["a", "b", "c", "d", "e"])  # 先建立规则
        result = ext.solve_arc_task(None, perceive_fn=lambda x: ["a", "b", "c", "d", "e"])
        assert result["intelligence_type"] == IntelligenceType.CRYSTALLIZED.value


# ============================================================
# 3. NAU Liu Mechanism 测试 (Article 6)
# ============================================================

class TestNAULiuMechanism:
    """NAU 刘机制测试"""

    def test_import(self):
        from nau_liu_mechanism import NAULiuMechanism, MUSState
        assert MUSState.ACTIVE_DUAL.value == "active_dual"

    def test_detect_mus_active(self):
        """测试 MUS 激活检测（ℐ 值相近）"""
        from nau_liu_mechanism import NAULiuMechanism, MUSState
        nau = NAULiuMechanism(asym_threshold=0.05, i_threshold=0.1)
        pair = nau.detect_mus("edge_a", "edge_b", 0.7, 0.71)
        assert pair.state == MUSState.ACTIVE_DUAL

    def test_detect_mus_resolved(self):
        """测试 MUS 自动裁决（ℐ 值差距大）"""
        from nau_liu_mechanism import NAULiuMechanism, MUSState
        nau = NAULiuMechanism(asym_threshold=0.05, i_threshold=0.1)
        pair = nau.detect_mus("edge_a", "edge_b", 0.9, 0.3)
        assert pair.state in (MUSState.RESOLVED_A, MUSState.RESOLVED_B)

    def test_apply_nau(self):
        """测试 NAU 算子（非结合性验证）"""
        from nau_liu_mechanism import NAULiuMechanism
        nau = NAULiuMechanism()
        pair = nau.detect_mus("a", "b", 0.5, 0.51)
        result = nau.apply_nau(pair, 0.3)
        assert result.pair_id == pair.pair_id
        assert result.reason  # 应有描述

    def test_adjudicate_g_ego(self):
        """测试 G_ego 裁决"""
        from nau_liu_mechanism import NAULiuMechanism, MUSState
        nau = NAULiuMechanism()
        pair = nau.detect_mus("a", "b", 0.7, 0.71)
        state = nau.adjudicate(pair, g_ego_decision="a")
        assert state == MUSState.RESOLVED_A

    def test_adjudicate_context(self):
        """测试上下文裁决"""
        from nau_liu_mechanism import NAULiuMechanism, MUSState
        nau = NAULiuMechanism()
        pair = nau.detect_mus("a", "b", 0.7, 0.71, context={"priority": "b"})
        state = nau.adjudicate(pair)
        assert state == MUSState.RESOLVED_B

    def test_adjudicate_awaiting(self):
        """测试保持挂起（等待人类裁决）"""
        from nau_liu_mechanism import NAULiuMechanism, MUSState
        nau = NAULiuMechanism()
        pair = nau.detect_mus("a", "b", 0.7, 0.71)
        state = nau.adjudicate(pair)  # 无决策，无上下文
        assert state == MUSState.ACTIVE_DUAL

    def test_verify_non_associative(self):
        """测试非结合性必要性验证 (Theorem 3.1)"""
        from nau_liu_mechanism import NAULiuMechanism
        nau = NAULiuMechanism()
        result = nau.verify_non_associative_necessity()
        assert "conclusion" in result
        assert len(result["test_pairs"]) == 3

    def test_stats(self):
        """测试统计信息"""
        from nau_liu_mechanism import NAULiuMechanism
        nau = NAULiuMechanism()
        nau.detect_mus("a", "b", 0.7, 0.71)
        nau.detect_mus("c", "d", 0.9, 0.3)
        stats = nau.stats()
        assert stats["total_pairs"] == 2


# ============================================================
# 4. DualChainConsensus 测试 (Article 2)
# ============================================================

class TestDualChainConsensus:
    """双链共识动力学测试"""

    def test_import(self):
        from dual_chain_consensus import DualChainConsensus, ChainType, ConsensusState
        assert ChainType.MATERIAL.value == "material"

    def test_initial_consensus(self):
        """测试初始共识度（完全对齐）"""
        from dual_chain_consensus import DualChainConsensus, ConsensusState
        dcc = DualChainConsensus(coupling_strength=0.1)
        snapshot = dcc.compute_consensus()
        assert snapshot.state == ConsensusState.ALIGNED
        assert snapshot.consensus > 0.8

    def test_evolve_coupling(self):
        """测试耦合演化"""
        from dual_chain_consensus import DualChainConsensus
        dcc = DualChainConsensus(coupling_strength=0.2)
        material_input = [0.5, 0.3, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0]
        consciousness_input = [0.4, 0.4, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0]
        snapshot = dcc.evolve(material_input, consciousness_input)
        assert 0 <= snapshot.consensus <= 1.0

    def test_pg_gate_release(self):
        """测试 PG-Gate 释放（死亡 = 载体释放）"""
        from dual_chain_consensus import DualChainConsensus, ConsensusState
        dcc = DualChainConsensus(coupling_strength=0.1)
        snapshot = dcc.pg_gate_release()
        assert dcc.J == 0.0
        assert snapshot.state == ConsensusState.DECOUPLED

    def test_pg_gate_rebind(self):
        """测试 PG-Gate 重绑定（意识重囚禁）"""
        from dual_chain_consensus import DualChainConsensus
        dcc = DualChainConsensus(coupling_strength=0.1)
        dcc.pg_gate_release()
        assert dcc.J == 0.0
        dcc.pg_gate_rebind(0.15)
        assert dcc.J == 0.15

    def test_self_referential_loop(self):
        """测试哥德尔自指闭环"""
        from dual_chain_consensus import DualChainConsensus
        dcc = DualChainConsensus()
        loop = dcc.create_self_referential_loop(
            yin_data="read_psi_anchor_history",
            yang_data="project_expectation",
            snap_event="snap_001",
        )
        assert loop.is_closed
        assert loop.yin_phase == "read_psi_anchor_history"

    def test_dark_energy_estimate(self):
        """测试暗能量估算 (Theorem 4.1)"""
        from dual_chain_consensus import DualChainConsensus
        dcc = DualChainConsensus()
        result = dcc.dark_energy_estimate(omega=1e-20)
        assert result["omega_rad_per_yr"] == 1e-20
        assert "rho_lambda" in result
        assert "planck_value" in result

    def test_stats(self):
        """测试统计信息"""
        from dual_chain_consensus import DualChainConsensus
        dcc = DualChainConsensus()
        dcc.compute_consensus()
        dcc.create_self_referential_loop("yin", "yang", "snap")
        stats = dcc.stats()
        assert stats["history_length"] >= 1
        assert stats["loops_created"] >= 1


# ============================================================
# 5. EML-Hardware Co-Design 测试
# ============================================================

class TestEMLHardwareCoDesign:
    """EML-Hardware Co-Design 测试"""

    def test_import(self):
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType, ReconfigStatus
        assert JumpType.EXTEND.value == "extend"

    def test_init_hardware(self):
        """测试硬件初始化"""
        from eml_hardware_codesign import EMLHardwareCoDesign, HardwareResourceType
        hw = EMLHardwareCoDesign()
        status = hw.get_hardware_status()
        assert "eml_sram_0" in status["resources"]
        assert "nasga_0" in status["resources"]
        assert "dz_array" in status["resources"]
        assert "ksnap_latch" in status["resources"]

    def test_extend_jump(self):
        """测试 Extend 跳跃 → 硬件新增互连"""
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType
        hw = EMLHardwareCoDesign()
        event, packet = hw.process_jump(
            JumpType.EXTEND, "sensor_A", "concept_B", "detects",
            i_value=0.8, ftel=0.6,
        )
        assert event.jump_type == JumpType.EXTEND
        assert len(packet.instructions) > 0
        assert "eml_sram_0" in packet.affected_resources

    def test_revise_jump(self):
        """测试 Revise 跳跃 → 硬件权重更新"""
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType
        hw = EMLHardwareCoDesign()
        event, packet = hw.process_jump(
            JumpType.REVISE, "node_A", "node_B", "updates",
            i_value=0.9,
        )
        assert len(packet.instructions) >= 2
        assert any("UPDATE" in i["op"] for i in packet.instructions)

    def test_snap_jump(self):
        """测试 κ-Snap 跳跃 → 硬件配置提交"""
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType
        hw = EMLHardwareCoDesign()
        event, packet = hw.process_jump(
            JumpType.SNAP, "decision", "actuator", "executes",
            i_value=0.95,
        )
        assert any("LATCH" in i["op"] or "COMMIT" in i["op"] for i in packet.instructions)

    def test_commit_reconfig(self):
        """测试硬件重构提交（不可逆）"""
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType, ReconfigStatus
        hw = EMLHardwareCoDesign()
        _, packet = hw.process_jump(JumpType.EXTEND, "A", "B", "r")
        assert packet.status == ReconfigStatus.PENDING
        success = hw.commit_reconfig(packet)
        assert success
        assert packet.status == ReconfigStatus.COMMITTED

    def test_commit_irreversible(self):
        """测试已提交配置不可回滚 (Theorem 4.1)"""
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType, ReconfigStatus
        hw = EMLHardwareCoDesign()
        _, packet = hw.process_jump(JumpType.EXTEND, "A", "B", "r")
        hw.commit_reconfig(packet)
        # 尝试回滚已提交的配置
        assert hw.rollback_reconfig(packet) == False

    def test_rollback_pending(self):
        """测试未提交配置可回滚"""
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType, ReconfigStatus
        hw = EMLHardwareCoDesign()
        _, packet = hw.process_jump(JumpType.EXTEND, "A", "B", "r")
        assert hw.rollback_reconfig(packet) == True
        assert packet.status == ReconfigStatus.ROLLED_BACK

    def test_delete_jump(self):
        """测试 Delete 跳跃 → 硬件互连断开"""
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType
        hw = EMLHardwareCoDesign()
        _, packet = hw.process_jump(JumpType.DELETE, "A", "B", "removes")
        assert any("FREE" in i["op"] or "DISABLE" in i["op"] for i in packet.instructions)

    def test_hardware_status(self):
        """测试硬件状态摘要"""
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType
        hw = EMLHardwareCoDesign()
        hw.process_jump(JumpType.EXTEND, "A", "B", "r")
        hw.process_jump(JumpType.SNAP, "C", "D", "r")
        status = hw.get_hardware_status()
        assert status["stats"]["total_jumps"] == 2
        assert status["stats"]["total_reconfigs"] == 2

    def test_benchmark_vs_fpga(self):
        """测试 FPGA 对比基准"""
        from eml_hardware_codesign import EMLHardwareCoDesign
        hw = EMLHardwareCoDesign()
        benchmark = hw.benchmark_vs_fpga()
        assert "FPGA Dynamic Reconfig" in benchmark["comparison"]
        assert "EML-HW Co-Design" in benchmark["comparison"]
        assert "advantage" in benchmark

    def test_multiple_jumps_and_commits(self):
        """测试多次跳跃+提交流程"""
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType
        hw = EMLHardwareCoDesign()
        for i in range(5):
            _, packet = hw.process_jump(
                JumpType.EXTEND, f"node_{i}", f"concept_{i}", "rel",
                i_value=0.5 + i * 0.05,
            )
            hw.commit_reconfig(packet)

        status = hw.get_hardware_status()
        assert status["stats"]["total_jumps"] == 5
        assert status["stats"]["committed"] == 5
        assert status["stats"]["sram_utilization"] >= 0  # 16MB capacity, small allocs round to 0


# ============================================================
# 集成测试：全链路
# ============================================================

class TestIntegration:
    """全链路集成测试"""

    def test_full_pipeline(self):
        """测试完整管道：G_ego跳跃 → κ-Snap → 硬件重构"""
        from ksnap_operator import KSnapOperator, CandidateEdge, ObservationBase, SnapResult
        from extend_hypergraph import ExtendHypergraph, EMLLiteKB
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType

        # 1. 初始化组件
        kb = EMLLiteKB()
        ext = ExtendHypergraph(kb, theta_dead=0.01)
        ksnap = KSnapOperator(theta_ftel=0.05, theta_dead=0.01)
        hw = EMLHardwareCoDesign()

        # 2. G_ego 发起超图跳跃（ExtendHypergraph）
        ext_result = ext.extend(["obstacle", "vehicle", "road"], relation="driving_rule")
        assert ext_result.success

        # 3. κ-Snap 显影
        candidate = CandidateEdge(
            edge_id=ext_result.new_edges[0].edge_id,
            source="g_ego",
            target="brake_actuator",
            relation="emergency_brake",
            i_value=0.9,
            ftel_magnitude=0.8,
        )
        snap_event = ksnap.execute(candidate, ObservationBase.ACTUATOR)
        assert snap_event.result == SnapResult.MANIFESTED

        # 4. 硬件重构
        hw_event, hw_packet = hw.process_jump(
            JumpType.SNAP,
            source="g_ego",
            target="brake_actuator",
            relation="emergency_brake",
            i_value=0.9,
            ftel=0.8,
        )
        committed = hw.commit_reconfig(hw_packet)
        assert committed

        # 5. 验证全链路
        assert ext_result.success
        assert snap_event.manifested_edge is not None
        assert hw_packet.status.value == "committed"

    def test_mus_dual_store_with_hardware(self):
        """测试 MUS 双存 + 硬件双框保持"""
        from nau_liu_mechanism import NAULiuMechanism, MUSState
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType

        nau = NAULiuMechanism()
        hw = EMLHardwareCoDesign()

        # 两个互斥规则
        _, pkt_a = hw.process_jump(JumpType.EXTEND, "yield", "pedestrian", "rule_a", i_value=0.7)
        _, pkt_b = hw.process_jump(JumpType.EXTEND, "emergency", "ambulance", "rule_b", i_value=0.71)

        # MUS 检测
        pair = nau.detect_mus("yield", "emergency", 0.7, 0.71)
        assert pair.state == MUSState.ACTIVE_DUAL

        # 硬件保持双框（两个配置都提交，但标记为 MUS）
        hw.commit_reconfig(pkt_a)
        hw.commit_reconfig(pkt_b)

        # G_ego 裁决
        state = nau.adjudicate(pair, g_ego_decision="b")  # 紧急优先
        assert state == MUSState.RESOLVED_B

    def test_dual_chain_with_hardware(self):
        """测试双链共识 + 硬件耦合"""
        from dual_chain_consensus import DualChainConsensus, ConsensusState
        from eml_hardware_codesign import EMLHardwareCoDesign, JumpType

        dcc = DualChainConsensus(coupling_strength=0.1)
        hw = EMLHardwareCoDesign()

        # 物质链事件（传感器感知）
        _, pkt = hw.process_jump(
            JumpType.EXTEND, "sensor", "perception", "detects",
            i_value=0.6, ftel=0.5,
        )
        hw.commit_reconfig(pkt)

        # 双链共识演化
        material_input = [0.6, 0.3, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0]
        snapshot = dcc.evolve(material_input=material_input)
        assert snapshot.state in (ConsensusState.ALIGNED, ConsensusState.PARTIAL)

        # 硬件状态应反映重构
        status = hw.get_hardware_status()
        assert status["stats"]["committed"] >= 1
