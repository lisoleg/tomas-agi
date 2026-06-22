"""
FDE Builder / Dual Timeline / IT-OT Bridge 测试套件
=====================================================
"""

import pytest
import math
import time
from unittest.mock import MagicMock

# ═══════════════════════════════════════════════════════════════
# FDE Builder 测试
# ═══════════════════════════════════════════════════════════════

from sim.fde_builder import (
    FDEOntologyBuilder, FDENode, FDENodeType, GroundingStatus,
    IndustrialStandard, EchoContext, FDEValidationResult,
)


class TestFDENode:
    def test_create_node(self):
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI, iota_value=0.8)
        assert node.id == "n1"
        assert node.iota_value == 0.8

    def test_dead_zero_check(self):
        low = FDENode(id="l", name="low", node_type=FDENodeType.QI, iota_value=0.1)
        assert low.is_dead_zero(0.15)
        high = FDENode(id="h", name="high", node_type=FDENodeType.QI, iota_value=0.8)
        assert not high.is_dead_zero(0.15)

    def test_mus_check(self):
        sym = FDENode(id="s", name="sym", node_type=FDENodeType.SHU, nasga_asym=0.01)
        assert not sym.is_mus(0.05)
        asym = FDENode(id="a", name="asym", node_type=FDENodeType.SHU, nasga_asym=0.08)
        assert asym.is_mus(0.05)

    def test_to_dict(self):
        node = FDENode(id="n1", name="test", node_type=FDENodeType.DAO, iota_value=0.7)
        d = node.to_dict()
        assert d["node_type"] == "道"
        assert d["iota_value"] == 0.7


