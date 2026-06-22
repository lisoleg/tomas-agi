# -*- coding: utf-8 -*-
"""
v3.8 模块测试套件 — GaussEx-EML Bridge + Cognitive Compression Engine
=======================================================================

测试覆盖:
  - gaussex_eml.py: GaussExSystem, Fibre, GaussianNoise, CopartialMap,
    Interconnection, NoisyResistor, CopartialRiskControl,
    ComplementaryInterconnection, GaussExPsiAnchor, GaussExKSnapRecord,
    GaussExPredictionValidator, IndustrialFeasibilityTheorem
  - cognitive_compression.py: PDEConservationLaw, WMHyperedgePDE,
    ENTBioNetwork, BioPsiAnchor, MUSEndogenousConflict, PhysicalAIEngine,
    CompressionLossKSnap, CognitiveCompressionEmbedding,
    CognitiveCompressionValidator

Author: TOMAS QA Team (严过关)
Version: v1.0 (v3.8)
"""

import pytest
import math
import json
import time
import hashlib
from dataclasses import dataclass

# ── 导入 v3.8 模块 ──────────────────────────────────────────────
from sim.gaussex_eml import (
    Fibre, FibreType, GaussianNoise, NoiseType, GaussExSystem,
    IndustryDomain, CopartialMap, InterconnectionResult, interconnect,
    NoisyResistor, CopartialRiskControl, ComplementaryInterconnection,
    GaussExPsiAnchor, PsiAnchorLevel, GaussExKSnapRecord,
    GaussExPredictionValidator, IndustrialFeasibilityTheorem,
)
from sim.cognitive_compression import (
    ConservationType, PDEConservationLaw, WMHyperedgePDE,
    CompressionStage, EMLLayer, BioPsiAnchorType, BioPsiAnchor,
    ENTBioNetwork, MUSEndogenousConflict, PhysicalAIEngine,
    CompressionLossKSnap, CognitiveCompressionEmbedding,
    CognitiveCompressionValidator,
)


# ══════════════════════════════════════════════════════════════════
#  GaussEx-EML Bridge 测试
# ══════════════════════════════════════════════════════════════════

class TestFibre:
    """测试确定性约束纤维 D"""

    def test_fibre_creation(self):
        f = Fibre("ohms_law", FibreType.PHYSICS_LAW, "V == 10 * I", ["V", "I"])
        assert f.name == "ohms_law"
        assert f.fibre_type == FibreType.PHYSICS_LAW
        assert f.variables == ["V", "I"]
        assert f.i_value == 1.0

    def test_fibre_is_satisfied_true(self):
        f = Fibre("test", FibreType.BUSINESS_RULE, "income > debt", ["income", "debt"])
        assert f.is_satisfied({"income": 100, "debt": 50}) is True

    def test_fibre_is_satisfied_false(self):
        f = Fibre("test", FibreType.BUSINESS_RULE, "income > debt", ["income", "debt"])
        assert f.is_satisfied({"income": 30, "debt": 50}) is False

    def test_fibre_to_dict(self):
        f = Fibre("test", FibreType.CONSERVATION, "mass = 0", ["mass"], i_value=0.9)
        d = f.to_dict()
        assert d["name"] == "test"
        assert d["type"] == "conservation"
        assert d["i_value"] == 0.9

    def test_fibre_types(self):
        assert FibreType.PHYSICS_LAW.value == "physics_law"
        assert FibreType.BUSINESS_RULE.value == "business_rule"
        assert FibreType.LEGAL_COMPLIANCE.value == "legal"
        assert FibreType.CONSERVATION.value == "conservation"
        assert FibreType.KINEMATIC.value == "kinematic"


class TestGaussianNoise:
    """测试高斯噪声 ψ"""

    def test_noise_creation(self):
        n = GaussianNoise(0.5, 0.04)
        assert n.mean == 0.5
        assert n.variance == 0.04
        assert n.noise_type == NoiseType.GAUSSIAN

    def test_noise_std(self):
        n = GaussianNoise(0.0, 9.0)
        assert n.std == pytest.approx(3.0)

    def test_noise_std_zero_variance(self):
        n = GaussianNoise(0.0, 0.0)
        assert n.std == 0.0

    def test_noise_pdf(self):
        n = GaussianNoise(0.0, 1.0)
        # 标准正态分布在 x=0 处的 PDF = 1/sqrt(2π)
        assert n.pdf(0.0) == pytest.approx(1.0 / math.sqrt(2 * math.pi))

    def test_noise_pdf_zero_variance(self):
        n = GaussianNoise(0.0, 0.0)
        assert n.pdf(0.0) == 1.0
        assert n.pdf(1.0) == 0.0

    def test_noise_sample(self):
        n = GaussianNoise(0.0, 1.0)
        s = n.sample()
        assert isinstance(s, float)

    def test_noise_marginal(self):
        n = GaussianNoise(1.0, 2.0, NoiseType.SENSOR, 3)
        m = n.marginal(0)
        assert m.mean == 1.0
        assert m.variance == 2.0

    def test_noise_to_dict(self):
        n = GaussianNoise(0.0, 1.0, NoiseType.THERMAL)
        d = n.to_dict()
        assert d["mean"] == 0.0
        assert d["type"] == "thermal"


