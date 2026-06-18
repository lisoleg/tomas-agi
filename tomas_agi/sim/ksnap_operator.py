# -*- coding: utf-8 -*-
"""
KSnapOperator — κ-Snap 显影算符 (TOMAS Axiom A2)
===================================================

Theory Source:
    "κ-Snap（κ-显影）作为时间与因果的本体论基石"
    (微信公众号文章, 章锋, 2026-06-18)

Core Concepts:
    1. κ-Snap 是投影算符 Π_κ，作用于 EML 超图的候选超边集
    2. 未 κ-Snap：超边仅作为候选关系（Candidate），处于叠加态
    3. κ-Snap：在观测基 Π 下投影为经典事实（Classical Fact）
    4. 时间 = κ-Snap 序列的偏序集（Partial Order）
    5. 与量子坍缩的区别：有载体(EML超边)、有动力(Ftel)、有裁判(MUS/G_ego)

Trigger Conditions:
    1. Ftel 阈值: |Ftel(e)| >= θ_ftel
    2. 无 MUS 冲突: e 未被标记为互斥稳态双存
    3. 观测基就绪: Π 已选定（由 G_ego 或物理环境决定）

Results:
    - Manifest: 超边成为经典事实，写入因果日志
    - Reject: Dead-Zero 或 MUS 激活且未裁决，信息耗散入未显影仓
    - Suspend: MUS 激活，挂起等待 G_ego 裁决

Author: TOMAS Team
Version: v1.0
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================
# 枚举与常量
# ============================================================

class SnapResult(Enum):
    """κ-Snap 执行结果"""
    MANIFESTED = "manifested"      # 显影成功
    REJECT_DZ = "reject_dz"        # Dead-Zero 拒绝
    SUSPEND_MUS = "suspend_mus"    # MUS 挂起
    REJECT_FTEL = "reject_ftel"    # Ftel 不足


class ObservationBase(Enum):
    """观测基类型"""
    SENSOR = "sensor"        # 感知基（空间位置/传感器触发）
    ACTUATOR = "actuator"    # 执行基（物理指令）
    ETHICAL = "ethical"      # 伦理决策基
    COGNITIVE = "cognitive"  # 认知基（推理/记忆）


# ============================================================
# 数据结构
# ============================================================

@dataclass
class CandidateEdge:
    """候选超边（未 κ-Snap）"""
    edge_id: str
    source: str
    target: str
    relation: str
    i_value: float                           # ℐ 信息存在度
    ftel_magnitude: float                    # |Ftel| 流贯强度
    features: Dict[str, Any] = field(default_factory=dict)
    mus_active: bool = False                 # 是否 MUS 激活
    std_ref: Optional[str] = None            # 标准引用
    timestamp: float = field(default_factory=time.time)


@dataclass
class ManifestedEdge:
    """显影超边（经典事实）"""
    edge_id: str
    source: str
    target: str
    relation: str
    i_value: float
    observation_base: ObservationBase
    snap_timestamp: float
    psi_anchor: str                          # ψ-锚（因果链标识）
    features: Dict[str, Any] = field(default_factory=dict)
    std_ref: Optional[str] = None


@dataclass
class SnapEvent:
    """κ-Snap 事件（因果日志条目）"""
    event_id: str
    candidate_id: str
    result: SnapResult
    observation_base: ObservationBase
    timestamp: float
    reason: str = ""
    manifested_edge: Optional[ManifestedEdge] = None

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "candidate_id": self.candidate_id,
            "result": self.result.value,
            "observation_base": self.observation_base.value,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "manifested": self.manifested_edge is not None,
        }


# ============================================================
# κ-Snap 算子
# ============================================================

class KSnapOperator:
    """
    κ-Snap 显影算符 (Axiom A2)

    将候选超边投影为经典事实，构建时间箭头（偏序集）。

    Algorithm (Article 1, Appendix B):
        1. Dead-Zero Check
        2. MUS Check
        3. Perform Snap (Projection)
        4. Write to Classical KB
        5. Log causality
    """

    def __init__(
        self,
        theta_ftel: float = 0.1,
        theta_dead: float = 0.01,
        dead_zero_checker=None,
        mus_arbiter=None,
    ):
        self.theta_ftel = theta_ftel
        self.theta_dead = theta_dead
        self.dead_zero_checker = dead_zero_checker
        self.mus_arbiter = mus_arbiter

        # 因果日志（偏序集 T）
        self.causal_log: List[SnapEvent] = []
        # 显影事实库
        self.manifested_kb: Dict[str, ManifestedEdge] = {}
        # 未显影仓（耗散信息）
        self.latent_pool: List[CandidateEdge] = []

    def execute(
        self,
        candidate: CandidateEdge,
        obs_base: ObservationBase = ObservationBase.COGNITIVE,
    ) -> SnapEvent:
        """
        执行 κ-Snap 投影算符

        Returns:
            SnapEvent: 包含结果和（如有）显影超边
        """
        event_id = f"snap_{uuid.uuid4().hex[:8]}"
        timestamp = time.time()

        # 1. Ftel 阈值检查
        if candidate.ftel_magnitude < self.theta_ftel:
            event = SnapEvent(
                event_id=event_id,
                candidate_id=candidate.edge_id,
                result=SnapResult.REJECT_FTEL,
                observation_base=obs_base,
                timestamp=timestamp,
                reason=f"Ftel insufficient: {candidate.ftel_magnitude:.4f} < {self.theta_ftel}",
            )
            self.latent_pool.append(candidate)
            self.causal_log.append(event)
            logger.debug("κ-Snap REJECT_FTEL: %s (ftel=%.4f)", candidate.edge_id, candidate.ftel_magnitude)
            return event

        # 2. Dead-Zero 检查
        is_dead = False
        dz_reason = ""
        if self.dead_zero_checker is not None:
            try:
                is_dead, dz_reason = self.dead_zero_checker.check_dead_zero_dikwp(
                    candidate.i_value, "data"
                )
            except Exception:
                is_dead = candidate.i_value < self.theta_dead
                dz_reason = f"ℐ={candidate.i_value:.4f} < θ_dead={self.theta_dead}"
        else:
            is_dead = candidate.i_value < self.theta_dead
            dz_reason = f"ℐ={candidate.i_value:.4f} < θ_dead={self.theta_dead}"

        if is_dead:
            event = SnapEvent(
                event_id=event_id,
                candidate_id=candidate.edge_id,
                result=SnapResult.REJECT_DZ,
                observation_base=obs_base,
                timestamp=timestamp,
                reason=f"Dead-Zero: {dz_reason}",
            )
            self.latent_pool.append(candidate)
            self.causal_log.append(event)
            logger.info("κ-Snap REJECT_DZ: %s (%s)", candidate.edge_id, dz_reason)
            return event

        # 3. MUS 检查
        mus_active = candidate.mus_active
        if not mus_active and self.mus_arbiter is not None:
            try:
                mus_result = self.mus_arbiter.check_mus(candidate.edge_id, candidate)
                mus_active = mus_result.is_mus_active if hasattr(mus_result, "is_mus_active") else False
            except Exception:
                pass

        if mus_active:
            event = SnapEvent(
                event_id=event_id,
                candidate_id=candidate.edge_id,
                result=SnapResult.SUSPEND_MUS,
                observation_base=obs_base,
                timestamp=timestamp,
                reason="MUS active: dual-state suspended, awaiting G_ego adjudication",
            )
            # 不写入 latent_pool，挂起等待裁决
            self.causal_log.append(event)
            logger.info("κ-Snap SUSPEND_MUS: %s (awaiting adjudication)", candidate.edge_id)
            return event

        # 4. 执行投影（显影）
        psi_anchor = f"ψ_{uuid.uuid4().hex[:12]}"
        manifested = ManifestedEdge(
            edge_id=candidate.edge_id,
            source=candidate.source,
            target=candidate.target,
            relation=candidate.relation,
            i_value=candidate.i_value,
            observation_base=obs_base,
            snap_timestamp=timestamp,
            psi_anchor=psi_anchor,
            features=candidate.features.copy(),
            std_ref=candidate.std_ref,
        )

        # 5. 写入经典事实库
        self.manifested_kb[manifested.edge_id] = manifested

        # 6. 记录因果日志
        event = SnapEvent(
            event_id=event_id,
            candidate_id=candidate.edge_id,
            result=SnapResult.MANIFESTED,
            observation_base=obs_base,
            timestamp=timestamp,
            reason="Manifested successfully",
            manifested_edge=manifested,
        )
        self.causal_log.append(event)
        logger.info("κ-Snap MANIFESTED: %s → ψ=%s (ℐ=%.4f)", candidate.edge_id, psi_anchor, candidate.i_value)
        return event

    def get_causal_chain(self, edge_id: str) -> List[SnapEvent]:
        """获取某超边的因果链（偏序集前驱）"""
        return [e for e in self.causal_log if e.candidate_id == edge_id]

    def get_time_order(self) -> List[Tuple[str, str, float]]:
        """
        获取时间偏序集 T = (events, ≤)
        返回 [(event_id, candidate_id, timestamp), ...] 按时间排序
        """
        return [(e.event_id, e.candidate_id, e.timestamp) for e in sorted(self.causal_log, key=lambda x: x.timestamp)]

    def un_snap(self, edge_id: str) -> bool:
        """
        Un-Snap 操作（需要访问全 EML 超图，物理不可达）

        Article 1, Theorem 4.1:
            "Un-Snap 需访问全 EML 超图，物理不可达"
            此方法始终返回 False，证明 κ-Snap 不可逆性。
        """
        logger.warning("Un-Snap attempted for %s — physically unreachable (Theorem 4.1)", edge_id)
        return False

    def stats(self) -> dict:
        """统计信息"""
        total = len(self.causal_log)
        manifested = sum(1 for e in self.causal_log if e.result == SnapResult.MANIFESTED)
        rejected = sum(1 for e in self.causal_log if e.result == SnapResult.REJECT_DZ)
        suspended = sum(1 for e in self.causal_log if e.result == SnapResult.SUSPEND_MUS)
        ftel_rejected = sum(1 for e in self.causal_log if e.result == SnapResult.REJECT_FTEL)
        return {
            "total_snaps": total,
            "manifested": manifested,
            "rejected_dz": rejected,
            "suspended_mus": suspended,
            "rejected_ftel": ftel_rejected,
            "manifest_rate": manifested / total if total > 0 else 0.0,
            "latent_pool_size": len(self.latent_pool),
            "kb_size": len(self.manifested_kb),
        }


# ============================================================
# 感知上行 / 执行下行 便捷函数
# ============================================================

def perception_k_snap(
    sensor_data: Dict[str, Any],
    ksnap: KSnapOperator,
    i_value: float = 0.5,
    ftel: float = 0.5,
) -> SnapEvent:
    """
    感知上行：sensor_data → 候选超边 → κ-Snap

    Article 1, Section 6.1:
        1. 生成候选超边
        2. T_Shield 校验（Dead-Zero）
        3. κ-Snap 触发
        4. 显影：写入 EML KB
    """
    candidate = CandidateEdge(
        edge_id=f"perc_{uuid.uuid4().hex[:8]}",
        source=sensor_data.get("source", "sensor"),
        target=sensor_data.get("target", "eml_graph"),
        relation=sensor_data.get("relation", "perceives"),
        i_value=i_value,
        ftel_magnitude=ftel,
        features=sensor_data,
    )
    return ksnap.execute(candidate, ObservationBase.SENSOR)


def actuation_k_snap(
    decision: Dict[str, Any],
    ksnap: KSnapOperator,
    i_value: float = 0.7,
    ftel: float = 0.7,
) -> SnapEvent:
    """
    执行下行：decision → 候选决策超边 → κ-Snap → 物理指令

    Article 1, Section 6.2:
        1. 候选决策超边
        2. 检查 MUS
        3. 显影为物理指令
        4. 记录因果链
    """
    candidate = CandidateEdge(
        edge_id=f"act_{uuid.uuid4().hex[:8]}",
        source=decision.get("source", "g_ego"),
        target=decision.get("target", "actuator"),
        relation=decision.get("relation", "executes"),
        i_value=i_value,
        ftel_magnitude=ftel,
        mus_active=decision.get("mus_active", False),
        features=decision,
    )
    return ksnap.execute(candidate, ObservationBase.ACTUATOR)
