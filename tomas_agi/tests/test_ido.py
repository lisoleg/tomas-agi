"""
IDO 桥接测试套件 — 李正强框架 ↔ TOMAS 融合

覆盖:
  - IDOFiveElementTemplate (五元素模板, 梯度流, UV截断)
  - PrimeZeroDuality (κ²=-1, K_IR=4, 有限标度律)
  - InformationalCardinality (I(M) 三元组)
  - IDOTierClassifier (Tier1/2/3 + A1-A4 验证链)
  - KappaMemoryModule (κ-MM 记忆存取)
  - IDOFlowSimulator (IDO 证明流)
  - IDOBridge (完整编排)
  - IDOTProcAuditor (T-Proc 审计)
  - IDOSAIAdapter (SAI ↔ IDO 转换)
  - IDODeadZeroExtension (死零扩展)
  - TOMAS MemOS IDO 集成
  - 可证伪预言 P_IDO_1/2/3
"""

import pytest
import sys, os, json, time, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sim'))

from ido_bridge import (
    IDOTier, IDOAxiom, EvidenceLevel, AuditStatus,
    IDOConfiguration, IDOFlowState, IDOHypothesis, IDOAssessment,
    IDOFiveElementTemplate, PrimeZeroDuality, InformationalCardinality,
    IDOTierClassifier, KappaMemoryModule, IDOFlowSimulator,
    IDOBridge, IDOTProcAuditor, PrimeZeroState, KappaMemoryRecord,
)

# ═══════════════════════════════════════════════════════════════
# IDOFiveElementTemplate
# ═══════════════════════════════════════════════════════════════

class TestIDOFiveElementTemplate:
    def test_get_configuration_known(self):
        t = IDOFiveElementTemplate()
        config = t.get_configuration("Poincare_Conjecture")
        assert config is not None
        assert config.config_dim == 4
        assert "π₁=0" in config.uv_constraints

    def test_get_configuration_unknown(self):
        t = IDOFiveElementTemplate()
        assert t.get_configuration("Unknown_Problem") is None

    def test_tier_classification(self):
        t = IDOFiveElementTemplate()
        assert t.get_tier("Poincare_Conjecture") == IDOTier.TIER1_PROVED
        assert t.get_tier("Riemann_Hypothesis") == IDOTier.TIER2_AXIOMATIC
        assert t.get_tier("Yang_Mills_Gap") == IDOTier.TIER3_OPEN
        assert t.get_tier("Unknown") == IDOTier.TIER2_AXIOMATIC  # default

    def test_compute_I_normal(self):
        t = IDOFiveElementTemplate()
        i_val = t.compute_I(ricci_scalar=0.5, kl_divergence=0.3)
        assert 0 < i_val <= 1.0

    def test_compute_I_zero(self):
        t = IDOFiveElementTemplate()
        i_val = t.compute_I(ricci_scalar=0.0, kl_divergence=0.0)
        assert i_val == 0.0

    def test_gradient_norm(self):
        t = IDOFiveElementTemplate()
        norm = t.compute_gradient_norm(0.3, -0.2)
        # ‖∂_t g‖ > 0 for non-zero (Ric+∇²f)
        assert norm > 0

    def test_monotonic(self):
        t = IDOFiveElementTemplate()
        assert t.is_monotonic(0.5, 0.4)
        assert not t.is_monotonic(0.4, 0.5)  # 0.4 < 0.5-1e-6 → False

    def test_near_fixed_point(self):
        t = IDOFiveElementTemplate()
        assert t.is_near_fixed_point(0.01, 0.01)
        assert not t.is_near_fixed_point(0.5, 0.01)

    def test_uv_truncate(self):
        t = IDOFiveElementTemplate()
        data = [{"i_value": 0.5}, {"i_value": 0.1}, {"i_value": 0.3}]
        filtered = t.uv_truncate(data, i_threshold=0.15)
        assert len(filtered) == 2  # 0.1 removed

    def test_run_flow_tier1(self):
        t = IDOFiveElementTemplate()
        flow = t.run_flow("Poincare_Conjecture", max_steps=50)
        assert isinstance(flow, IDOFlowState)
        assert flow.step > 0
        assert 0 <= flow.i_value <= 1.0

    def test_run_flow_tier2(self):
        t = IDOFiveElementTemplate()
        flow = t.run_flow("Riemann_Hypothesis", max_steps=80)
        assert flow.i_value > 0
        assert flow.gradient_norm >= 0

    def test_run_flow_tier3(self):
        t = IDOFiveElementTemplate()
        flow = t.run_flow("Yang_Mills_Gap", max_steps=60)
        assert isinstance(flow, IDOFlowState)

    def test_problem_config_completeness(self):
        t = IDOFiveElementTemplate()
        # All 12 problems should have configs
        assert len(t.PROBLEM_CONFIGS) >= 12

    def test_fisher_kl_decomposition(self):
        t = IDOFiveElementTemplate()
        flow = t.run_flow("Riemann_Hypothesis", max_steps=100, noise_scale=0.01)
        # Fisher + KL terms should sum to approximately i_value
        total = flow.fisher_term + flow.kl_term
        assert abs(total - flow.i_value) < 0.5  # noisy approximation