class TestGaussExSystem:
    """测试 GaussEx 开放系统"""

    def _make_system(self):
        f = Fibre("ohms_law", FibreType.PHYSICS_LAW, "V == 10 * I", ["V", "I"])
        n = GaussianNoise(0.0, 0.01, NoiseType.SENSOR)
        return GaussExSystem(f, n, IndustryDomain.AUTONOMOUS_DRIVING)

    def test_system_creation(self):
        s = self._make_system()
        assert s.fibre.name == "ohms_law"
        assert s.noise.variance == 0.01
        assert s.domain == IndustryDomain.AUTONOMOUS_DRIVING
        assert len(s.system_id) > 0

    def test_system_auto_id(self):
        s = self._make_system()
        assert s.system_id.startswith("gaussex_")

    def test_system_marginal(self):
        s = self._make_system()
        m = s.marginal("V")
        assert m.mean == 0.0
        assert m.variance == 0.01

    def test_system_to_eml_hyperedge(self):
        s = self._make_system()
        h = s.to_eml_hyperedge()
        assert h["type"] == "GaussEx_Hyperedge"
        assert "fibre_D" in h
        assert "noise_psi" in h
        assert h["domain"] == "auto_drive"


class TestCopartialMap:
    """测试共偏性映射 (隐私计算)"""

    def _make_copartial(self, statistic="mean"):
        f = Fibre("bank_rule", FibreType.BUSINESS_RULE, "income > debt", ["income", "debt"])
        n = GaussianNoise(0.8, 0.1, NoiseType.MARKET)
        s = GaussExSystem(f, n, IndustryDomain.FINTECH)
        return CopartialMap(s, statistic)

    def test_copartial_creation(self):
        c = self._make_copartial()
        assert c.observable_statistic == "mean"
        assert c.psi_anchor_id.startswith("psi_copartial_")

    def test_copartial_project_mean(self):
        c = self._make_copartial("mean")
        result = c.project()
        assert "mean" in result
        assert result["mean"] == 0.8

    def test_copartial_project_variance(self):
        c = self._make_copartial("variance")
        result = c.project()
        assert "variance" in result
        assert result["variance"] == 0.1

    def test_copartial_project_default_prob(self):
        c = self._make_copartial("default_prob")
        result = c.project()
        assert "default_prob" in result
        assert 0.0 <= result["default_prob"] <= 1.0

    def test_copartial_no_raw_data_exposed(self):
        c = self._make_copartial()
        assert c.is_raw_data_exposed() is False

    def test_copartial_eml_query(self):
        c = self._make_copartial()
        q = c.to_eml_query()
        assert "SELECT" in q
        assert "psi_anchor" in q


class TestInterconnection:
    """测试系统互联"""

    def _make_two_systems(self):
        f1 = Fibre("sys_a", FibreType.PHYSICS_LAW, "V == 10 * I", ["V", "I"])
        f2 = Fibre("sys_b", FibreType.KINEMATIC, "a > 0", ["a"])
        n1 = GaussianNoise(0.0, 0.01)
        n2 = GaussianNoise(0.5, 0.02)
        s1 = GaussExSystem(f1, n1, IndustryDomain.AUTONOMOUS_DRIVING)
        s2 = GaussExSystem(f2, n2, IndustryDomain.AUTONOMOUS_DRIVING)
        return s1, s2

    def test_interconnect_basic(self):
        s1, s2 = self._make_two_systems()
        result = interconnect(s1, s2)
        assert isinstance(result, InterconnectionResult)
        assert len(result.participant_ids) == 2

    def test_interconnect_combined_fibre(self):
        s1, s2 = self._make_two_systems()
        result = interconnect(s1, s2)
        assert "AND" in result.combined_fibre.constraint_expr

    def test_interconnect_combined_noise(self):
        s1, s2 = self._make_two_systems()
        result = interconnect(s1, s2)
        # 方差相加
        assert result.combined_noise.variance == pytest.approx(0.03)

    def test_interconnect_complementary(self):
        s1, s2 = self._make_two_systems()
        result = interconnect(s1, s2)
        # 不同变量 → 互补
        assert result.is_complementary is True

    def test_interconnect_not_complementary(self):
        f1 = Fibre("a", FibreType.PHYSICS_LAW, "V == 10 * I", ["V", "I"])
        f2 = Fibre("b", FibreType.PHYSICS_LAW, "V == 5 * I", ["V", "I"])
        s1 = GaussExSystem(f1, GaussianNoise(0, 0.01))
        s2 = GaussExSystem(f2, GaussianNoise(0, 0.02))
        result = interconnect(s1, s2)
        assert result.is_complementary is False

    def test_interconnect_to_dict(self):
        s1, s2 = self._make_two_systems()
        result = interconnect(s1, s2)
        d = result.to_dict()
        assert "combined_fibre" in d
        assert "combined_noise" in d


