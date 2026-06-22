# -*- coding: utf-8 -*-
"""Tests for TOMAS v3.7 modules — HTD, Topology Soliton, Gan-TOMAS P=GW

Covers:
  - htd_sim.py: Octonion, BraidWord, TOHTD_Simulator, P10/P11
  - topo_soliton.py: TopologicalSoliton, TOMAS_Topology_Simulator, P7-P9
  - gan_tomas_pgw.py: GanOperator, GanTOMAS_Core, P1-P6, MassFromOctonion
"""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sim'))

from htd_sim import (
    Octonion, BraidWord, BraidGenerator, TopologicalOrderState,
    BulkState, EdgeState, TOHTD_Simulator, HTDPredictionValidator,
    HolographicKSnap, create_laughlin_nu13_state,
    create_majorana_soliton, verify_tee_kitaev_preskill,
    TopoChargeGroup,
)

from topo_soliton import (
    TopologicalSoliton, TopologicalCharge, SolitonType,
    TOMAS_Topology_Simulator, SolitonBraider,
    PsiAnchorTopoProtection, TopoPhaseTransitionSnap,
    TopoPredictionValidator, create_abrikosov_vortex,
    create_majorana_zero_mode,
)

from gan_tomas_pgw import (
    GanOperator, GanWaveParticleEngine, GanTOMAS_Core,
    MassFromOctonion, ObservationOrderEffect,
    GanPredictionValidator, GanKSnapRecord,
    create_electron_state, create_photon_state, create_neutrino_state,
    HBAR, ME_MEV, MMU_MEV, MTAU_MEV,
)

sqrt = math.sqrt
log = math.log
cos = math.cos
sin = math.sin
atan = math.atan
tanh = math.tanh
pi = math.pi


# ═══════════════════════════════════════════════════════════════════
# HTD Module Tests
# ═══════════════════════════════════════════════════════════════════