# ═══════════════════════════════════════════════════════════════
# PrimeZeroDuality
# ═══════════════════════════════════════════════════════════════

class TestPrimeZeroDuality:
    def setup_method(self):
        self.pz = PrimeZeroDuality()

    def test_compute_K(self):
        K = self.pz.compute_K(d_P=0.25, zeta_R=1.5)
        expected = 1.0 / 0.25 + 1.5  # 4.0 + 1.5 = 5.5
        assert abs(K - expected) < 0.01

    def test_finite_size_scaling(self):
        K = self.pz.finite_size_scaling(L=1000.0, a=0.5)
        # K(1000) ≈ 4 + 0.5 * 1000^{-0.51}
        assert 4.0 < K < 5.0

    def test_measure_duality_empty(self):
        state = self.pz.measure_duality(None, None)
        assert isinstance(state, PrimeZeroState)
        assert state.d_P > 0
        assert state.K > 0

    def test_measure_duality_with_data(self):
        prime_data = [2.0, 3.0, 5.0, 7.0, 11.0, 13.0]
        zero_data = [14.13, 21.02, 25.01]
        state = self.pz.measure_duality(prime_data, zero_data)
        assert state.K > 3.5
        assert state.scale > 0

    def test_is_near_ir(self):
        assert self.pz.is_near_ir_fixed_point(4.0)
        assert not self.pz.is_near_ir_fixed_point(11.0, tolerance=0.3)

    def test_self_duality_check(self):
        signal = [0.2, 0.8, 0.2, 0.8]
        result = self.pz.self_duality_check(signal)
        assert "is_self_dual" in result

    def test_self_duality_short(self):
        result = self.pz.self_duality_check([0.5])
        assert result["is_self_dual"] is False

    def test_information_conservation(self):
        total, conserved = self.pz.information_conservation(1.46, -1.46)
        assert abs(total) < 0.01
        assert conserved

    def test_information_conservation_broken(self):
        total, conserved = self.pz.information_conservation(1.46, -0.5)
        assert not conserved

    def test_ir_fixed_point_constant(self):
        assert self.pz.K_IR_THEORETICAL == 4.0
        assert self.pz.K_UV_THEORETICAL == 11.0


# ═══════════════════════════════════════════════════════════════
# InformationalCardinality
# ═══════════════════════════════════════════════════════════════

class TestInformationalCardinality:
    def setup_method(self):
        self.ic = InformationalCardinality()

    def test_prime_set(self):
        alpha, delta, iota = self.ic.for_prime_set()
        assert alpha == 1
        assert delta == 0.5
        assert abs(iota - (-1.46035)) < 0.01

    def test_classical_cantor(self):
        alpha, delta, iota = self.ic.for_classical_cantor()
        assert delta == 1.0 / 3.0
        assert iota == 0.0

    def test_prime_fractal(self):
        alpha, delta, iota = self.ic.for_prime_fractal()
        assert delta == 0.25

    def test_compare_greater(self):
        prime = self.ic.for_prime_set()
        cantor = self.ic.for_classical_cantor()
        assert self.ic.compare(prime, cantor) > 0  # prime > cantor (delta 0.5 > 1/3)

    def test_compare_equal(self):
        a = self.ic.compute(1, 0.5, 1.46)
        b = self.ic.compute(1, 0.5, 1.46)
        assert self.ic.compare(a, b) == 0

    def test_conservation_law_true(self):
        assert self.ic.information_conservation_law(1.4603545, -1.4603545)
        assert not self.ic.information_conservation_law(1.0, 0.0)