class TestNoisyResistor:
    """测试含噪电阻 (自动驾驶实例)"""

    def test_resistor_creation(self):
        nr = NoisyResistor(resistance=10.0, noise_variance=0.04)
        assert nr.resistance == 10.0
        assert nr.noise_variance == 0.04
        assert nr.system.domain == IndustryDomain.AUTONOMOUS_DRIVING

    def test_solve_current(self):
        nr = NoisyResistor(resistance=10.0, noise_variance=0.04)
        i_mean, i_var = nr.solve_current(5.0)
        assert i_mean == pytest.approx(0.5)
        assert i_var == pytest.approx(0.04 / 100)

    def test_solve_voltage(self):
        nr = NoisyResistor(resistance=10.0, noise_variance=0.04)
        v_mean, v_var = nr.solve_voltage(2.0)
        assert v_mean == pytest.approx(20.0)

    def test_multi_sensor_fuse(self):
        nr = NoisyResistor(resistance=10.0, noise_variance=0.04)
        result = nr.multi_sensor_fuse([
            ("camera", 5.0, 0.04),
            ("radar", 5.1, 0.02),
            ("lidar", 4.95, 0.01),
        ])
        assert "fused_mean" in result
        assert "fused_variance" in result
        assert 4.9 < result["fused_mean"] < 5.1

    def test_multi_sensor_fuse_empty(self):
        nr = NoisyResistor(resistance=10.0, noise_variance=0.04)
        result = nr.multi_sensor_fuse([])
        assert result["fused_mean"] == 0.0
        assert result["fused_variance"] == float('inf')

    def test_multi_sensor_fuse_lower_variance(self):
        """融合后方差应小于任一单传感器"""
        nr = NoisyResistor(resistance=10.0, noise_variance=0.04)
        result = nr.multi_sensor_fuse([
            ("s1", 5.0, 0.04),
            ("s2", 5.0, 0.04),
        ])
        assert result["fused_variance"] < 0.04


class TestCopartialRiskControl:
    """测试共偏性风控 (金融隐私计算)"""

    def _make_risk_control(self):
        bank = GaussExSystem(
            Fibre("bank_rule", FibreType.BUSINESS_RULE, "income > debt", ["income", "debt"]),
            GaussianNoise(0.8, 0.1, NoiseType.MARKET),
            IndustryDomain.FINTECH,
        )
        eco = GaussExSystem(
            Fibre("eco_rule", FibreType.BUSINESS_RULE, "freq > 10", ["freq"]),
            GaussianNoise(0.6, 0.15, NoiseType.MARKET),
            IndustryDomain.FINTECH,
        )
        return CopartialRiskControl(bank, eco)

    def test_risk_control_creation(self):
        rc = self._make_risk_control()
        assert rc.psi_anchor.anchor_id == "psi_no_raw_data_access"
        assert rc.psi_anchor.level == PsiAnchorLevel.REGULATORY

    def test_joint_risk_assessment(self):
        rc = self._make_risk_control()
        result = rc.joint_risk_assessment()
        assert "joint_default_prob" in result
        assert 0.0 <= result["joint_default_prob"] <= 1.0
        assert result["raw_data_exposed"] is False
        assert result["psi_anchor_active"] is True

    def test_risk_control_jsonld(self):
        rc = self._make_risk_control()
        j = rc.to_jsonld()
        assert j["@context"] == "https://tomas.org/fintech/v1"
        assert j["type"] == "GaussEx_Copartial_System"
        assert "Bank_A" in j
        assert "Ecommerce_B" in j
        assert "Interconnection" in j


class TestComplementaryInterconnection:
    """测试互补互联 (工业数字孪生)"""

    def _make_interconnection(self, temp_mean=85.0):
        phys = GaussExSystem(
            Fibre("vibration", FibreType.PHYSICS_LAW, "vibration < 0.5", ["vibration"]),
            GaussianNoise(0.2, 0.01, NoiseType.SENSOR),
            IndustryDomain.INDUSTRIAL_TWIN,
        )
        rt = GaussExSystem(
            Fibre("temp", FibreType.KINEMATIC, "temp < 100", ["temp"]),
            GaussianNoise(temp_mean, 4.0, NoiseType.THERMAL),
            IndustryDomain.INDUSTRIAL_TWIN,
        )
        return ComplementaryInterconnection(phys, rt, rul_baseline_hours=200.0)

    def test_compute_rul(self):
        ci = self._make_interconnection()
        rul = ci.compute_rul()
        assert "rul_mean_hours" in rul
        assert "rul_std_hours" in rul
        assert rul["rul_mean_hours"] > 0
        assert rul["complementary"] is True

    def test_rul_high_temp_shorter(self):
        """温度越高 → RUL 越短"""
        ci_normal = self._make_interconnection(temp_mean=25.0)
        ci_hot = self._make_interconnection(temp_mean=85.0)
        assert ci_hot.compute_rul()["rul_mean_hours"] < ci_normal.compute_rul()["rul_mean_hours"]

    def test_rul_maintenance_threshold(self):
        ci = self._make_interconnection(temp_mean=85.0)
        rul = ci.compute_rul()
        # 85°C → temp_effect = 1 - 60/100 = 0.4 → RUL = 80h < 150h
        assert rul["maintenance_recommended"] is True

    def test_ksnap_log(self):
        ci = self._make_interconnection()
        log = ci.to_ksnap_log()
        assert "ksnap_id" in log
        assert "System_1" in log
        assert "System_2" in log
        assert "Interconnection_Result" in log