class TestFDEOntologyBuilder:
    def test_add_and_get_node(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI, iota_value=0.5)
        builder.add_node(node)
        assert builder.get_node("n1") is not None
        assert builder.get_node("n1").name == "test"

    def test_parent_child_relationship(self):
        builder = FDEOntologyBuilder()
        parent = FDENode(id="p1", name="parent", node_type=FDENodeType.DAO, iota_value=0.9)
        child = FDENode(id="c1", name="child", node_type=FDENodeType.QI, iota_value=0.5, parent_id="p1")
        builder.add_node(parent)
        builder.add_node(child)
        assert "c1" in builder.get_node("p1").children_ids

    def test_calibrate_iota_zero_evidence(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI)
        builder.add_node(node)
        iota = builder.calibrate_iota("n1", [])
        assert iota == 0.0
        assert builder.get_node("n1").grounding == GroundingStatus.DEAD_ZERO

    def test_calibrate_iota_with_evidence(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI)
        builder.add_node(node)
        evidence = [{"weight": 0.8}, {"weight": 0.7}]
        iota = builder.calibrate_iota("n1", evidence)
        assert iota > 0.0
        assert builder.get_node("n1").grounding == GroundingStatus.GROUNDED

    def test_validate_qi_no_eml(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI, iota_value=0.8)
        builder.add_node(node)
        passed, reason = builder.validate_qi(node)
        assert not passed
        assert "no_eml" in reason

    def test_validate_qi_ok(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI,
                       iota_value=0.8, eml_vertex_ids=["v1"])
        builder.add_node(node)
        passed, reason = builder.validate_qi(node)
        assert passed

    def test_validate_qi_dead_zero(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI,
                       iota_value=0.1, eml_vertex_ids=["v1"])
        builder.add_node(node)
        passed, reason = builder.validate_qi(node)
        assert not passed
        assert "dead_zero" in reason

    def test_validate_shu_zero_asym(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.SHU, nasga_asym=0.0)
        builder.add_node(node)
        passed, reason = builder.validate_shu(node)
        assert not passed

    def test_validate_shu_ok(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.SHU, nasga_asym=0.1)
        builder.add_node(node)
        passed, reason = builder.validate_shu(node)
        assert passed

    def test_validate_shu_mus(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.SHU, nasga_asym=0.08)
        builder.add_node(node)
        passed, reason = builder.validate_shu(node)
        assert passed  # MUS 不阻断
        assert "mus" in reason

    def test_validate_fa_no_alignment(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.FA,
                       gh_distance=float('inf'))
        builder.add_node(node)
        passed, reason = builder.validate_fa(node)
        assert not passed

    def test_validate_fa_ok(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.FA, gh_distance=0.2)
        builder.add_node(node)
        passed, reason = builder.validate_fa(node)
        assert passed

    def test_validate_dao_no_anchor(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.DAO,
                       self_anchor_deviation=float('inf'))
        builder.add_node(node)
        passed, reason = builder.validate_dao(node)
        assert not passed

    def test_validate_dao_ok(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.DAO,
                       self_anchor_deviation=0.1)
        builder.add_node(node)
        passed, reason = builder.validate_dao(node)
        assert passed

    def test_full_validation_grounded(self):
        builder = FDEOntologyBuilder()
        node = FDENode(
            id="n1", name="complete", node_type=FDENodeType.QI,
            iota_value=0.8, eml_vertex_ids=["v1"],
            nasga_asym=0.1, gh_distance=0.2, self_anchor_deviation=0.1,
        )
        builder.add_node(node)
        result = builder.validate_full("n1")
        assert result.all_pass
        assert result.overall == GroundingStatus.GROUNDED

    def test_full_validation_dead_zero(self):
        builder = FDEOntologyBuilder()
        node = FDENode(
            id="n1", name="bad_dao", node_type=FDENodeType.QI,
            iota_value=0.8, eml_vertex_ids=["v1"],
            nasga_asym=0.1, gh_distance=0.2,
            self_anchor_deviation=0.5,  # 道层失败
        )
        builder.add_node(node)
        result = builder.validate_full("n1")
        assert not result.dao_pass
        assert result.overall == GroundingStatus.DEAD_ZERO

    def test_full_validation_not_found(self):
        builder = FDEOntologyBuilder()
        result = builder.validate_full("nonexistent")
        assert result.overall == GroundingStatus.UNGROUNDED

    def test_build_from_eml(self):
        builder = FDEOntologyBuilder()
        vertices = [
            {"id": "v1", "name": "sensor_A", "i_value": 0.8, "asym": 0.05},
            {"id": "v2", "name": "sensor_B", "i_value": 0.1, "asym": 0.0},
        ]
        ids = builder.build_from_eml(vertices, domain="scada")
        assert len(ids) == 2
        n1 = builder.get_node("v1")
        assert n1.iota_value == 0.8
        assert n1.grounding == GroundingStatus.GROUNDED
        n2 = builder.get_node("v2")
        assert n2.iota_value == 0.1
        assert n2.grounding == GroundingStatus.DEAD_ZERO

    def test_echo_context(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI, iota_value=0.8)
        builder.add_node(node)
        ctx = EchoContext(it_context="API call", ot_context="PLC read",
                         translation_confidence=0.85)
        builder.set_echo_context("n1", ctx)
        result = builder.check_cross_domain_alignment("n1")
        assert result["aligned"]

    def test_echo_context_misaligned(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI, iota_value=0.8)
        builder.add_node(node)
        ctx = EchoContext(it_context="deploy", ot_context="stop",
                         translation_confidence=0.3,
                         cross_domain_conflicts=["intent_mismatch"])
        builder.set_echo_context("n1", ctx)
        result = builder.check_cross_domain_alignment("n1")
        assert not result["aligned"]

    def test_assign_industry_standard(self):
        builder = FDEOntologyBuilder()
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI, iota_value=0.8)
        builder.add_node(node)
        std = builder.assign_industry_standard("n1", "scada")
        assert std == IndustrialStandard.IEC_62443
        assert builder.get_node("n1").industrial_standard == IndustrialStandard.IEC_62443

    def test_stats(self):
        builder = FDEOntologyBuilder()
        builder.add_node(FDENode(id="n1", name="a", node_type=FDENodeType.QI, iota_value=0.8))
        builder.add_node(FDENode(id="n2", name="b", node_type=FDENodeType.DAO, iota_value=0.1))
        stats = builder.stats
        assert stats["total"] == 2
        assert stats["dead_zero_count"] == 1


# ═══════════════════════════════════════════════════════════════
# Dual Timeline 测试
# ═══════════════════════════════════════════════════════════════