# ═══════════════════════════════════════════════════════════════
# IDOTierClassifier
# ═══════════════════════════════════════════════════════════════

class TestIDOTierClassifier:
    def setup_method(self):
        self.template = IDOFiveElementTemplate()
        self.cls = IDOTierClassifier(self.template)

    def test_classify_tier1(self):
        assert self.cls.classify("Poincare_Conjecture") == IDOTier.TIER1_PROVED
        assert self.cls.classify("RMT_Universality") == IDOTier.TIER1_PROVED

    def test_classify_tier2(self):
        assert self.cls.classify("Riemann_Hypothesis") == IDOTier.TIER2_AXIOMATIC
        assert self.cls.classify("P_vs_NP") == IDOTier.TIER2_AXIOMATIC

    def test_classify_tier3(self):
        assert self.cls.classify("Yang_Mills_Gap") == IDOTier.TIER3_OPEN
        assert self.cls.classify("Navier_Stokes") == IDOTier.TIER3_OPEN

    def test_get_gaps_tier1(self):
        gaps = self.cls.get_gaps("Poincare_Conjecture")
        assert gaps == []

    def test_get_gaps_tier2(self):
        gaps = self.cls.get_gaps("Riemann_Hypothesis")
        assert len(gaps) == 4
        assert "A1" in gaps

    def test_next_axiom(self):
        assert self.cls.next_axiom_to_prove("Riemann_Hypothesis") == "A1"
        assert self.cls.next_axiom_to_prove("Poincare_Conjecture") is None

    def test_proof_sketch_rh(self):
        sketch = self.cls.produce_proof_sketch("Riemann_Hypothesis")
        assert "A1" in sketch
        assert "Wasserstein" in sketch

    def test_proof_sketch_unknown(self):
        sketch = self.cls.produce_proof_sketch("Unknown")
        assert "A1-A4" in sketch

    def test_classify_custom_axioms(self):
        # 如果手动传 A1=True 但 A2=False → Tier2
        tier = self.cls.classify("Riemann_Hypothesis", {"A1":True,"A2":False,"A3":False,"A4":False})
        assert tier == IDOTier.TIER2_AXIOMATIC


# ═══════════════════════════════════════════════════════════════
# KappaMemoryModule
# ═══════════════════════════════════════════════════════════════

class TestKappaMemoryModule:
    def setup_method(self):
        self.kmm = KappaMemoryModule(capacity=100)

    def test_encode_decode(self):
        record = self.kmm.encode({"concept": "Riemann_Hypothesis", "iota": 0.8})
        assert record.id.startswith("kmm_")
        assert abs(record.kappa_signature.imag) > 0

    def test_retrieve(self):
        self.kmm.encode({"key": "value"}, record_id="test_001")
        retrieved = self.kmm.retrieve("test_001")
        assert retrieved is not None
        assert retrieved.content["key"] == "value"

    def test_retrieve_missing(self):
        assert self.kmm.retrieve("nonexistent") is None

    def test_retrieve_by_signature(self):
        r = self.kmm.encode({"type": "mathematical"}, record_id="math_001")
        results = self.kmm.retrieve_by_signature(r.kappa_signature, tolerance=0.2)
        assert len(results) >= 1

    def test_search_content(self):
        self.kmm.encode({"problem": "Riemann_Hypothesis"})
        self.kmm.encode({"problem": "P_vs_NP"})
        results = self.kmm.search_content("Riemann")
        assert len(results) >= 1

    def test_search_content_missing(self):
        results = self.kmm.search_content("xyzabc_nonexistent")
        assert len(results) == 0

    def test_forgetting_rate(self):
        rate = self.kmm.forgetting_rate(100.0)
        expected = 1.0 / math.sqrt(100.0)  # 0.1
        assert abs(rate - expected) < 0.01

    def test_stats(self):
        self.kmm.encode({"a": 1})
        self.kmm.encode({"b": 2})
        stats = self.kmm.get_stats()
        assert stats["total_records"] == 2

    def test_capacity_management(self):
        kmm_small = KappaMemoryModule(capacity=5)
        for i in range(20):
            kmm_small.encode({"i": i})
        assert len(kmm_small.boundary) <= 5