class TestGaussExPsiAnchor:
    """测试 ψ-锚 宪法级权限控制"""

    def test_anchor_creation(self):
        a = GaussExPsiAnchor(
            "psi_test", PsiAnchorLevel.CONSTITUTIONAL,
            "no raw data access", ["sys1", "sys2"],
        )
        assert a.anchor_id == "psi_test"
        assert a.level == PsiAnchorLevel.CONSTITUTIONAL
        assert a.is_active is True

    def test_check_query_allowed(self):
        a = GaussExPsiAnchor("psi", PsiAnchorLevel.REGULATORY, "copartial_only")
        ok, reason = a.check_query("SELECT mean FROM systems")
        assert ok is True

    def test_check_query_blocked_raw_data(self):
        a = GaussExPsiAnchor("psi", PsiAnchorLevel.REGULATORY, "copartial_only")
        ok, reason = a.check_query("SELECT * FROM raw_data")
        assert ok is False
        assert a.violation_count == 1

    def test_check_query_blocked_individual(self):
        a = GaussExPsiAnchor("psi", PsiAnchorLevel.REGULATORY, "copartial_only")
        ok, reason = a.check_query("SELECT individual_record FROM users")
        assert ok is False

    def test_check_interconnection(self):
        a = GaussExPsiAnchor("psi", PsiAnchorLevel.CONSTITUTIONAL, "physics check")
        f = Fibre("test", FibreType.PHYSICS_LAW, "V == R*I", ["V", "I"])
        s1 = GaussExSystem(f, GaussianNoise(0, 0.01))
        s2 = GaussExSystem(f, GaussianNoise(0, 0.02))
        ok, reason = a.check_interconnection(s1, s2)
        assert ok is True

    def test_anchor_inactive(self):
        a = GaussExPsiAnchor("psi", PsiAnchorLevel.OPERATIONAL, "test")
        a.is_active = False
        ok, _ = a.check_query("SELECT * FROM raw_data")
        assert ok is True

    def test_enforce(self):
        a = GaussExPsiAnchor("psi", PsiAnchorLevel.CONSTITUTIONAL, "test")
        f = Fibre("test", FibreType.PHYSICS_LAW, "x > 0", ["x"])
        s = GaussExSystem(f, GaussianNoise(0, 1))
        a.enforce(s)
        assert s.system_id in a.enforced_systems


class TestGaussExKSnapRecord:
    """测试 κ-Snap 审计记录"""

    def test_record_creation(self):
        snap = GaussExKSnapRecord(
            snap_id="ksnap_001",
            system_id="sys_001",
            action="interconnect",
            fibre_snapshot={"name": "test"},
            noise_snapshot={"mean": 0.0},
        )
        assert snap.snap_id == "ksnap_001"
        assert snap.action == "interconnect"

    def test_to_log(self):
        snap = GaussExKSnapRecord(
            snap_id="ksnap_002",
            system_id="sys_002",
            action="solve",
            fibre_snapshot={"constraint": "V==R*I"},
            noise_snapshot={"variance": 0.01},
            psi_anchor_id="psi_test",
            result_summary="I=0.5A",
        )
        log = snap.to_log()
        assert "κ-Snap" in log
        assert "sys_002" in log
        assert "solve" in log
        assert "psi_test" in log

    def test_to_dict(self):
        snap = GaussExKSnapRecord("k", "s", "a")
        d = snap.to_dict()
        assert d["snap_id"] == "k"
        assert d["action"] == "a"


class TestGaussExPredictions:
    """测试可证伪预言 P17-P19"""

    def test_p18_pass(self):
        """P18: 含噪电阻审计链可追溯"""
        nr = NoisyResistor(resistance=10.0, noise_variance=0.04)
        pv = GaussExPredictionValidator()
        result = pv.validate_p18_noisy_resistor_audit(nr, 5.0)
        assert result["prediction"] == "P18"
        assert result["passed"] is True
        assert result["audit_log_exists"] is True

    def test_p17_mechanism(self):
        """P17: 共偏性风控机制验证"""
        bank = GaussExSystem(
            Fibre("bank", FibreType.BUSINESS_RULE, "income > debt", ["income"]),
            GaussianNoise(0.15, 0.01, NoiseType.MARKET),
            IndustryDomain.FINTECH,
        )
        eco = GaussExSystem(
            Fibre("eco", FibreType.BUSINESS_RULE, "freq > 10", ["freq"]),
            GaussianNoise(0.15, 0.01, NoiseType.MARKET),
            IndustryDomain.FINTECH,
        )
        rc = CopartialRiskControl(bank, eco)
        pv = GaussExPredictionValidator()
        result = pv.validate_p17_copartial_risk(rc, ground_truth_default_rate=0.15)
        assert result["prediction"] == "P17"
        assert result["raw_data_exposed"] is False

    def test_p19_mechanism(self):
        """P19: 工业互补互联机制验证"""
        phys = GaussExSystem(
            Fibre("vib", FibreType.PHYSICS_LAW, "vib < 0.5", ["vib"]),
            GaussianNoise(0.2, 0.01, NoiseType.SENSOR),
            IndustryDomain.INDUSTRIAL_TWIN,
        )
        rt = GaussExSystem(
            Fibre("temp", FibreType.KINEMATIC, "temp < 100", ["temp"]),
            GaussianNoise(25.0, 1.0, NoiseType.THERMAL),
            IndustryDomain.INDUSTRIAL_TWIN,
        )
        ci = ComplementaryInterconnection(phys, rt, rul_baseline_hours=200.0)
        pv = GaussExPredictionValidator()
        result = pv.validate_p19_industrial_rul(ci, actual_rul_hours=200.0)
        assert result["prediction"] == "P19"
        assert result["is_complementary"] is True