from sim.dual_timeline import (
    DualTimelineEngine, ExternalTimeline, InternalTimeline,
    CognitiveFirewall, DualTimelineAligner,
    CausalEvent, CognitiveEvent, CausalEventType, CognitiveEventType,
    TimeDomain, FirewallVerdict, SingularityReport,
)


class TestExternalTimeline:
    def test_add_and_get(self):
        tl = ExternalTimeline()
        event = CausalEvent(id="e1", event_type=CausalEventType.OBSERVATION, causal_iota=0.8)
        tl.add_event(event)
        assert tl.get_event("e1") is not None
        assert tl.count == 1

    def test_latest(self):
        tl = ExternalTimeline()
        tl.add_event(CausalEvent(id="e1", event_type=CausalEventType.OBSERVATION, timestamp=1.0))
        tl.add_event(CausalEvent(id="e2", event_type=CausalEventType.ACTION, timestamp=2.0))
        assert tl.latest.id == "e2"

    def test_empty_latest(self):
        tl = ExternalTimeline()
        assert tl.latest is None


class TestInternalTimeline:
    def test_add_and_get(self):
        tl = InternalTimeline()
        event = CognitiveEvent(id="c1", event_type=CognitiveEventType.HYPOTHESIS,
                               content="test", cognitive_iota=0.7)
        tl.add_event(event)
        assert tl.get_event("c1") is not None
        assert tl.count == 1

    def test_branches(self):
        tl = InternalTimeline()
        root = CognitiveEvent(id="c1", event_type=CognitiveEventType.HYPOTHESIS, content="root")
        branch = CognitiveEvent(id="c2", event_type=CognitiveEventType.INFERENCE,
                                content="branch", predecessor_ids=["c1"])
        tl.add_event(root)
        tl.add_event(branch)
        branches = tl.get_branches("c1")
        assert len(branches) == 1
        assert branches[0].id == "c2"

    def test_lineage(self):
        tl = InternalTimeline()
        c1 = CognitiveEvent(id="c1", event_type=CognitiveEventType.HYPOTHESIS, content="root")
        c2 = CognitiveEvent(id="c2", event_type=CognitiveEventType.INFERENCE,
                            content="child", predecessor_ids=["c1"])
        tl.add_event(c1)
        tl.add_event(c2)
        lineage = tl.get_lineage("c2")
        assert len(lineage) == 2


class TestCognitiveFirewall:
    def test_allow(self):
        fw = CognitiveFirewall()
        event = CognitiveEvent(id="c1", event_type=CognitiveEventType.HYPOTHESIS,
                               content="safe", cognitive_iota=0.8, recursion_depth=1)
        assert fw.evaluate(event) == FirewallVerdict.ALLOW

    def test_dead_zero(self):
        fw = CognitiveFirewall()
        event = CognitiveEvent(id="c1", event_type=CognitiveEventType.HYPOTHESIS,
                               content="low iota", cognitive_iota=0.05, recursion_depth=0)
        assert fw.evaluate(event) == FirewallVerdict.DEAD_ZERO

    def test_block_recursion(self):
        fw = CognitiveFirewall(max_recursion=5)
        event = CognitiveEvent(id="c1", event_type=CognitiveEventType.REFLECTION,
                               content="deep", cognitive_iota=0.8, recursion_depth=5)
        assert fw.evaluate(event) == FirewallVerdict.BLOCK

    def test_throttle(self):
        fw = CognitiveFirewall(warn_recursion=3, max_recursion=8)
        event = CognitiveEvent(id="c1", event_type=CognitiveEventType.REFLECTION,
                               content="moderate", cognitive_iota=0.7, recursion_depth=4)
        assert fw.evaluate(event) == FirewallVerdict.THROTTLE

    def test_self_referential(self):
        fw = CognitiveFirewall()
        event = CognitiveEvent(id="evil_ref", event_type=CognitiveEventType.REFLECTION,
                               content="evil_ref references itself", cognitive_iota=0.8,
                               recursion_depth=1)
        assert fw.evaluate(event) == FirewallVerdict.BLOCK

    def test_planck_threshold(self):
        fw = CognitiveFirewall(theta_dead=0.15, planck_threshold=0.01)
        event = CognitiveEvent(id="c1", event_type=CognitiveEventType.HYPOTHESIS,
                               content="tiny", cognitive_iota=0.005, recursion_depth=0)
        assert fw.evaluate(event) == FirewallVerdict.DEAD_ZERO

    def test_block_log(self):
        fw = CognitiveFirewall()
        event = CognitiveEvent(id="c1", event_type=CognitiveEventType.HYPOTHESIS,
                               content="low", cognitive_iota=0.05, recursion_depth=0)
        fw.evaluate(event)
        assert fw.block_count == 1