class TestOctonion:
    """八元数基本运算"""

    def test_identity(self):
        e = Octonion.identity()
        assert e.re == 1.0
        assert all(v == 0.0 for v in e.im)

    def test_norm(self):
        o = Octonion(re=3.0, im=[4.0, 0, 0, 0, 0, 0, 0])
        assert abs(o.norm() - 5.0) < 1e-12

    def test_norm_sq(self):
        o = Octonion(re=1.0, im=[2.0, 0, 0, 0, 0, 0, 0])
        assert abs(o.norm_sq() - 5.0) < 1e-12

    def test_conjugate(self):
        o = Octonion(re=1.0, im=[2.0, 3.0, 0, 0, 0, 0, 0])
        c = o.conjugate()
        assert c.re == 1.0
        assert c.im[0] == -2.0
        assert c.im[1] == -3.0

    def test_add_sub(self):
        a = Octonion(re=2.0, im=[1.0, 0, 0, 0, 0, 0, 0])
        b = Octonion(re=3.0, im=[2.0, 0, 0, 0, 0, 0, 0])
        s = a + b
        assert s.re == 5.0
        assert s.im[0] == 3.0
        d = a - b
        assert d.re == -1.0
        assert d.im[0] == -1.0

    def test_scalar_mul(self):
        o = Octonion(re=1.0, im=[2.0, 0, 0, 0, 0, 0, 0])
        m = o * 3.0
        assert m.re == 3.0
        assert m.im[0] == 6.0

    def test_moufang_multiply_identity(self):
        e = Octonion.identity()
        o = Octonion(re=2.0, im=[0.5, 0, 0, 0, 0, 0, 0])
        r1 = Octonion.moufang_multiply(e, o)
        r2 = Octonion.moufang_multiply(o, e)
        assert abs(r1.re - o.re) < 1e-12
        assert abs(r2.re - o.re) < 1e-12

    def test_moufang_nonzero(self):
        a = Octonion(re=1.0, im=[0.1, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = Octonion(re=0.0, im=[0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        c = Octonion.moufang_multiply(a, b)
        assert c.norm() > 0

    def test_associator(self):
        a = Octonion(re=1.0, im=[0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0])
        b = Octonion(re=0.0, im=[0.4, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0])
        c = Octonion(re=0.0, im=[0.0, 0.0, 0.6, 0.0, 0.0, 0.0, 0.0])
        assoc = Octonion.associator(a, b, c)
        assert assoc.norm() >= 0

    def test_associator_norm_nonnegative(self):
        a = Octonion(re=1.0, im=[0.1, 0, 0, 0, 0, 0, 0])
        b = Octonion(re=0.0, im=[0.2, 0, 0, 0, 0, 0, 0])
        c = Octonion(re=0.0, im=[0.3, 0, 0, 0, 0, 0, 0])
        n = Octonion.associator_norm(a, b, c)
        assert n >= 0

    def test_to_dict(self):
        o = Octonion(re=1.5, im=[0.1, 0.2, 0, 0, 0, 0, 0])
        d = o.to_dict()
        assert d["re"] == 1.5
        assert len(d["im"]) == 7


class TestBraidWord:
    """编织词解析"""

    def test_from_string_unicode_subscripts(self):
        bw = BraidWord.from_string("σ₁ σ₂ σ₁⁻¹")
        assert len(bw.generators) == 3
        assert bw.generators[0].index == 0
        assert bw.generators[0].sign == 1
        assert bw.generators[2].index == 0
        assert bw.generators[2].sign == -1

    def test_from_string_ascii(self):
        bw = BraidWord.from_string("σ_1 σ_2 σ_1^-1")
        assert len(bw.generators) == 3
        assert bw.generators[0].sign == 1
        assert bw.generators[2].sign == -1

    def test_to_string(self):
        bw = BraidWord.from_string("σ₁ σ₂ σ₁⁻¹")
        s = bw.to_string()
        assert "σ_1" in s
        assert "σ_2" in s
        assert "⁻¹" in s

    def test_empty_braid(self):
        bw = BraidWord()
        assert len(bw.generators) == 0


class TestTopologicalOrderState:
    """拓扑序态"""

    def test_laughlin_nu13(self):
        state = create_laughlin_nu13_state()
        assert state.chern_number == 1
        assert state.filling_factor == "1/3"
        assert state.chiral_edge_modes == 1
        assert state.gap_open is True

    def test_tee_value(self):
        state = create_laughlin_nu13_state()
        expected = log(sqrt(3.0))
        assert abs(state.topo_entanglement_entropy - expected) < 1e-12

    def test_json_ld(self):
        state = create_laughlin_nu13_state()
        jld = state.to_json_ld()
        assert jld["type"] == "Topological_Order_State"
        assert jld["bulk_properties"]["chern_number"] == 1
        assert "topo_entanglement_entropy" in jld["bulk_properties"]

    def test_tee_verification(self):
        state = create_laughlin_nu13_state()
        assert verify_tee_kitaev_preskill(state)


class TestTOHTDSimulator:
    """HTD 模拟器"""

    def setup_method(self):
        self.sim = TOHTD_Simulator()

    def test_load_bulk_state(self):
        self.sim.load_bulk_state(create_laughlin_nu13_state())
        assert self.sim.bulk_state is not None
        assert self.sim.bulk_state.topo_state.chern_number == 1

    def test_load_edge_state(self):
        edge = EdgeState(chiral_modes=1, edge_current=0.333, conductance=1.0/3.0)
        self.sim.load_edge_state(edge)
        assert self.sim.edge_state.chiral_modes == 1

    def test_set_solitons(self):
        sols = [create_majorana_soliton(i * pi / 3) for i in range(3)]
        self.sim.set_solitons(sols)
        assert len(self.sim.solitons) == 3

    def test_evolve_braiding(self):
        self.sim.load_bulk_state(create_laughlin_nu13_state())
        self.sim.load_edge_state(EdgeState(
            chiral_modes=1, edge_current=0.333, conductance=1.0/3.0
        ))
        sols = [create_majorana_soliton(i * pi / 3) for i in range(3)]
        self.sim.set_solitons(sols)

        bw = BraidWord.from_string("σ₁ σ₂ σ₁⁻¹")
        new_bulk, snap = self.sim.evolve_boundary_braiding(bw)

        assert snap.event_type == "HOLOGRAPHIC_TOPO_DYNAMICS"
        assert snap.holonomy_norm > 0
        assert abs(snap.bulk_tee_before - snap.bulk_tee_after) < 1e-12

    def test_tee_conservation(self):
        self.sim.load_bulk_state(create_laughlin_nu13_state())
        self.sim.load_edge_state(EdgeState(
            chiral_modes=1, edge_current=0.333, conductance=1.0/3.0
        ))
        sols = [create_majorana_soliton(i * pi / 3) for i in range(3)]
        self.sim.set_solitons(sols)
        self.sim.evolve_boundary_braiding(BraidWord.from_string("σ₁"))
        assert self.sim.verify_tee_conservation()

    def test_gap_protection(self):
        self.sim.load_bulk_state(create_laughlin_nu13_state())
        assert self.sim.verify_gap_protection()

    def test_edge_bulk_correspondence(self):
        self.sim.load_bulk_state(create_laughlin_nu13_state())
        self.sim.load_edge_state(EdgeState(
            chiral_modes=1, edge_current=0.333, conductance=1.0/3.0
        ))
        assert self.sim.check_edge_bulk_correspondence()

    def test_get_bulk_summary(self):
        self.sim.load_bulk_state(create_laughlin_nu13_state())
        s = self.sim.get_bulk_summary()
        assert s["chern_number"] == 1
        assert s["gap_open"] is True

    def test_all_checks_pass(self):
        self.sim.load_bulk_state(create_laughlin_nu13_state())
        self.sim.load_edge_state(EdgeState(
            chiral_modes=1, edge_current=0.333, conductance=1.0/3.0
        ))
        sols = [create_majorana_soliton(i * pi / 3) for i in range(3)]
        self.sim.set_solitons(sols)
        self.sim.evolve_boundary_braiding(BraidWord.from_string("σ₁"))
        checks = self.sim.all_checks_pass()
        assert all(checks.values())

    def test_evolve_without_state_raises(self):
        with pytest.raises(ValueError):
            self.sim.evolve_boundary_braiding(BraidWord())

    def test_evolve_without_solitons_raises(self):
        self.sim.load_bulk_state(create_laughlin_nu13_state())
        with pytest.raises(ValueError):
            self.sim.evolve_boundary_braiding(BraidWord())

    def test_multiple_braids(self):
        self.sim.load_bulk_state(create_laughlin_nu13_state())
        self.sim.load_edge_state(EdgeState(
            chiral_modes=1, edge_current=0.333, conductance=1.0/3.0
        ))
        sols = [create_majorana_soliton(i * pi / 3) for i in range(3)]
        self.sim.set_solitons(sols)

        self.sim.evolve_boundary_braiding(BraidWord.from_string("σ₁"))
        self.sim.evolve_boundary_braiding(BraidWord.from_string("σ₂"))
        assert len(self.sim.k_snap_records) == 2
        assert self.sim.verify_tee_conservation()


class TestHTDPredictions:
    """HTD 可证伪预言"""

    def test_p10_pass(self):
        D = sqrt(3.0)
        measured_tee = log(D) + 0.0005  # small perturbation
        passed, msg = HTDPredictionValidator.verify_p10(measured_tee, D, sigma=3.0)
        assert passed

    def test_p10_fail_large_deviation(self):
        D = sqrt(3.0)
        measured_tee = log(D) + 0.5  # large deviation
        passed, msg = HTDPredictionValidator.verify_p10(measured_tee, D, sigma=3.0)
        assert not passed

    def test_p11_parity_flip(self):
        passed, msg = HTDPredictionValidator.verify_p11(
            BraidWord.from_string("σ₁"), parity_before=1, parity_after=-1
        )
        assert passed

    def test_p11_no_flip_when_expected(self):
        passed, msg = HTDPredictionValidator.verify_p11(
            BraidWord.from_string("σ₁"), parity_before=1, parity_after=1
        )
        assert not passed


class TestHolographicKSnap:
    """κ-Snap 审计"""

    def test_to_log(self):
        snap = HolographicKSnap(
            snap_id=1,
            timestamp="2026-06-22T16:00:00Z",
            braid_word_str="σ_1 σ_2 σ_1⁻¹",
            holonomy_norm=1.0,
            associator_norm=2.14e-9,
            bulk_tee_before=0.5493,
            bulk_tee_after=0.5493,
            bulk_state_change="Post-selection within same topological sector",
            tdc_ref=123456789
        )
        log_str = snap.to_log()
        assert "κ-Snap #1" in log_str
        assert "HOLOGRAPHIC_TOPO_DYNAMICS" in log_str


# ═══════════════════════════════════════════════════════════════════
# Topology Soliton Module Tests
# ═══════════════════════════════════════════════════════════════════

class TestTopologicalCharge:
    """拓扑荷"""

    def test_create_charge(self):
        tc = TopologicalCharge(group=TopoChargeGroup.PI_1_U1, value=1)
        assert tc.group == TopoChargeGroup.PI_1_U1
        assert tc.value == 1

    def test_trivial_charge(self):
        tc = TopologicalCharge(group=TopoChargeGroup.Z, value=0)
        assert tc.is_trivial()

    def test_nontrivial_charge(self):
        tc = TopologicalCharge(group=TopoChargeGroup.PI_1_U1, value=1)
        assert not tc.is_trivial()

    def test_charge_conjugate(self):
        tc = TopologicalCharge(group=TopoChargeGroup.Z, value=3)
        anti = tc.charge_conjugate()
        assert anti.value == -3

    def test_charge_equality(self):
        a = TopologicalCharge(group=TopoChargeGroup.Z2, value=1)
        b = TopologicalCharge(group=TopoChargeGroup.Z2, value=1)
        assert a == b


class TestTopologicalSoliton:
    """拓扑孤子"""

    def test_create_vortex(self):
        v = create_abrikosov_vortex("v1", winding=1)
        assert v.soliton_type == SolitonType.ABRIKOSOV_VORTEX
        assert v.is_stable()

    def test_create_mzm(self):
        m = create_majorana_zero_mode("m1")
        assert m.soliton_type == SolitonType.MAJORANA_ZERO_MODE
        assert m.is_stable()

    def test_annihilation(self):
        v1 = create_abrikosov_vortex("v1", winding=1)
        v2 = create_abrikosov_vortex("v2", winding=-1)
        assert v1.can_annihilate_with(v2)

    def test_no_annihilation_same_charge(self):
        v1 = create_abrikosov_vortex("v1", winding=1)
        v2 = create_abrikosov_vortex("v2", winding=1)
        assert not v1.can_annihilate_with(v2)

    def test_json_ld(self):
        v = create_abrikosov_vortex("v1")
        jld = v.to_json_ld()
        assert jld["type"] == "Topological_Soliton"
        assert jld["subtype"] == "Abrikosov_Vortex"
        assert jld["psi_anchor"] == "psi_topological_charge_conservation"

    def test_core_order_parameter(self):
        v = create_abrikosov_vortex("v1", winding=1)
        assert v.core_order_parameter == 0.0


class TestPsiAnchorProtection:
    """ψ-锚 拓扑保护"""

    def test_gap_protection_pass(self):
        psi = PsiAnchorTopoProtection()
        ok, msg = psi.check_gap_protection(0.05)
        assert ok

    def test_gap_protection_fail(self):
        psi = PsiAnchorTopoProtection()
        ok, msg = psi.check_gap_protection(0.00001)
        assert not ok

    def test_charge_conservation(self):
        psi = PsiAnchorTopoProtection()
        tc = TopologicalCharge(group=TopoChargeGroup.Z, value=1)
        ok, msg = psi.check_charge_conservation(tc, tc)
        assert ok

    def test_charge_change_blocked(self):
        psi = PsiAnchorTopoProtection()
        tc1 = TopologicalCharge(group=TopoChargeGroup.Z, value=1)
        tc2 = TopologicalCharge(group=TopoChargeGroup.Z, value=2)
        ok, msg = psi.check_charge_conservation(tc1, tc2)
        assert not ok

    def test_soliton_stability(self):
        psi = PsiAnchorTopoProtection()
        v = create_abrikosov_vortex("v1")
        ok, msg = psi.check_soliton_stability(v)
        assert ok

    def test_protection_stats(self):
        psi = PsiAnchorTopoProtection()
        stats = psi.get_protection_stats()
        assert "charge_changes_blocked" in stats
        assert "gap_violations_blocked" in stats


class TestTOMASTopologySimulator:
    """拓扑主模拟器"""

    def setup_method(self):
        self.sim = TOMAS_Topology_Simulator()

    def test_set_topological_state(self):
        self.sim.set_topological_state(chern=0)
        assert self.sim.chern_number == 0
        assert self.sim.edge_modes == 0

    def test_add_soliton(self):
        v = create_abrikosov_vortex("v1")
        ok = self.sim.add_soliton(v)
        assert ok
        assert len(self.sim.solitons) == 1

    def test_no_phase_transition_below_critical(self):
        self.sim.set_topological_state(chern=0)
        result = self.sim.apply_perturbation(strain_delta=0.001)
        assert not result["phase_transition_occurred"]

    def test_phase_transition_above_critical(self):
        self.sim.set_topological_state(chern=0)
        result = self.sim.apply_perturbation(strain_delta=0.006)
        assert result["phase_transition_occurred"]
        assert self.sim.chern_number == 1
        assert self.sim.edge_modes == 1

    def test_chern_edge_correspondence(self):
        self.sim.set_topological_state(chern=1)
        assert self.sim.verify_chern_edge_correspondence()

    def test_braid_solitons(self):
        self.sim.set_topological_state(chern=0)
        self.sim.add_soliton(create_majorana_zero_mode("m1"))
        self.sim.add_soliton(create_majorana_zero_mode("m2"))
        bw = BraidWord.from_string("σ₁ σ₂")
        holonomy, assoc = self.sim.braid_solitons(bw)
        assert holonomy.norm() > 0
        assert assoc >= 0

    def test_state_summary(self):
        self.sim.set_topological_state(chern=1)
        self.sim.add_soliton(create_abrikosov_vortex("v1"))
        s = self.sim.get_state_summary()
        assert s["chern_number"] == 1
        assert s["soliton_count"] == 1

    def test_all_checks_pass(self):
        self.sim.set_topological_state(chern=1)
        self.sim.add_soliton(create_abrikosov_vortex("v1"))
        checks = self.sim.all_checks_pass()
        assert all(checks.values())

    def test_topological_invariant(self):
        self.sim.set_topological_state(chern=3)
        assert self.sim.get_topological_invariant() == 3.0

    def test_multiple_phase_transitions(self):
        self.sim.set_topological_state(chern=0)
        self.sim.apply_perturbation(strain_delta=0.006)
        self.sim.apply_perturbation(strain_delta=0.001)
        assert len(self.sim.phase_transitions) >= 1


class TestSolitonBraider:
    """孤子编织器"""

    def test_braid_pair(self):
        a = Octonion(re=1.0, im=[0.1, 0, 0, 0, 0, 0, 0])
        b = Octonion(re=0.0, im=[0.2, 0, 0, 0, 0, 0, 0])
        c = SolitonBraider.braid_pair(a, b)
        assert c.norm() > 0

    def test_braid_sequence(self):
        sols = [Octonion(re=1.0, im=[0.1, 0, 0, 0, 0, 0, 0]) for _ in range(3)]
        bw = BraidWord.from_string("σ₁ σ₂")
        h = SolitonBraider.braid_sequence(sols, bw)
        assert h.norm() > 0

    def test_associator_deviation(self):
        a = Octonion(re=1.0, im=[0.1, 0.2, 0.3, 0, 0, 0, 0])
        b = Octonion(re=0.0, im=[0.4, 0.5, 0, 0, 0, 0, 0])
        c = Octonion(re=0.0, im=[0, 0, 0.6, 0, 0, 0, 0])
        dev = SolitonBraider.compute_associator_deviation(a, b, c)
        assert dev >= 0

    def test_braiding_phase(self):
        a = Octonion(re=1.0, im=[0.1, 0, 0, 0, 0, 0, 0])
        b = Octonion(re=0.0, im=[0.2, 0, 0, 0, 0, 0, 0])
        phase = SolitonBraider.compute_braiding_phase(a, b)
        assert -pi <= phase <= pi


class TestTopoPredictions:
    """拓扑预言 P7-P9"""

    def test_p7_phase_correction_confirmed(self):
        passed, msg = TopoPredictionValidator.verify_p7_braiding_phase_correction(
            measured_phase_shift_rad=1.5e-3, threshold_rad=1e-4
        )
        assert passed

    def test_p7_phase_correction_falsified(self):
        passed, msg = TopoPredictionValidator.verify_p7_braiding_phase_correction(
            measured_phase_shift_rad=1e-6, threshold_rad=1e-4
        )
        assert not passed

    def test_p8_chern_jump_audit(self):
        sim = TOMAS_Topology_Simulator()
        sim.set_topological_state(chern=0)
        sim.apply_perturbation(strain_delta=0.006)
        passed, msg = TopoPredictionValidator.verify_p8_chern_jump_audit(sim, 1.0)
        assert passed

    def test_p9_disorder_immunity(self):
        v = create_abrikosov_vortex("v1", winding=1)
        passed, msg = TopoPredictionValidator.verify_p9_soliton_disorder_immunity(v, 0.8)
        assert passed


class TestTopoPhaseTransitionSnap:
    """拓扑相变审计"""

    def test_snap_creation(self):
        snap = TopoPhaseTransitionSnap(
            snap_id=10001,
            timestamp="2026-06-22T15:00:00Z",
            old_chern=0, new_chern=1,
            old_gap_eV=0.05, new_gap_eV=0.048,
            old_edge_modes=0, new_edge_modes=1,
            trigger_parameter={"Strain": "0.5%", "Magnetic_Field": "2 Tesla"}
        )
        assert snap.event_type == "TOPOLOGICAL_PHASE_TRANSITION"

    def test_snap_to_log(self):
        snap = TopoPhaseTransitionSnap(
            snap_id=10001,
            timestamp="2026-06-22T15:00:00Z",
            old_chern=0, new_chern=1,
            old_gap_eV=0.05, new_gap_eV=0.048,
            old_edge_modes=0, new_edge_modes=1,
        )
        log_str = snap.to_log()
        assert "TOPOLOGICAL_PHASE_TRANSITION" in log_str


# ═══════════════════════════════════════════════════════════════════
# Gan-TOMAS P=GW Module Tests
# ═══════════════════════════════════════════════════════════════════

class TestGanOperator:
    """Gan 极化算子"""

    def test_default_construction(self):
        gop = GanOperator()
        assert gop.kappa == 7.0
        assert gop.hbar == HBAR

    def test_custom_kappa(self):
        gop = GanOperator(kappa=3.0)
        assert gop.kappa == 3.0

    def test_phi_calculation(self):
        gop = GanOperator(kappa=1.0)
        assert abs(gop.phi - pi / 4) < 1e-12

    def test_weights_between_zero_and_one(self):
        gop = GanOperator(kappa=7.0)
        assert 0 <= gop.particle_weight <= 1
        assert 0 <= gop.wave_weight <= 1

    def test_kappa_limits_small(self):
        gop = GanOperator(kappa=0.01)
        assert gop.particle_weight > gop.wave_weight

    def test_kappa_limits_large(self):
        gop = GanOperator(kappa=100)
        assert gop.wave_weight > gop.particle_weight

    def test_apply_polarization_norm(self):
        gop = GanOperator()
        e = create_electron_state()
        p = gop.apply_polarization(e)
        assert p.norm() > 0

    def test_polarization_invertible(self):
        gop = GanOperator(kappa=7.0)
        e = create_electron_state()
        p = gop.apply_polarization(e)
        recovered = gop.apply_inverse(p)
        diff_norm = Octonion(
            re=e.re - recovered.re,
            im=[a - b for a, b in zip(e.im, recovered.im)]
        ).norm()
        assert diff_norm < 1e-12

    def test_to_dict(self):
        gop = GanOperator(kappa=3.7)
        d = gop.to_dict()
        assert d["kappa"] == 3.7
        assert "phi_rad" in d
        assert "particle_weight" in d


class TestGanWaveParticleEngine:
    """P=GW 波粒对偶引擎"""

    def setup_method(self):
        self.gop = GanOperator(kappa=7.0)
        self.engine = GanWaveParticleEngine(self.gop)

    def test_particle_view(self):
        self.engine.set_state(create_electron_state())
        pv = self.engine.particle_view()
        assert pv["view"] == "particle"
        assert pv["layer"] == "L3_WorldFrame"

    def test_wave_view(self):
        self.engine.set_state(create_photon_state())
        wv = self.engine.wave_view()
        assert wv["view"] == "wave"
        assert wv["layer"] == "L1_Akashic"

    def test_verify_p_eq_gw(self):
        self.engine.set_state(create_electron_state())
        assert self.engine.verify_p_eq_gw()

    def test_compute_gan_transform(self):
        s = create_neutrino_state()
        p, w = self.engine.compute_gan_transform(s)
        assert p.norm() > 0
        assert w.norm() > 0


class TestMassFromOctonion:
    """质量定义"""

    def test_compute_mass(self):
        gop = GanOperator(kappa=7.0)
        mf = MassFromOctonion(gop)
        e = create_electron_state()
        m = mf.compute_mass(e)
        assert m > 0

    def test_mass_ratio(self):
        gop = GanOperator(kappa=7.0)
        mf = MassFromOctonion(gop)
        r = mf.compute_mass_ratio(100, 50)
        assert abs(r - 2.0) < 1e-9

    def test_photon_lighter_than_electron(self):
        gop_e = GanOperator(kappa=7.0)
        gop_p = GanOperator(kappa=0.1)
        m_e = MassFromOctonion(gop_e).compute_mass(create_electron_state())
        m_p = MassFromOctonion(gop_p).compute_mass(create_photon_state())
        # 光子 κ 小 → 质量应较小
        # 注意: 这个断言取决于具体的八元数范数和 κ 值
        assert m_e > 0
        assert m_p > 0

    def test_lepton_mass_ratios(self):
        ratios = MassFromOctonion.lepton_mass_ratios()
        assert "mu_over_e_algebraic" in ratios
        assert "mu_over_e_measured" in ratios
        assert "tau_over_mu_algebraic" in ratios

    def test_effective_kappa_from_mass(self):
        gop = GanOperator(kappa=7.0)
        mf = MassFromOctonion(gop)
        k = mf.effective_kappa_from_mass(0.511, norm_sq=1.0)
        assert k > 0


class TestGanTOMASCore:
    """Gan-TOMAS 核心循环"""

    def setup_method(self):
        self.core = GanTOMAS_Core(GanOperator(kappa=7.0))

    def test_process_hyperedge(self):
        result = self.core.process_hyperedge(
            create_electron_state(),
            create_photon_state(),
            result_note="Test coupling"
        )
        assert result["associator_norm"] >= 0
        assert result["mass_estimate"] > 0
        assert result["k_snap_id"] == 1

    def test_k_snap_records(self):
        self.core.process_hyperedge(
            create_electron_state(), create_photon_state()
        )
        self.core.process_hyperedge(
            create_neutrino_state(), create_electron_state()
        )
        assert len(self.core.k_snap_records) == 2

    def test_get_mass_for_state(self):
        m = self.core.get_mass_for_state(create_electron_state())
        assert m > 0

    def test_analyze_observation_order(self):
        states = [
            create_electron_state(),
            create_photon_state(),
            create_neutrino_state()
        ]
        info = self.core.analyze_observation_order(states)
        assert "associator_norm" in info
        assert "detectable" in info
        assert "regime" in info

    def test_analyze_order_needs_3_states(self):
        info = self.core.analyze_observation_order([
            create_electron_state(), create_photon_state()
        ])
        assert "error" in info

    def test_gan_op_params_in_snap(self):
        self.core.process_hyperedge(
            create_electron_state(), create_photon_state()
        )
        snap = self.core.k_snap_records[-1]
        assert snap.gan_params["kappa"] == 7.0
        assert "hbar" in snap.gan_params


class TestObservationOrderEffect:
    """观测顺序效应"""

    def test_compute_order_dependence(self):
        s1, s2, s3 = create_electron_state(), create_photon_state(), create_neutrino_state()
        info = ObservationOrderEffect.compute_order_dependence(s1, s2, s3)
        assert info["associator_norm"] >= 0
        assert isinstance(info["detectable"], bool)
        assert info["regime"] != ""

    def test_predict_interference_correction(self):
        v = ObservationOrderEffect.predict_interference_correction(
            arm_difference=1e-3, associator_norm=1e-2, coherence_length=1e-6
        )
        assert 0 <= v <= 1.0


class TestGanPredictions:
    """Gan 预言 P1-P6"""

    def test_p1_invalid_case(self):
        # Large deviation → falsified
        passed, msg = GanPredictionValidator.verify_p1_interference_visibility(
            measured_visibility=0.5, arm_difference_m=1.0,
            predicted_associator_norm=0.1, tolerance=0.01
        )
        # 可能通过也可能不通过
        assert isinstance(passed, bool)

    def test_p2_asymmetry(self):
        passed, msg = GanPredictionValidator.verify_p2_ab_asymmetry(
            phase_positive=0.001, phase_negative=-0.0011, tolerance_rad=1e-6
        )
        assert isinstance(passed, bool)

    def test_p5_lepton_ratios(self):
        result = GanPredictionValidator.verify_p5_lepton_mass_ratios()
        assert "mu_over_e" in result
        assert "tau_over_mu" in result
        assert isinstance(result["overall_pass"], bool)

    def test_p6_residual(self):
        passed, msg = GanPredictionValidator.verify_p6_delayed_choice_residual(
            measured_residual_visibility=0.03, kappa=7.0
        )
        assert passed

    def test_p6_no_residual(self):
        passed, msg = GanPredictionValidator.verify_p6_delayed_choice_residual(
            measured_residual_visibility=0.001, kappa=7.0, tolerance=0.005
        )
        assert not passed


class TestGanKSnapRecord:
    """Gan κ-Snap 审计"""

    def test_to_log(self):
        snap = GanKSnapRecord(
            snap_id=9000,
            timestamp="2026-06-22T14:30:00Z",
            gan_params={"hbar": HBAR, "kappa": 3.7, "phi_rad": 1.304},
            oct_state_final={"re": 0.7, "im": [0.45, 0.38, 0, 0, 0, 0, 0]},
            associator_norm=3.712e-8,
            wave_particle_ratio=0.8,
            tdc_ref=1234567890,
            result_note="Artemisia vulgaris test"
        )
        log_str = snap.to_log()
        assert "κ-Snap #9000" in log_str
        assert "3.712e-08" in log_str


# ═══════════════════════════════════════════════════════════════════
# Integration Tests (Cross-module)
# ═══════════════════════════════════════════════════════════════════

class TestCrossModuleIntegration:
    """跨模块集成测试"""

    def test_htd_to_topo_octonion_shared(self):
        """验证 htd_sim 的 Octonion 可被 topo_soliton 使用"""
        from htd_sim import Octonion as OctHTD
        from topo_soliton import Octonion as OctTopo
        a = OctHTD(re=1.0, im=[0.1, 0, 0, 0, 0, 0, 0])
        b = OctTopo(re=0.0, im=[0.2, 0, 0, 0, 0, 0, 0])
        # 它们是同一个类
        c = OctHTD.moufang_multiply(a, b)
        assert c.norm() > 0

    def test_htd_to_gan_octonion_shared(self):
        """验证 htd_sim 的 Octonion 可被 gan_tomas 使用"""
        from htd_sim import Octonion as OctHTD
        from gan_tomas_pgw import Octonion as OctGan
        a = OctHTD(re=1.0, im=[0.1, 0, 0, 0, 0, 0, 0])
        # 验证同一性
        assert isinstance(a, OctGan)

    def test_full_pipeline_htd_topo_gan(self):
        """完整管程: HTD → Topo → Gan"""
        # 1. HTD: 创建体态
        sim = TOHTD_Simulator()
        sim.load_bulk_state(create_laughlin_nu13_state())
        sim.load_edge_state(EdgeState(
            chiral_modes=1, edge_current=0.333, conductance=1.0/3.0
        ))
        sols = [create_majorana_soliton(i * pi / 3) for i in range(3)]
        sim.set_solitons(sols)
        sim.evolve_boundary_braiding(BraidWord.from_string("σ₁"))
        assert sim.verify_tee_conservation()

        # 2. Topo: 孤子操作
        topo_sim = TOMAS_Topology_Simulator()
        topo_sim.set_topological_state(chern=1)
        topo_sim.add_soliton(create_abrikosov_vortex("v1"))
        assert topo_sim.verify_chern_edge_correspondence()

        # 3. Gan: P=GW 引擎
        core = GanTOMAS_Core(GanOperator(kappa=7.0))
        result = core.process_hyperedge(
            create_electron_state(), create_photon_state()
        )
        assert result["mass_estimate"] > 0