class TestIndustrialFeasibilityTheorem:
    """测试产业落地可行性定理"""

    def test_polynomial_complexity(self):
        assert IndustrialFeasibilityTheorem.verify_polynomial_complexity(10) is True
        assert IndustrialFeasibilityTheorem.verify_polynomial_complexity(1) is True

    def test_privacy_preservation(self):
        bank = GaussExSystem(
            Fibre("bank", FibreType.BUSINESS_RULE, "income > debt", ["income"]),
            GaussianNoise(0.8, 0.1),
            IndustryDomain.FINTECH,
        )
        eco = GaussExSystem(
            Fibre("eco", FibreType.BUSINESS_RULE, "freq > 10", ["freq"]),
            GaussianNoise(0.6, 0.15),
            IndustryDomain.FINTECH,
        )
        rc = CopartialRiskControl(bank, eco)
        assert IndustrialFeasibilityTheorem.verify_privacy_preservation(rc) is True

    def test_audit_trail(self):
        snap = GaussExKSnapRecord("k", "s", "a",
                                   fibre_snapshot={"x": 1},
                                   noise_snapshot={"y": 2})
        assert IndustrialFeasibilityTheorem.verify_audit_trail(snap) is True

    def test_constitutional_safety(self):
        a = GaussExPsiAnchor("psi", PsiAnchorLevel.CONSTITUTIONAL, "test")
        assert IndustrialFeasibilityTheorem.verify_constitutional_safety(a) is True

    def test_full_verification(self):
        f = Fibre("test", FibreType.PHYSICS_LAW, "x > 0", ["x"])
        s = GaussExSystem(f, GaussianNoise(0, 1))
        a = GaussExPsiAnchor("psi", PsiAnchorLevel.CONSTITUTIONAL, "test", [s.system_id])
        result = IndustrialFeasibilityTheorem.full_verification([s], a)
        assert result["theorem_holds"] is True


# ══════════════════════════════════════════════════════════════════
#  Cognitive Compression Engine 测试
# ══════════════════════════════════════════════════════════════════

class TestPDEConservationLaw:
    """测试 PDE 守恒律"""

    def test_law_creation(self):
        law = PDEConservationLaw(
            ConservationType.MASS,
            "∂ₜρ + ∇·(ρv) = 0",
            ["rho"],
        )
        assert law.conservation_type == ConservationType.MASS
        assert law.psi_anchor_id == "psi_mass_conservation"
        assert law.tolerance == 1e-12

    def test_check_no_violation(self):
        law = PDEConservationLaw(ConservationType.MASS, "mass = 0", ["m"])
        violated, dev = law.check_violation({"m": 100.0}, {"m": 100.0})
        assert violated is False
        assert dev == pytest.approx(0.0)

    def test_check_violation(self):
        law = PDEConservationLaw(ConservationType.MASS, "mass = 0", ["m"])
        violated, dev = law.check_violation({"m": 100.0}, {"m": 90.0})
        assert violated is True
        assert dev == pytest.approx(0.1)

    def test_check_violation_zero_before(self):
        law = PDEConservationLaw(ConservationType.MASS, "mass = 0", ["m"])
        violated, dev = law.check_violation({"m": 0.0}, {"m": 1.0})
        assert violated is True

    def test_to_psi_anchor_rule(self):
        law = PDEConservationLaw(ConservationType.ENERGY, "E = 0", ["E"])
        rule = law.to_psi_anchor_rule()
        assert "ψ-ANCHOR" in rule
        assert "energy_conservation" in rule
        assert "REJECT_AND_LOG" in rule

    def test_all_conservation_types(self):
        for ct in ConservationType:
            law = PDEConservationLaw(ct, "test", ["x"])
            assert law.psi_anchor_id.startswith("psi_")


class TestWMHyperedgePDE:
    """测试 WM 超边 (含 PDE 守恒律)"""

    def _make_wm(self):
        wm = WMHyperedgePDE(
            scene="test_scene",
            sdf_ref="test.sdf",
            pde_source="ReactionDiffusion",
            kappa_depth=5,
        )
        wm.add_conservation_law(PDEConservationLaw(
            ConservationType.MASS, "∂ₜρ + ∇·(ρv) = 0", ["rho"]))
        wm.add_conservation_law(PDEConservationLaw(
            ConservationType.MOMENTUM, "∂ₜ(ρv) + ∇·Π = f", ["rho_v"]))
        return wm

    def test_wm_creation(self):
        wm = self._make_wm()
        assert wm.scene == "test_scene"
        assert len(wm.conservation_laws) == 2

    def test_check_all_conservation_satisfied(self):
        wm = self._make_wm()
        check = wm.check_all_conservation(
            {"rho": 100.0, "rho_v": 50.0},
            {"rho": 100.0, "rho_v": 50.0},
        )
        assert check["all_satisfied"] is True
        assert check["psi_anchor_triggered"] is False

    def test_check_all_conservation_violated(self):
        wm = self._make_wm()
        check = wm.check_all_conservation(
            {"rho": 100.0, "rho_v": 50.0},
            {"rho": 80.0, "rho_v": 50.0},
        )
        assert check["all_satisfied"] is False
        assert check["psi_anchor_triggered"] is True

    def test_to_jsonld(self):
        wm = self._make_wm()
        j = wm.to_jsonld()
        assert j["@context"] == "https://tomas.org/wm/v2"
        assert j["type"] == "WM_Hyperedge"
        assert len(j["PDE_Form"]["conservation_laws"]) == 2
        assert j["kappa_depth"] == 5


class TestBioPsiAnchor:
    """测试生物 ψ-锚"""

    def test_atp_threshold(self):
        a = BioPsiAnchor(BioPsiAnchorType.ATP_THRESHOLD, 2.0, ">")
        assert a.check(3.0) is True
        assert a.check(1.0) is False

    def test_membrane_potential(self):
        a = BioPsiAnchor(BioPsiAnchorType.MEMBRANE_POTENTIAL, -70.0, "<")
        assert a.check(-75.0) is True
        assert a.check(-60.0) is False

    def test_inactive_anchor(self):
        a = BioPsiAnchor(BioPsiAnchorType.ATP_THRESHOLD, 2.0, ">")
        a.is_active = False
        assert a.check(0.0) is True