class TestDualTimelineEngine:
    def test_observe(self):
        engine = DualTimelineEngine()
        event = engine.observe("obs1", {"data": "temperature"}, iota=0.8)
        assert event.id == "obs1"
        assert engine.external.count == 1

    def test_think_allow(self):
        engine = DualTimelineEngine()
        verdict, sing = engine.think("hyp1", "water boils at 100C", iota=0.9, recursion=0)
        assert verdict == FirewallVerdict.ALLOW
        assert sing is None
        assert engine.internal.count == 1

    def test_think_dead_zero(self):
        engine = DualTimelineEngine()
        verdict, sing = engine.think("hyp2", "speculation", iota=0.05, recursion=0)
        assert verdict == FirewallVerdict.DEAD_ZERO
        assert sing is not None
        assert sing.resolved

    def test_think_blocked_recursion(self):
        engine = DualTimelineEngine(max_recursion=3)
        verdict, sing = engine.think("hyp3", "deep thought", iota=0.8, recursion=3)
        assert verdict == FirewallVerdict.BLOCK
        assert sing is not None

    def test_act(self):
        engine = DualTimelineEngine()
        act = engine.act("act1", {"action": "open_valve"}, predecessor=None, iota=0.7)
        assert act.id == "act1"

    def test_stats(self):
        engine = DualTimelineEngine()
        engine.observe("o1", iota=0.8)
        engine.think("h1", "test", iota=0.7)
        stats = engine.stats
        assert stats["external_events"] == 1
        assert stats["internal_events"] == 1

    def test_alignment_stats(self):
        engine = DualTimelineEngine()
        engine.think("h1", "test", iota=0.05)  # dead zero
        stats = engine.aligner.alignment_stats
        assert stats["singularities"] == 1


# ═══════════════════════════════════════════════════════════════
# IT-OT Bridge 测试
# ═══════════════════════════════════════════════════════════════

from sim.itot_bridge import (
    ITOTBridge, ITOTTranslator, TechnicalDebtGovernor, ZeroTrustGate,
    TechDomain, DebtType, DebtSeverity, TrustLevel,
    TranslationEntry, TechDebt, JointKPI,
)


class TestITOTTranslator:
    def test_it_to_ot(self):
        t = ITOTTranslator()
        assert t.translate_it_to_ot("latency") == "response_time"

    def test_ot_to_it(self):
        t = ITOTTranslator()
        assert t.translate_ot_to_it("response_time") == "latency"

    def test_unknown_term(self):
        t = ITOTTranslator()
        assert t.translate_it_to_ot("quantum_state") is None

    def test_add_custom(self):
        t = ITOTTranslator()
        entry = TranslationEntry(id="c1", it_term="model_server", ot_term=" historian_node",
                                translation_iota=0.8)
        t.add_translation(entry)
        assert t.translate_it_to_ot("model_server") == " historian_node"

    def test_evaluate_perfect(self):
        t = ITOTTranslator()
        assert t.evaluate_translation("latency", "response_time") == 1.0

    def test_evaluate_no_translation(self):
        t = ITOTTranslator()
        assert t.evaluate_translation("quantum", "classical") == 0.0

    def test_vocabulary_size(self):
        t = ITOTTranslator()
        assert t.vocabulary_size >= 20