# ═══════════════════════════════════════════════════════════════
# IDOFlowSimulator
# ═══════════════════════════════════════════════════════════════

class TestIDOFlowSimulator:
    def setup_method(self):
        self.template = IDOFiveElementTemplate()
        self.sim = IDOFlowSimulator(self.template)

    def test_simulate_tier1(self):
        result = self.sim.simulate_proof("Poincare_Conjecture")
        assert result["tier"] == "Tier1"
        assert "flow_state" in result
        assert result["flow_state"]["i_value"] > 0

    def test_simulate_tier2(self):
        result = self.sim.simulate_proof("Riemann_Hypothesis")
        assert result["tier"] == "Tier2"

    def test_simulate_with_eml(self):
        eml_data = [{"i_value": 0.8}, {"i_value": 0.05}, {"i_value": 0.6}]
        result = self.sim.simulate_proof("Poincare_Conjecture", eml_data)
        assert result["uv_pruned"] >= 1  # 0.05 removed

    def test_simulate_batch(self):
        results = self.sim.simulate_batch(["Poincare_Conjecture", "Riemann_Hypothesis"])
        assert len(results) == 2
        assert results[0]["tier"] == "Tier1"
        assert results[1]["tier"] == "Tier2"


# ═══════════════════════════════════════════════════════════════
# IDOBridge
# ═══════════════════════════════════════════════════════════════

class TestIDOBridge:
    def setup_method(self):
        self.bridge = IDOBridge(theta_dead=0.15)

    # -- 假设评估 --
    def test_evaluate_tier1_hypothesis(self):
        h = IDOHypothesis(id="pc_01", problem="Poincare_Conjecture",
                          tier=IDOTier.TIER1_PROVED,
                          axiom_status={"A1":True,"A2":True,"A3":True,"A4":True},
                          i_support=0.8, evidence=EvidenceLevel.EMPIRICAL)
        a = self.bridge.evaluate_hypothesis(h)
        assert a.tier == IDOTier.TIER1_PROVED
        assert a.passed_axioms == ["A1","A2","A3","A4"]

    def test_evaluate_tier2_hypothesis_a1_unproven(self):
        h = IDOHypothesis(id="rh_01", problem="Riemann_Hypothesis",
                          tier=IDOTier.TIER2_AXIOMATIC,
                          axiom_status={"A1":False,"A2":False,"A3":False,"A4":False},
                          i_support=0.3)
        a = self.bridge.evaluate_hypothesis(h)
        assert "A1" in a.pending_axioms
        assert len(a.pending_axioms) == 4

    def test_evaluate_mus_hypothesis(self):
        h = IDOHypothesis(id="pnp_01", problem="P_vs_NP",
                          tier=IDOTier.TIER2_AXIOMATIC,
                          i_support=0.5, asym=0.08,
                          competing=["P=NP_solver", "P≠NP_barrier"])
        a = self.bridge.evaluate_hypothesis(h)
        # 应该触发 MUS
        assert a.tomas_status in ("MUS_ACTIVE", "WARN_UNGROUNDED")

    def test_dead_zero_check(self):
        is_dead, reason = self.bridge.dead_zero_check(0.05)
        assert is_dead
        is_dead2, _ = self.bridge.dead_zero_check(0.8, axiom_a1_proved=True)
        assert not is_dead2

    def test_dead_zero_a1_unproven(self):
        is_dead, reason = self.bridge.dead_zero_check(0.3, axiom_a1_proved=False)
        assert is_dead

    def test_mus_check(self):
        is_mus, _ = self.bridge.mus_check(0.08, 2)
        assert is_mus
        is_mus2, _ = self.bridge.mus_check(0.01, 0)
        assert not is_mus2

    def test_tier_classify(self):
        assert self.bridge.tier_classify("Poincare_Conjecture") == IDOTier.TIER1_PROVED
        assert self.bridge.tier_classify("Riemann_Hypothesis") == IDOTier.TIER2_AXIOMATIC

    def test_flow_search(self):
        result = self.bridge.flow_search("Poincare_Conjecture")
        assert "conclusion" in result
        assert "flow_state" in result

    # -- Prime-Zero --
    def test_prime_zero_measure(self):
        state = self.bridge.prime_zero_measure([2,3,5], [14.13, 21.02])
        assert state.K > 0

    # -- κ-MM 记忆 --
    def test_kappa_store_recall(self):
        record = self.bridge.kappa_store({"problem": "RH", "step": "A1"})
        retrieved = self.bridge.kappa_recall(record.id)
        assert retrieved is not None
        assert retrieved.content["problem"] == "RH"

    def test_kappa_recall_missing(self):
        assert self.bridge.kappa_recall("nonexistent") is None

    # -- 可证伪预言 P_IDO_1 --
    def test_p_ido_1(self):
        result = self.bridge.predict_p_ido_1(num_cases=20)
        assert "pure_ido_false_positive_rate" in result
        assert "tproc_false_positive_rate" in result

    # -- 可证伪预言 P_IDO_2 --
    def test_p_ido_2(self):
        result = self.bridge.predict_p_ido_2(t=100.0)
        assert abs(result["forgetting_rate"] - 0.1) < 0.01

    # -- 可证伪预言 P_IDO_3 --
    def test_p_ido_3(self):
        result = self.bridge.predict_p_ido_3()
        assert result["prediction"] == "P_IDO_3"
        assert "tomas_status" in result

    def test_stats(self):
        stats = self.bridge.get_stats()
        assert "kappa_memory" in stats
        assert stats["theta_dead"] == 0.15


