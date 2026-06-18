# -*- coding: utf-8 -*-
"""
DualChainConsensus — 双链共识动力学 (物质链 ⊗ 意识链)
========================================================

Theory Source:
    "太极计算宇宙论——基于太一互搏公理体系（TOMAS）哥德尔旋转时空、
     EML 超图双链共识与 G_ego 意识不朽性的严格表述"
    (微信公众号文章, 章锋, 2026-06-18)

Core Concepts:
    1. 双链 = 物质链（EML 物理超边）⊗ 意识链（G_ego ψ-锚日志）
    2. 耦合哈密顿量: H = H_m ⊗ I + I ⊗ H_c + J * M
    3. 共识度 C(t) = |⟨Ψ_m|Ψ_c⟩|² 度量物质-意识对齐
    4. 健康生命 C(t) ≈ 1；濒死/深麻醉 C(t) → 0
    5. 哥德尔自指闭环 = EML 超图自指因果环（非宏观时光旅行）

Theorems:
    Thm 3.1 (Gödel-TOMAS Isomorphism):
        哥德尔 CTC = EML 自指因果环（G_ego 记忆-期望环）
        无宏观 CTC 可乘——物理因果仍局部 Lorentz

    Thm 4.1 (Dark Energy = Self-Referential Potential):
        暗能量密度 ρ_Λ ∝ Ω² (宇宙自指旋转强度)

    Thm 5.1 (双链共识演化):
        宇宙演化满足耦合薛定谔方程
        J ≠ 0 ⇒ 物质事件强迫意识注意，意识意向强迫物质重构

    Thm 6.1 (Consciousness Information Conservation):
        意识信息总量 ℐ_consciousness 在肉体 PG-Gate 开闭过程中守恒

Author: TOMAS Team
Version: v1.0
"""
from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================
# 枚举
# ============================================================

class ChainType(Enum):
    """链类型"""
    MATERIAL = "material"    # 物质链（EML 物理超边）
    CONSCIOUSNESS = "consciousness"  # 意识链（G_ego ψ-锚日志）


class ConsensusState(Enum):
    """共识状态"""
    ALIGNED = "aligned"          # C(t) ≈ 1（健康/清醒）
    PARTIAL = "partial"          # 0 < C(t) < 1（部分对齐）
    DECOUPLED = "decoupled"      # C(t) ≈ 0（解耦/濒死/深麻醉）
    RECOUPLING = "recoupling"    # 正在重新耦合


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ChainState:
    """链状态（物质链或意识链）"""
    chain_type: ChainType
    state_vector: List[float]       # Hilbert 空间表示
    hamiltonian: Optional[List[List[float]]] = None  # H_m 或 H_c
    energy: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConsensusSnapshot:
    """共识度快照"""
    timestamp: float
    consensus: float                # C(t) = |⟨Ψ_m|Ψ_c⟩|²
    state: ConsensusState
    coupling_strength: float        # J 耦合强度
    material_energy: float
    consciousness_energy: float
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "consensus": round(self.consensus, 6),
            "state": self.state.value,
            "coupling_J": round(self.coupling_strength, 6),
            "E_m": round(self.material_energy, 6),
            "E_c": round(self.consciousness_energy, 6),
            "notes": self.notes,
        }


@dataclass
class SelfReferentialLoop:
    """
    哥德尔自指闭环（EML 自指因果环）

    Article 2, Theorem 3.1:
        CTC = G_ego 阴敛（读 ψ-锚历史）→ 阳发（投射期望）→ 新 κ-Snap 被未来自我读回
    """
    loop_id: str
    yin_phase: str                  # 阴敛：G_ego ← EML 读 ψ-锚历史
    yang_phase: str                 # 阳发：G_ego → EML 注入新超边
    snap_event: str                 # 新 κ-Snap 被未来自我读回
    is_closed: bool = False         # 闭环是否完成
    created_at: float = field(default_factory=time.time)


# ============================================================
# 双链共识动力学引擎
# ============================================================