class TestENTBioNetwork:
    """测试 ENT 内源性网络"""

    def _make_network(self):
        net = ENTBioNetwork("test_net", "tumor")
        net.add_edge("TGF_beta", "upregulates", "Proliferate")
        net.add_edge("FasL", "upregulates", "Apoptose")
        net.add_psi_anchor(BioPsiAnchor(BioPsiAnchorType.ATP_THRESHOLD, 2.0, ">"))
        net.add_psi_anchor(BioPsiAnchor(BioPsiAnchorType.MEMBRANE_POTENTIAL, -70.0, "<"))
        return net

    def test_network_creation(self):
        net = self._make_network()
        assert net.network_id == "test_net"
        assert net.tissue == "tumor"
        assert len(net.nodes) == 4
        assert len(net.edges) == 2

    def test_add_node_no_duplicate(self):
        net = self._make_network()
        net.add_node("TGF_beta")  # Already exists
        assert net.nodes.count("TGF_beta") == 1

    def test_check_bio_state_satisfied(self):
        net = self._make_network()
        result = net.check_bio_state({"atp_threshold": 3.5, "membrane": -75.0})
        assert result["all_satisfied"] is True

    def test_check_bio_state_not_satisfied(self):
        net = self._make_network()
        result = net.check_bio_state({"atp_threshold": 1.0, "membrane": -75.0})
        assert result["all_satisfied"] is False

    def test_to_eml_query(self):
        net = self._make_network()
        q = net.to_eml_query()
        assert "MATCH" in q
        assert "biosystem" in q
        assert "tumor" in q


class TestMUSEndogenousConflict:
    """测试 MUS 内源竞争双存"""

    def _make_mus(self):
        return MUSEndogenousConflict(
            mus_id="mus_test_01",
            entity_a={"signal": "Proliferate", "predicate": "Grow", "i_value": 0.88, "context": "hypoxia"},
            entity_b={"signal": "Apoptose", "predicate": "Die", "i_value": 0.85, "context": "DNA_damage"},
        )

    def test_mus_creation(self):
        mus = self._make_mus()
        assert mus.resolution == "PENDING"
        assert mus.tag == "ent_endogenous_competition"

    def test_mus_resolve_a(self):
        mus = self._make_mus()
        mus.resolve("A")
        assert mus.resolution == "RESOLVED_A"
        assert mus.is_resolved() is True

    def test_mus_resolve_b(self):
        mus = self._make_mus()
        mus.resolve("B")
        assert mus.resolution == "RESOLVED_B"

    def test_mus_resolve_override(self):
        mus = self._make_mus()
        mus.resolve("A", clinician_override=True)
        assert mus.resolution == "OVERRIDDEN"

    def test_mus_to_log(self):
        mus = self._make_mus()
        log = mus.to_log()
        assert "MUS ZONE" in log
        assert "Proliferate" in log
        assert "Apoptose" in log
        assert "PENDING" in log


class TestPhysicalAIEngine:
    """测试物理AI 引擎"""

    def _make_engine(self, kappa=2.0):
        wm = WMHyperedgePDE(scene="test", pde_source="RD_eq")
        wm.add_conservation_law(PDEConservationLaw(ConservationType.MASS, "mass=0", ["m"]))
        return PhysicalAIEngine(pde_hyperedge=wm, kappa=kappa)

    def test_engine_creation(self):
        e = self._make_engine()
        assert e.kappa == 2.0
        assert e.pde_hyperedge.scene == "test"

    def test_gan_polarize(self):
        e = self._make_engine(kappa=1.0)
        p, d = e.gan_polarize()
        # κ=1 → φ=π/4 → cos=sin=√2/2
        assert p == pytest.approx(math.cos(math.pi / 4))
        assert d == pytest.approx(math.sin(math.pi / 4))

    def test_gan_polarize_large_kappa(self):
        """κ 大 → PDE 权重大"""
        e = self._make_engine(kappa=100.0)
        p, d = e.gan_polarize()
        assert p < d  # atan(100) ≈ π/2, cos→0, sin→1 → wave dominant
        # Note: κ→∞ → φ→π/2 → cos→0 (particle→0), sin→1 (wave→1)
        # So κ large → wave_weight dominant (trust data more)

    def test_gan_polarize_small_kappa(self):
        """κ 小 → particle 主导"""
        e = self._make_engine(kappa=0.01)
        p, d = e.gan_polarize()
        assert p > d  # κ→0 → φ→0 → cos→1 (particle dominant)

    def test_couple_pde_data(self):
        e = self._make_engine(kappa=1.0)
        result = e.couple_pde_data(
            pde_state={"x": 1.0},
            data_obs={"x": 2.0},
        )
        assert "coupled_state" in result
        assert "pde_weight" in result
        assert "data_weight" in result
        # κ=1 → equal weights → coupled = (1+2)/2 = 1.5
        assert result["coupled_state"]["x"] == pytest.approx(1.5)

    def test_step(self):
        e = self._make_engine(kappa=1.0)
        result = e.step(
            dt=0.01,
            pde_state={"x": 1.0},
            data_obs={"x": 1.1},
        )
        assert "coupled_state" in result
        assert "kappa" in result
        assert result["ksnap_committed"] is True

    def test_detect_conflict(self):
        e = self._make_engine()
        assert e.detect_endogenous_conflict({"proliferate_signal": 0.8, "apoptose_signal": 0.7}) is True
        assert e.detect_endogenous_conflict({"proliferate_signal": 0.3, "apoptose_signal": 0.7}) is False