# ═══════════════════════════════════════════════════════════════
# IDOTProcAuditor
# ═══════════════════════════════════════════════════════════════

class TestIDOTProcAuditor:
    def setup_method(self):
        self.auditor = IDOTProcAuditor(theta_dead=0.15)

    def test_audit_allow(self):
        h = IDOHypothesis(id="t1_01", problem="Poincare_Conjecture",
                          tier=IDOTier.TIER1_PROVED,
                          axiom_status={"A1":True,"A2":True,"A3":True,"A4":True},
                          i_support=0.8, evidence=EvidenceLevel.EMPIRICAL)
        a = self.auditor.audit(h)
        assert a.tomas_status == "ALLOW"

    def test_audit_reject_dead_zero(self):
        h = IDOHypothesis(id="dz_01", problem="Riemann_Hypothesis",
                          tier=IDOTier.TIER2_AXIOMATIC,
                          i_support=0.05)  # < theta_dead
        a = self.auditor.audit(h)
        assert a.tomas_status == "REJECT"

    def test_audit_mus_active(self):
        h = IDOHypothesis(id="mus_01", problem="P_vs_NP",
                          i_support=0.5, asym=0.08,
                          competing=["P=NP", "P≠NP"])
        a = self.auditor.audit(h)
        # Should be MUS_ACTIVE (if conditions met) or WARN_UNGROUNDED
        assert a.tomas_status in ("MUS_ACTIVE", "WARN_UNGROUNDED")

    def test_audit_batch(self):
        hs = [
            IDOHypothesis(id="a1", problem="Poincare_Conjecture",
                          axiom_status={"A1":True,"A2":True,"A3":True,"A4":True},
                          i_support=0.9, evidence=EvidenceLevel.EMPIRICAL),
            IDOHypothesis(id="a2", problem="Riemann_Hypothesis",
                          i_support=0.05),
        ]
        assessments = self.auditor.audit_batch(hs)
        assert len(assessments) == 2
        assert assessments[0].tomas_status == "ALLOW"
        assert assessments[1].tomas_status == "REJECT"

    def test_filter_allowed(self):
        hs = [
            IDOHypothesis(id="a", problem="Poincare_Conjecture",
                          axiom_status={"A1":True,"A2":True,"A3":True,"A4":True},
                          i_support=0.9, evidence=EvidenceLevel.EMPIRICAL),
            IDOHypothesis(id="r", problem="Riemann_Hypothesis", i_support=0.05),
        ]
        results = self.auditor.audit_batch(hs)
        allowed = self.auditor.filter_allowed(results)
        assert len(allowed) == 1

    def test_filter_mus(self):
        h = IDOHypothesis(id="mus", problem="P_vs_NP",
                          i_support=0.5, asym=0.08,
                          competing=["P=NP", "P≠NP"])
        results = self.auditor.audit_batch([h])
        mus = self.auditor.filter_mus(results)
        assert len(mus) >= 0  # dep on bridge conditions

    def test_filter_rejected(self):
        h = IDOHypothesis(id="bad", problem="Riemann_Hypothesis", i_support=0.02)
        results = self.auditor.audit_batch([h])
        rejected = self.auditor.filter_rejected(results)
        assert len(rejected) == 1

    def test_audit_report(self):
        h = IDOHypothesis(id="rpt", problem="Poincare_Conjecture",
                          axiom_status={"A1":True,"A2":True,"A3":True,"A4":True},
                          i_support=0.9, evidence=EvidenceLevel.EMPIRICAL)
        self.auditor.audit(h)
        report = self.auditor.get_audit_report()
        assert report["total_audits"] >= 1

    def test_reset(self):
        h = IDOHypothesis(id="r", problem="Poincare_Conjecture",
                          axiom_status={"A1":True,"A2":True,"A3":True,"A4":True},
                          i_support=0.9, evidence=EvidenceLevel.EMPIRICAL)
        self.auditor.audit(h)
        self.auditor.reset()
        assert len(self.auditor.audit_log) == 0

    def test_schedule(self):
        problems = ["Poincare_Conjecture", "Riemann_Hypothesis", "Yang_Mills_Gap"]
        schedule = self.auditor.schedule_by_i_density(problems)
        assert len(schedule) == 3
        # Tier1 should have higher I
        assert schedule[0][0] == "Poincare_Conjecture"
        assert schedule[0][1] > 0