class TestTechnicalDebtGovernor:
    def test_register_and_get(self):
        gov = TechnicalDebtGovernor()
        debt = TechDebt(id="d1", debt_type=DebtType.DATA, severity=DebtSeverity.MEDIUM,
                        iota_impact=0.3)
        gov.register_debt(debt)
        assert gov.get_debt("d1") is not None

    def test_auto_high_severity(self):
        gov = TechnicalDebtGovernor()
        debt = TechDebt(id="d2", debt_type=DebtType.MODEL, severity=DebtSeverity.LOW,
                        iota_impact=0.1)
        gov.register_debt(debt)
        assert gov.get_debt("d2").severity == DebtSeverity.HIGH

    def test_resolve(self):
        gov = TechnicalDebtGovernor()
        debt = TechDebt(id="d3", debt_type=DebtType.SEMANTIC, severity=DebtSeverity.MEDIUM,
                        iota_impact=0.3)
        gov.register_debt(debt)
        assert gov.resolve_debt("d3")
        assert gov.get_debt("d3").resolved

    def test_scan_dead_zero(self):
        gov = TechnicalDebtGovernor()
        gov.register_debt(TechDebt(id="d1", debt_type=DebtType.DATA, severity=DebtSeverity.HIGH,
                                   iota_impact=0.1))
        gov.register_debt(TechDebt(id="d2", debt_type=DebtType.MODEL, severity=DebtSeverity.LOW,
                                   iota_impact=0.8))
        critical = gov.scan_dead_zero_debts()
        assert len(critical) == 1
        assert critical[0].id == "d1"

    def test_prioritize(self):
        gov = TechnicalDebtGovernor()
        gov.register_debt(TechDebt(id="d1", debt_type=DebtType.DATA, severity=DebtSeverity.HIGH,
                                   iota_impact=0.1, fix_cost=3))
        gov.register_debt(TechDebt(id="d2", debt_type=DebtType.MODEL, severity=DebtSeverity.MEDIUM,
                                   iota_impact=0.5, fix_cost=1))
        prioritized = gov.prioritize()
        assert len(prioritized) == 2

    def test_stats(self):
        gov = TechnicalDebtGovernor()
        gov.register_debt(TechDebt(id="d1", debt_type=DebtType.DATA, severity=DebtSeverity.MEDIUM,
                                   iota_impact=0.3))
        stats = gov.debt_stats
        assert stats["total"] == 1
        assert stats["active"] == 1


class TestZeroTrustGate:
    def test_unknown_entity(self):
        zt = ZeroTrustGate()
        result = zt.evaluate("unknown")
        assert result.trust_level == TrustLevel.UNTRUSTED

    def test_verified_entity(self):
        zt = ZeroTrustGate()
        zt.register_entity("sensor_A")
        result = zt.evaluate("sensor_A", request_iota=0.8)
        assert result.trust_level == TrustLevel.VERIFIED

    def test_conditional_trust(self):
        zt = ZeroTrustGate()
        zt.register_entity("sensor_B")
        result = zt.evaluate("sensor_B", request_iota=0.3)
        assert result.trust_level == TrustLevel.CONDITIONAL

    def test_dead_zero_block(self):
        zt = ZeroTrustGate()
        zt.register_entity("sensor_C")
        result = zt.evaluate("sensor_C", request_iota=0.05)
        assert result.trust_level == TrustLevel.BLOCKED

    def test_adc_detection(self):
        zt = ZeroTrustGate()
        zt.register_entity("attacker")
        result = zt.evaluate("attacker", request_iota=0.8, content="exec(rm -rf /)")
        assert result.trust_level == TrustLevel.BLOCKED
        assert "command_injection" in result.adc_patterns

    def test_blocked_count(self):
        zt = ZeroTrustGate()
        zt.register_entity("e1")
        zt.evaluate("e1", request_iota=0.05)
        zt.evaluate("unknown", request_iota=0.8)
        assert zt.blocked_count >= 1