class TestCompressionLossKSnap:
    """测试 κ-Snap 压缩损失审计"""

    def test_snap_creation(self):
        snap = CompressionLossKSnap(
            snap_id="k1",
            action="compression",
            original_info_bits=1e6,
            compressed_info_bits=1e3,
        )
        assert snap.original_info_bits == 1e6
        assert snap.compressed_info_bits == 1e3

    def test_compression_ratio(self):
        snap = CompressionLossKSnap("k", "a", 1e6, 1e3)
        assert snap.compression_ratio == pytest.approx(1000.0)

    def test_info_loss(self):
        snap = CompressionLossKSnap("k", "a", 1e6, 1e3)
        assert snap.info_loss_bits == pytest.approx(999000.0)

    def test_compute_fingerprint(self):
        snap = CompressionLossKSnap("k", "a", 1e6, 1e3)
        fp = snap.compute_fingerprint(b"discarded_data")
        assert fp == hashlib.sha256(b"discarded_data").hexdigest()
        assert len(fp) == 64

    def test_verify_fingerprint_correct(self):
        snap = CompressionLossKSnap("k", "a", 1e6, 1e3)
        snap.compute_fingerprint(b"test_data")
        assert snap.verify_fingerprint(b"test_data") is True

    def test_verify_fingerprint_incorrect(self):
        snap = CompressionLossKSnap("k", "a", 1e6, 1e3)
        snap.compute_fingerprint(b"test_data")
        assert snap.verify_fingerprint(b"wrong_data") is False

    def test_to_log(self):
        snap = CompressionLossKSnap(
            "k", "Cognitive_Compression", 9.7e8, 5200,
            psi_anchor_applied="psi_test",
        )
        snap.compute_fingerprint(b"modes")
        log = snap.to_log()
        assert "κ-Snap" in log
        assert "Cognitive_Compression" in log
        assert "SHA256" in log
        assert "Compression_Ratio" in log


class TestCognitiveCompressionEmbedding:
    """测试认知压缩嵌入定理"""

    def _make_wm(self):
        wm = WMHyperedgePDE(scene="test", pde_source="RD")
        wm.add_conservation_law(PDEConservationLaw(ConservationType.MASS, "m=0", ["m"]))
        return wm

    def _make_network(self):
        net = ENTBioNetwork("net", "tumor")
        net.add_edge("A", "upregulates", "B")
        return net

    def test_embed_pde(self):
        wm = self._make_wm()
        snap = CognitiveCompressionEmbedding.embed_pde_compression(wm, 1e9)
        assert snap.action.startswith("Cognitive_Compression(PDE")
        assert snap.compression_ratio > 1
        assert len(snap.discarded_mode_fingerprint) == 64

    def test_embed_ent(self):
        net = self._make_network()
        snap = CognitiveCompressionEmbedding.embed_ent_compression(net, 5e8)
        assert snap.action.startswith("Cognitive_Compression(ENT")
        assert snap.compression_ratio > 1

    def test_embed_physics_ai(self):
        wm = self._make_wm()
        engine = PhysicalAIEngine(pde_hyperedge=wm, kappa=1.0)
        snap = CognitiveCompressionEmbedding.embed_physics_ai_compression(engine, 8e8)
        assert snap.action.startswith("Cognitive_Compression(PhysAI")

    def test_verify_embedding(self):
        wm = self._make_wm()
        snap = CognitiveCompressionEmbedding.embed_pde_compression(wm, 1e9)
        result = CognitiveCompressionEmbedding.verify_embedding(snap, wm=wm)
        assert result["theorem_holds"] is True
        assert result["fingerprint_computed"] is True


class TestCognitiveCompressionPredictions:
    """测试可证伪预言 P14-P16"""

    def test_p14_pass(self):
        """P14: 肿瘤免疫数字孪生预测"""
        wm = WMHyperedgePDE(scene="tumor", pde_source="RD")
        wm.add_conservation_law(PDEConservationLaw(ConservationType.MASS, "m=0", ["m"]))
        engine = PhysicalAIEngine(pde_hyperedge=wm, kappa=1.0)
        cv = CognitiveCompressionValidator()
        result = cv.validate_p14_tumor_immune(
            engine,
            pde_state={"cd8_infiltration": 0.30},
            data_obs={"cd8_infiltration": 0.32},
            ground_truth=0.31,
        )
        assert result["prediction"] == "P14"
        assert result["passed"] is True

    def test_p15_intercept(self):
        """P15: ψ-锚拦截质量不守恒"""
        wm = WMHyperedgePDE(scene="tumor", pde_source="RD")
        wm.add_conservation_law(PDEConservationLaw(
            ConservationType.MASS, "m=0", ["m"]))
        cv = CognitiveCompressionValidator()
        result = cv.validate_p15_psi_anchor_intercept(
            wm,
            {"m": 100.0},
            {"m": 90.0},  # 10% mass loss
        )
        assert result["prediction"] == "P15"
        assert result["intercepted"] is True
        assert result["passed"] is True

    def test_p15_no_violation(self):
        """P15: 质量守恒时不触发"""
        wm = WMHyperedgePDE(scene="tumor", pde_source="RD")
        wm.add_conservation_law(PDEConservationLaw(
            ConservationType.MASS, "m=0", ["m"]))
        cv = CognitiveCompressionValidator()
        result = cv.validate_p15_psi_anchor_intercept(
            wm, {"m": 100.0}, {"m": 100.0},
        )
        assert result["passed"] is True
        assert result["intercepted"] is False

    def test_p16_fingerprint_match(self):
        """P16: κ-Snap 指纹匹配"""
        snap = CompressionLossKSnap("k", "a", 1e6, 1e3)
        snap.compute_fingerprint(b"discarded_modes")
        cv = CognitiveCompressionValidator()
        result = cv.validate_p16_ksnap_fingerprint(snap, b"discarded_modes")
        assert result["prediction"] == "P16"
        assert result["fingerprint_matches"] is True
        assert result["passed"] is True

    def test_p16_fingerprint_mismatch(self):
        """P16: 修改数据后指纹不匹配"""
        snap = CompressionLossKSnap("k", "a", 1e6, 1e3)
        snap.compute_fingerprint(b"original_modes")
        cv = CognitiveCompressionValidator()
        # 传原始数据 — 指纹应匹配, 修改数据后不匹配
        result = cv.validate_p16_ksnap_fingerprint(snap, b"original_modes")
        assert result["fingerprint_matches"] is True
        assert result["fingerprint_unchanged_on_modified"] is False  # 修改数据后指纹不同
        assert result["passed"] is True  # 指纹正确区分原始与修改数据