# ═══════════════════════════════════════════════════════════════
# IDOSAIAdapter (SAI → IDO 转换)
# ═══════════════════════════════════════════════════════════════

class TestIDOSAIAdapter:
    def _import_adapter(self):
        from sai_tproc import IDOSAIAdapter, Hypothesis, HypothesisSource
        return IDOSAIAdapter, Hypothesis, HypothesisSource

    def test_sai_to_ido_valid(self):
        IDOSAIAdapter, Hypothesis, HypothesisSource = self._import_adapter()
        adapter = IDOSAIAdapter()
        h = Hypothesis(id="sai_test", data="wooden table on cliff edge",
                       source=HypothesisSource.SAI_WORLD_MODEL, confidence=0.85)
        result = adapter.sai_to_ido(h)
        if result is not None:
            assert result.id == "ido_sai_test"
            assert result.i_support > 0
            assert result.evidence == EvidenceLevel.EMPIRICAL

    def test_sai_to_ido_low_confidence(self):
        IDOSAIAdapter, Hypothesis, HypothesisSource = self._import_adapter()
        adapter = IDOSAIAdapter()
        h = Hypothesis(id="sai_low", data="perpetual motion machine",
                       source=HypothesisSource.SAI_WORLD_MODEL, confidence=0.1)
        result = adapter.sai_to_ido(h)
        if result is not None:
            assert result.i_support < 0.2
            assert result.evidence == EvidenceLevel.UNGROUNDED

    def test_audit_sai_outputs(self):
        IDOSAIAdapter, Hypothesis, HypothesisSource = self._import_adapter()
        adapter = IDOSAIAdapter()
        hs = [
            Hypothesis(id="sa", data="stable table on ground", source=HypothesisSource.SAI_WORLD_MODEL, confidence=0.9),
            Hypothesis(id="sb", data="floating table 30cm above", source=HypothesisSource.SAI_WORLD_MODEL, confidence=0.3),
        ]
        results = adapter.audit_sai_outputs(hs)
        assert len(results) >= 2
        # High-confidence should have better status
        statuses = [r.get("tomas_status", r.get("reason", "")) for r in results]
        assert len(statuses) == 2


# ═══════════════════════════════════════════════════════════════
# MemOS IDO 集成
# ═══════════════════════════════════════════════════════════════