class TestITOTBridge:
    def test_translate_it(self):
        bridge = ITOTBridge()
        result = bridge.translate("latency", TechDomain.IT)
        assert result == "response_time"

    def test_translate_ot(self):
        bridge = ITOTBridge()
        result = bridge.translate("alarm", TechDomain.OT)
        assert result == "alert"

    def test_register_and_scan_debt(self):
        bridge = ITOTBridge()
        bridge.register_debt(TechDebt(id="d1", debt_type=DebtType.DATA,
                                      severity=DebtSeverity.HIGH, iota_impact=0.1))
        critical = bridge.scan_critical_debts()
        assert len(critical) == 1

    def test_trust_evaluation(self):
        bridge = ITOTBridge()
        bridge.register_entity("sensor_1")
        result = bridge.evaluate_trust("sensor_1", iota=0.7)
        assert result.trust_level == TrustLevel.VERIFIED

    def test_unified_iota(self):
        bridge = ITOTBridge()
        bridge.add_kpi(JointKPI(id="k1", name="availability",
                                it_target=0.99, ot_target=0.99,
                                current_it=0.98, current_ot=0.97,
                                iota_score=0.95))
        assert bridge.compute_unified_iota() == 0.95

    def test_stats(self):
        bridge = ITOTBridge()
        stats = bridge.stats
        assert "vocabulary_size" in stats
        assert "debt_stats" in stats


# ═══════════════════════════════════════════════════════════════
# MemOS 集成测试
# ═══════════════════════════════════════════════════════════════

from sim.memos_fusion import TOMAS_Mem_OS_Fusion


class TestMemOSFDEIntegration:
    def setup_method(self):
        self.fusion = TOMAS_Mem_OS_Fusion()
        self.fusion.install_fde_builder()

    def test_fde_installed(self):
        assert self.fusion.fde_installed

    def test_fde_add_node(self):
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI, iota_value=0.8)
        self.fusion.fde_add_node(node)
        assert self.fusion.fde_stats()["total"] == 1

    def test_fde_validate(self):
        node = FDENode(id="n1", name="test", node_type=FDENodeType.QI, iota_value=0.8,
                       eml_vertex_ids=["v1"], nasga_asym=0.1, gh_distance=0.2,
                       self_anchor_deviation=0.1)
        self.fusion.fde_add_node(node)
        result = self.fusion.fde_validate("n1")
        assert result.all_pass

    def test_fde_not_installed(self):
        fusion = TOMAS_Mem_OS_Fusion()
        with pytest.raises(RuntimeError):
            fusion.fde_validate("n1")

    def test_fde_build_from_eml(self):
        vertices = [{"id": "v1", "name": "sensor", "i_value": 0.7}]
        ids = self.fusion.fde_build_from_eml(vertices, "scada")
        assert len(ids) == 1


class TestMemOSDualTimelineIntegration:
    def setup_method(self):
        self.fusion = TOMAS_Mem_OS_Fusion()
        self.fusion.install_dual_timeline()

    def test_installed(self):
        assert self.fusion.dual_timeline_installed

    def test_observe(self):
        event = self.fusion.dt_observe("obs1", {"data": "temp"}, iota=0.8)
        assert event.id == "obs1"

    def test_think(self):
        verdict, sing = self.fusion.dt_think("h1", "test hypothesis", iota=0.8)
        assert verdict == FirewallVerdict.ALLOW

    def test_stats(self):
        self.fusion.dt_observe("o1", iota=0.8)
        stats = self.fusion.dt_stats()
        assert stats["external_events"] == 1

    def test_not_installed(self):
        fusion = TOMAS_Mem_OS_Fusion()
        with pytest.raises(RuntimeError):
            fusion.dt_observe("o1")


class TestMemOSITOTIntegration:
    def setup_method(self):
        self.fusion = TOMAS_Mem_OS_Fusion()
        self.fusion.install_itot_bridge()

    def test_installed(self):
        assert self.fusion.itot_installed

    def test_translate(self):
        result = self.fusion.itot_translate("latency", "IT")
        assert result == "response_time"

    def test_register_debt(self):
        debt = TechDebt(id="d1", debt_type=DebtType.DATA, severity=DebtSeverity.MEDIUM,
                        iota_impact=0.3)
        self.fusion.itot_register_debt(debt)
        stats = self.fusion.itot_stats()
        assert stats["debt_stats"]["total"] == 1

    def test_trust(self):
        self.fusion.itot_register_entity("e1")
        result = self.fusion.itot_evaluate_trust("e1", iota=0.8)
        assert result.trust_level == TrustLevel.VERIFIED

    def test_not_installed(self):
        fusion = TOMAS_Mem_OS_Fusion()
        with pytest.raises(RuntimeError):
            fusion.itot_translate("test")