# ══════════════════════════════════════════════════════════════════
#  跨模块集成测试
# ══════════════════════════════════════════════════════════════════

class TestCrossModuleIntegration:
    """跨模块集成测试 — GaussEx × Cognitive Compression"""

    def test_gaussex_as_data_source_for_physics_ai(self):
        """GaussEx 系统作为物理AI引擎的数据源"""
        # PDE 超边
        wm = WMHyperedgePDE(scene="auto_drive", pde_source="vehicle_dynamics")
        wm.add_conservation_law(PDEConservationLaw(
            ConservationType.MOMENTUM, "p = mv", ["p", "m", "v"]))

        # GaussEx 观测系统 (含噪电阻 = 传感器)
        nr = NoisyResistor(resistance=10.0, noise_variance=0.04)

        # 物理AI引擎
        engine = PhysicalAIEngine(pde_hyperedge=wm, kappa=2.0)

        # 执行一步
        result = engine.step(
            dt=0.01,
            pde_state={"v": 5.0, "p": 50.0},
            data_obs={"v": nr.solve_current(5.0)[0], "p": 48.0},
        )
        assert result["ksnap_committed"] is True
        assert "v" in result["coupled_state"]

    def test_copartial_risk_with_pde_conservation(self):
        """共偏性风控 + PDE 守恒律"""
        # 银行系统带有守恒律约束
        bank = GaussExSystem(
            Fibre("bank", FibreType.CONSERVATION, "assets == liabilities + equity",
                  ["assets", "liabilities", "equity"]),
            GaussianNoise(0.8, 0.1, NoiseType.MARKET),
            IndustryDomain.FINTECH,
        )
        eco = GaussExSystem(
            Fibre("eco", FibreType.BUSINESS_RULE, "freq > 10", ["freq"]),
            GaussianNoise(0.6, 0.15, NoiseType.MARKET),
            IndustryDomain.FINTECH,
        )
        rc = CopartialRiskControl(bank, eco)
        result = rc.joint_risk_assessment()
        assert result["raw_data_exposed"] is False

    def test_full_pipeline(self):
        """完整流水线: PDE → GaussEx → 物理AI → κ-Snap"""
        # 1. PDE 守恒律
        wm = WMHyperedgePDE(scene="industrial", pde_source="heat_eq")
        wm.add_conservation_law(PDEConservationLaw(
            ConservationType.ENERGY, "E = 0", ["E"]))

        # 2. GaussEx 系统 (传感器)
        sensor = GaussExSystem(
            Fibre("sensor", FibreType.PHYSICS_LAW, "T < 100", ["T"]),
            GaussianNoise(85.0, 4.0, NoiseType.THERMAL),
            IndustryDomain.INDUSTRIAL_TWIN,
        )

        # 3. 物理AI引擎
        engine = PhysicalAIEngine(pde_hyperedge=wm, kappa=1.0)

        # 4. 执行 + 记录
        result = engine.step(
            dt=0.1,
            pde_state={"E": 100.0, "T": 80.0},
            data_obs={"E": 98.0, "T": sensor.noise.sample()},
        )

        # 5. κ-Snap 压缩损失审计
        snap = CognitiveCompressionEmbedding.embed_physics_ai_compression(engine, 1e9)

        assert result["ksnap_committed"] is True
        assert snap.compression_ratio > 0
        assert len(snap.discarded_mode_fingerprint) == 64

    def test_mus_in_physics_ai_pipeline(self):
        """MUS 双存在物理AI流水线中"""
        wm = WMHyperedgePDE(scene="bio", pde_source="RD_bio")
        engine = PhysicalAIEngine(pde_hyperedge=wm, kappa=1.0)

        # 模拟冲突状态
        result = engine.step(
            dt=0.01,
            pde_state={"proliferate_signal": 0.8, "apoptose_signal": 0.7},
            data_obs={"proliferate_signal": 0.9, "apoptose_signal": 0.6},
        )
        assert result["endogenous_conflict"] is True

        # 创建 MUS 双存
        mus = MUSEndogenousConflict(
            mus_id="mus_test",
            entity_a={"signal": "Proliferate", "predicate": "Grow", "i_value": 0.85},
            entity_b={"signal": "Apoptose", "predicate": "Die", "i_value": 0.75},
        )
        assert mus.resolution == "PENDING"