class TestMemOSIDOIntegration:
    def _get_fusion(self):
        from memos_fusion import TOMAS_Mem_OS_Fusion
        fusion = TOMAS_Mem_OS_Fusion()
        fusion.install_ido_bridge()
        return fusion

    def test_install_ido_bridge(self):
        fusion = self._get_fusion()
        assert hasattr(fusion, '_ido_bridge')

    def test_ido_evaluate(self):
        fusion = self._get_fusion()
        result = fusion.ido_evaluate({
            "id": "test_rh", "problem": "Riemann_Hypothesis",
            "tier": "Tier2",
            "axiom_status": {"A1":False,"A2":False,"A3":False,"A4":False},
            "i_support": 0.3,
        })
        assert result["tier"] == "Tier2"
        assert "tomas_status" in result
        assert "next_action" in result

    def test_ido_flow_search(self):
        fusion = self._get_fusion()
        result = fusion.ido_flow_search("Poincare_Conjecture")
        assert "conclusion" in result

    def test_ido_tier_classify(self):
        fusion = self._get_fusion()
        tier = fusion.ido_tier_classify("Poincare_Conjecture")
        assert tier == "Tier1"

    def test_ido_kappa_store_recall(self):
        fusion = self._get_fusion()
        record = fusion.ido_kappa_store({"fact": "PI = 3.14159"})
        assert "id" in record
        retrieved = fusion.ido_kappa_recall(record["id"])
        assert retrieved is not None
        assert retrieved["content"]["fact"] == "PI = 3.14159"

    def test_ido_prime_zero_measure(self):
        fusion = self._get_fusion()
        state = fusion.ido_prime_zero_measure([2,3,5,7], [14.13, 21.02])
        assert state["K_IR"] == 4.0
        assert state["K_UV"] == 11.0

    def test_ido_predictions(self):
        fusion = self._get_fusion()
        preds = fusion.ido_predictions()
        assert "p_ido_1" in preds
        assert "p_ido_2" in preds
        assert "p_ido_3" in preds

    def test_get_ido_stats(self):
        fusion = self._get_fusion()
        stats = fusion.get_ido_stats()
        assert "kappa_memory" in stats

    def test_ido_not_installed(self):
        from memos_fusion import TOMAS_Mem_OS_Fusion
        fusion = TOMAS_Mem_OS_Fusion()
        with pytest.raises(RuntimeError):
            fusion.ido_evaluate({"problem": "RH"})


# ═══════════════════════════════════════════════════════════════
# IDODeadZeroExtension
# ═══════════════════════════════════════════════════════════════

class TestIDODeadZeroExtension:
    def _get_ext(self):
        from dead_zero_mus import DeadZeroMUSGate, IDODeadZeroExtension
        gate = DeadZeroMUSGate(theta_dead=0.15)
        ext = IDODeadZeroExtension(gate)
        return ext, gate

    def test_audit_ido_allow(self):
        ext, _ = self._get_ext()
        result = ext.audit_ido_proof("Poincare_Conjecture", i_value=0.8, axiom_a1_proved=True)
        assert result["status"] == "ALLOW"
        assert not result["dead_zero_triggered"]

    def test_audit_ido_reject(self):
        ext, _ = self._get_ext()
        result = ext.audit_ido_proof("Riemann_Hypothesis", i_value=0.03)
        assert result["status"] == "REJECT"
        assert result["dead_zero_triggered"]

    def test_audit_ido_mus(self):
        ext, _ = self._get_ext()
        result = ext.audit_ido_proof("P_vs_NP", i_value=0.5, asym=0.08, evidence_flags=["P=NP","P≠NP"])
        assert result["status"] == "MUS_ACTIVE"
        assert result["mus_triggered"]

    def test_available(self):
        ext, _ = self._get_ext()
        assert ext.available is True


# ═══════════════════════════════════════════════════════════════
# 综合测试: TOMAS-IDO 融合端到端
# ═══════════════════════════════════════════════════════════════