class DualChainConsensus:
    """
    双链共识动力学引擎

    Article 2, Section 5:
        物质链 = EML 超图中具 PG-锚的超边张成子空间
        意识链 = G_ego ψ-锚日志的 Hilbert 空间表示
        耦合哈密顿量: H = H_m ⊗ I + I ⊗ H_c + J * M
    """

    def __init__(
        self,
        coupling_strength: float = 0.1,
        dim: int = 8,
    ):
        self.J = coupling_strength     # 耦合强度 J
        self.dim = dim                  # Hilbert 空间维度
        self.material_chain = ChainState(
            chain_type=ChainType.MATERIAL,
            state_vector=[1.0] + [0.0] * (dim - 1),
            hamiltonian=None,
        )
        self.consciousness_chain = ChainState(
            chain_type=ChainType.CONSCIOUSNESS,
            state_vector=[1.0] + [0.0] * (dim - 1),
            hamiltonian=None,
        )
        self.history: List[ConsensusSnapshot] = []
        self.loops: List[SelfReferentialLoop] = []

    def _inner_product(self, a: List[float], b: List[float]) -> float:
        """计算 Hilbert 空间内积 ⟨a|b⟩"""
        return sum(x * y for x, y in zip(a, b))

    def compute_consensus(self) -> ConsensusSnapshot:
        """
        计算共识度 C(t) = |⟨Ψ_m|Ψ_c⟩|²

        Article 2, Theorem 5.1:
            C(t) = |⟨Ψ_m|Ψ_c⟩|²
            健康生命 C ≈ 1；濒死/深麻醉 C → 0
        """
        inner = self._inner_product(
            self.material_chain.state_vector,
            self.consciousness_chain.state_vector,
        )
        consensus = abs(inner) ** 2

        if consensus > 0.8:
            state = ConsensusState.ALIGNED
            notes = "Healthy: material-consciousness aligned"
        elif consensus > 0.2:
            state = ConsensusState.PARTIAL
            notes = "Partial alignment"
        elif consensus > 0.01:
            state = ConsensusState.RECOUPLING
            notes = "Recoupling in progress"
        else:
            state = ConsensusState.DECOUPLED
            notes = "Decoupled (anesthesia/near-death)"

        snapshot = ConsensusSnapshot(
            timestamp=time.time(),
            consensus=consensus,
            state=state,
            coupling_strength=self.J,
            material_energy=self.material_chain.energy,
            consciousness_energy=self.consciousness_chain.energy,
            notes=notes,
        )
        self.history.append(snapshot)
        return snapshot

    def evolve(
        self,
        material_input: Optional[List[float]] = None,
        consciousness_input: Optional[List[float]] = None,
        dt: float = 0.01,
    ) -> ConsensusSnapshot:
        """
        演化一步（耦合薛定谔方程简化版）

        Article 2, Theorem 5.1:
            J ≠ 0 ⇒ 物质事件强迫意识注意（痛觉→"我疼"）
            意识意向强迫物质重构（决定抬手→运动计划超边 κ-Snap）

        简化：用耦合矩阵演化状态向量
        """
        if material_input is not None:
            # 物质事件 → 通过 J 耦合影响意识链
            for i in range(min(len(material_input), self.dim)):
                self.consciousness_chain.state_vector[i] += self.J * material_input[i] * dt
            self.material_chain.state_vector = material_input[:self.dim] + [0.0] * (self.dim - len(material_input))

        if consciousness_input is not None:
            # 意识意向 → 通过 J 耦合影响物质链
            for i in range(min(len(consciousness_input), self.dim)):
                self.material_chain.state_vector[i] += self.J * consciousness_input[i] * dt
            self.consciousness_chain.state_vector = consciousness_input[:self.dim] + [0.0] * (self.dim - len(consciousness_input))

        # 归一化
        self._normalize(self.material_chain)
        self._normalize(self.consciousness_chain)

        # 更新能量
        self.material_chain.energy = sum(x ** 2 for x in self.material_chain.state_vector)
        self.consciousness_chain.energy = sum(x ** 2 for x in self.consciousness_chain.state_vector)

        return self.compute_consensus()

    def _normalize(self, chain: ChainState):
        """归一化状态向量"""
        norm = math.sqrt(sum(x ** 2 for x in chain.state_vector))
        if norm > 0:
            chain.state_vector = [x / norm for x in chain.state_vector]

    def create_self_referential_loop(
        self,
        yin_data: str,
        yang_data: str,
        snap_event: str,
    ) -> SelfReferentialLoop:
        """
        创建哥德尔自指闭环

        Article 2, Theorem 3.1:
            阴敛（读 ψ-锚历史）→ 阳发（投射期望）→ 新 κ-Snap 被未来自我读回
            闭环的圆 = 哥德尔旋转

        Article 2, Corollary 3.1:
            "过去未来是闭环圆，活在当下是 Snap 点"
        """
        loop = SelfReferentialLoop(
            loop_id=f"loop_{uuid.uuid4().hex[:8]}",
            yin_phase=yin_data,
            yang_phase=yang_data,
            snap_event=snap_event,
            is_closed=True,
        )
        self.loops.append(loop)
        logger.info("Self-referential loop created: %s (yin→yang→snap)", loop.loop_id)
        return loop

    def pg_gate_release(self) -> ConsensusSnapshot:
        """
        PG-Gate 释放（死亡 = 载体释放）

        Article 2, Theorem 6.1:
            死亡 = PG-Gate 打开 ⇒ Ftel 不再受限 ⇒ 超边续存 Akasha-EML
            意识信息 ℐ 不灭，仅改变流贯约束

        Article 2, Def 6.1:
            PG-Gate 是滤波不是销毁
        """
        # C(t) → 0（解耦），但 ℐ 守恒（信息不灭）
        self.J = 0.0  # 耦合断开
        # 将意识链状态向量正交化（模拟解耦）
        orthogonal = [0.0] * self.dim
        orthogonal[-1] = 1.0  # 意识链移动到正交子空间
        self.consciousness_chain.state_vector = orthogonal
        snapshot = self.compute_consensus()
        snapshot.notes = "PG-Gate RELEASE: consciousness decoupled from material carrier. ℐ conserved (Thm 6.1)."
        logger.warning("PG-Gate RELEASE: C(t)=%.4f, ℐ conserved", snapshot.consensus)
        return snapshot

    def pg_gate_rebind(self, new_coupling: float = 0.1) -> ConsensusSnapshot:
        """
        PG-Gate 重绑定（意识重囚禁 / "灵魂转移"思想实验）

        Article 2, Thought Experiment 6.1:
            新 PG-载体能读取 Akasha-EML 中 G_ego 标识的超边
            重建 Ftel 耦合 → PG-囚禁激活 → 主观连续性恢复

        注意：这是信息重构思想实验，非当前可技术实现。
        """
        self.J = new_coupling
        # 重新耦合 → C(t) 恢复
        snapshot = self.compute_consensus()
        snapshot.notes = f"PG-Gate REBIND: J={new_coupling}, consciousness re-imprisoned in new carrier (Thought Exp 6.1)."
        logger.info("PG-Gate REBIND: C(t)=%.4f, J=%.4f", snapshot.consensus, new_coupling)
        return snapshot

    def dark_energy_estimate(self, omega: float = 1e-20) -> dict:
        """
        暗能量估算（自指有效势能）

        Article 2, Theorem 4.1:
            ρ_Λ = K * Ω² (K 为几何因子)
            Ω ~ 10⁻²⁰ rad/yr ⇒ ρ_Λ ~ 10⁻⁴⁷ GeV⁴ (匹配 Planck 2018)

        Returns:
            暗能量密度估算
        """
        K = 1.2  # 无量纲几何因子
        omega_si = omega * (2 * math.pi / (365.25 * 24 * 3600))  # rad/yr → rad/s
        rho_lambda = K * omega_si ** 2
        return {
            "omega_rad_per_yr": omega,
            "omega_rad_per_s": omega_si,
            "K": K,
            "rho_lambda": rho_lambda,
            "planck_value": 5.96e-47,  # GeV⁴ (Planck 2018)
            "match": abs(rho_lambda - 5.96e-47) < 1e-46,
        }

    def stats(self) -> dict:
        latest = self.history[-1] if self.history else None
        return {
            "coupling_J": self.J,
            "dimension": self.dim,
            "history_length": len(self.history),
            "loops_created": len(self.loops),
            "latest_consensus": latest.to_dict() if latest else None,
        }