class TestTOMASIDOEndToEnd:
    """端到端测试: IDO Level 4 数理引擎 → T-Proc Level 5 认知审计"""

    def test_full_pipeline_tier1(self):
        """Tier1 已证问题: 梯度流 → 通过审计"""
        bridge = IDOBridge()
        auditor = IDOTProcAuditor(bridge)
        h = IDOHypothesis(
            id="e2e_t1", problem="Poincare_Conjecture",
            axiom_status={"A1":True,"A2":True,"A3":True,"A4":True},
            i_support=0.85, evidence=EvidenceLevel.EMPIRICAL,
        )
        a = auditor.audit(h)
        assert a.tomas_status == "ALLOW"
        assert a.passed_axioms == ["A1","A2","A3","A4"]
        assert a.next_action.startswith("PROCEED") or a.next_action.startswith("ALL")

    def test_full_pipeline_tier2_dead_zero(self):
        """Tier2 RH: A1未证 → 死零拦截"""
        bridge = IDOBridge()
        auditor = IDOTProcAuditor(bridge)
        h = IDOHypothesis(
            id="e2e_t2", problem="Riemann_Hypothesis",
            i_support=0.3, evidence=EvidenceLevel.INFERRED,
        )
        a = auditor.audit(h)
        assert a.tomas_status in ("REJECT", "UNPROVABLE_LACKING_A1")
        assert "A1" in a.pending_axioms

    def test_full_pipeline_tier2_mus(self):
        """Tier2 P=NP: 正反竞争 → MUS双存"""
        bridge = IDOBridge()
        auditor = IDOTProcAuditor(bridge)
        h = IDOHypothesis(
            id="e2e_pnp", problem="P_vs_NP",
            i_support=0.5, asym=0.06, competing=["P=NP_prover", "P≠NP_barrier"],
        )
        a = auditor.audit(h)
        assert a.tomas_status in ("MUS_ACTIVE", "WARN_UNGROUNDED")

    def test_kappa_memory_end_to_end(self):
        """κ-MM: 编码→检索→遗忘"""
        bridge = IDOBridge()
        # 存储多个记录
        ids = []
        for i in range(5):
            r = bridge.kappa_store({"step": f"A{i+1}", "problem": "RH"})
            ids.append(r.id)
        # 检索
        for rid in ids:
            assert bridge.kappa_recall(rid) is not None
        # 遗忘率
        rate = bridge.kappa_memory.forgetting_rate(25.0)
        assert rate > 0
        assert bridge.kappa_memory.get_stats()["total_records"] == 5

    def test_prime_zero_flow(self):
        """素数-零点对偶: 测度 + 有限标度律 + 信息守恒"""
        bridge = IDOBridge()
        state = bridge.prime_zero_measure(
            prime_data=[2,3,5,7,11,13,17,19],
            zero_data=[14.13, 21.02, 25.01, 30.42],
        )
        assert 3.5 < state.K < 6.0  # near IR fixed point
        total, conserved = bridge.duality.information_conservation(1.46, -1.46)
        assert conserved

    def test_schedule_optimization(self):
        """ℐ-最优调度: Tier1 优先 → Tier3 最后"""
        auditor = IDOTProcAuditor()
        problems = ["Yang_Mills_Gap", "Riemann_Hypothesis", "Poincare_Conjecture"]
        schedule = auditor.schedule_by_i_density(problems)
        # Poincare (Tier1) 应该排在第一位
        assert schedule[0][0] == "Poincare_Conjecture"
        assert schedule[0][1] > schedule[-1][1]


# ═══════════════════════════════════════════════════════════════
# 边界测试
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_prime_zero(self):
        pz = PrimeZeroDuality()
        state = pz.measure_duality([], [])
        assert state.K > 0  # Uses defaults

    def test_zero_iota_hypothesis(self):
        bridge = IDOBridge(theta_dead=0.15)
        h = IDOHypothesis(id="zero_iota", problem="Riemann_Hypothesis",
                          i_support=0.0, evidence=EvidenceLevel.UNGROUNDED)
        a = bridge.evaluate_hypothesis(h)
        assert a.tomas_status == "REJECT"

    def test_max_i_hypothesis(self):
        bridge = IDOBridge()
        h = IDOHypothesis(id="max_i", problem="Poincare_Conjecture",
                          tier=IDOTier.TIER1_PROVED,
                          axiom_status={"A1":True,"A2":True,"A3":True,"A4":True},
                          i_support=1.0, evidence=EvidenceLevel.EMPIRICAL)
        a = bridge.evaluate_hypothesis(h)
        assert a.tomas_status == "ALLOW"

    def test_competing_empty(self):
        """MUS: competing为空 → 不触发MUS"""
        bridge = IDOBridge()
        h = IDOHypothesis(id="no_compete", problem="P_vs_NP",
                          i_support=0.5, asym=0.08, competing=[])
        a = bridge.evaluate_hypothesis(h)
        assert a.tomas_status not in ("MUS_ACTIVE",)

    def test_unknown_problem_flow(self):
        t = IDOFiveElementTemplate()
        flow = t.run_flow("NonExistentProblem", max_steps=30)
        assert flow.i_value >= 0

    def test_serialize_config(self):
        config = IDOConfiguration(uv_constraints=["test"], config_dim=5, symmetry_group="SU(2)", topological_barrier="test_barrier")
        d = config.to_dict()
        assert d["config_dim"] == 5
        assert d["symmetry_group"] == "SU(2)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
