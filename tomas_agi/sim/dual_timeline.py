"""
双时间维度引擎 — 因果/认知分离 ↔ TOMAS 融合
==============================================

基于《第二时间维度：从奇点消失到认知防火墙》与 TOMAS AGI 的融合架构。

核心概念:
  外部时间 (t_ext) — 因果流: 事件驱动的物理时序
  内部时间 (t_int) — 认知流: 思维驱动的概念演化时序

关键映射:
  普朗克阈值  → κ-Snap 临界值 (因果/认知分界)
  奇点消失   → Dead-Zero 生效 (认知奇点被死零熔断消除)
  认知防火墙 → 防止认知无限递归 (anti-infinity guard)
  双时序对齐 → ℐ/causal 分离 (信息存在度 ≠ 因果强度)

架构:
  ExternalTimeline  — 因果链 (事件序列, 严格因果序)
  InternalTimeline  — 认知链 (概念演化, 可回溯/可分支)
  CognitiveFirewall — 认知防火墙 (防止无限递归/自指爆炸)
  DualTimelineAligner — 双时序对齐器

Author: TOMAS v3.0
Date: 2026-06-16
"""

import time
import math
import logging
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 枚举与数据类
# ═══════════════════════════════════════════════════════════════

class TimeDomain(Enum):
    """时间域"""
    EXTERNAL = "external"     # 外部因果时间
    INTERNAL = "internal"     # 内部认知时间


class CausalEventType(Enum):
    """因果事件类型"""
    OBSERVATION = "observation"      # 观察
    ACTION = "action"                # 行动
    INTERRUPTION = "interruption"    # 中断
    DEAD_ZERO = "dead_zero"         # 死零熔断
    KAPPA_SNAP = "kappa_snap"       # κ-Snap 决策


class CognitiveEventType(Enum):
    """认知事件类型"""
    HYPOTHESIS = "hypothesis"        # 提出假设
    INFERENCE = "inference"          # 推理
    REFLECTION = "reflection"        # 反思
    REVISION = "revision"            # 修正
    DEAD_ZERO_REJECT = "dz_reject"  # 死零拒答
    MUS_DUAL = "mus_dual"           # MUS 双存


class FirewallVerdict(Enum):
    """认知防火墙判定"""
    ALLOW = "ALLOW"                  # 放行
    THROTTLE = "THROTTLE"            # 限速 (递归深度大)
    BLOCK = "BLOCK"                  # 阻断 (无限递归/自指)
    DEAD_ZERO = "DEAD_ZERO"          # 死零熔断


@dataclass
class CausalEvent:
    """因果事件"""
    id: str
    event_type: CausalEventType
    timestamp: float = field(default_factory=time.time)
    # 事件载荷
    payload: Dict[str, Any] = field(default_factory=dict)
    # 因果前驱
    predecessor_id: Optional[str] = None
    # ℐ 因果强度
    causal_iota: float = 0.0


@dataclass
class CognitiveEvent:
    """认知事件"""
    id: str
    event_type: CognitiveEventType
    timestamp: float = field(default_factory=time.time)
    # 认知内容
    content: str = ""
    # ℐ 信息存在度
    cognitive_iota: float = 0.0
    # 递归深度
    recursion_depth: int = 0
    # 关联的因果事件
    linked_causal_id: Optional[str] = None
    # 认知前驱 (可以有多个 → 分支)
    predecessor_ids: List[str] = field(default_factory=list)


@dataclass
class SingularityReport:
    """奇点检测报告"""
    event_id: str
    domain: TimeDomain
    # 奇点类型
    singularity_type: str = ""  # "infinite_recursion" / "self_reference" / "cognitive_divergence"
    # 是否被消解
    resolved: bool = False
    # 消解方式
    resolution: str = ""  # "dead_zero" / "kappa_snap" / "firewall_block"
    # 风险等级
    risk_level: float = 0.0


# ═══════════════════════════════════════════════════════════════
# 外部时间线 (因果流)
# ═══════════════════════════════════════════════════════════════

class ExternalTimeline:
    """
    外部时间线 — 因果链

    严格因果序: 每个事件必须有前驱
    事件不可删除/修改 (append-only)
    """

    def __init__(self):
        self._events: Dict[str, CausalEvent] = {}
        self._order: List[str] = []  # 按时间排序的事件 ID

    def add_event(self, event: CausalEvent) -> None:
        """添加因果事件"""
        self._events[event.id] = event
        self._order.append(event.id)
        # 按时间排序
        self._order.sort(key=lambda eid: self._events[eid].timestamp)

    def get_event(self, event_id: str) -> Optional[CausalEvent]:
        return self._events.get(event_id)

    def get_events_range(
        self, start: float = 0.0, end: float = float('inf')
    ) -> List[CausalEvent]:
        """获取时间范围内的事件"""
        return [
            self._events[eid]
            for eid in self._order
            if start <= self._events[eid].timestamp <= end
        ]

    @property
    def latest(self) -> Optional[CausalEvent]:
        if not self._order:
            return None
        return self._events[self._order[-1]]

    @property
    def count(self) -> int:
        return len(self._events)


# ═══════════════════════════════════════════════════════════════
# 内部时间线 (认知流)
# ═══════════════════════════════════════════════════════════════

class InternalTimeline:
    """
    内部时间线 — 认知链

    可回溯/可分支: 支持假设分支和修正
    递归深度追踪: 防止认知无限递归
    """

    def __init__(self, max_recursion: int = 10):
        self._events: Dict[str, CognitiveEvent] = {}
        self._branches: Dict[str, List[str]] = {}  # 根事件 → 分支
        self.max_recursion = max_recursion

    def add_event(self, event: CognitiveEvent) -> None:
        """添加认知事件"""
        self._events[event.id] = event

        # 检查递归深度
        if event.recursion_depth > self.max_recursion:
            logger.warning(
                f"[InternalTimeline] Recursion depth {event.recursion_depth} "
                f"exceeds max {self.max_recursion}"
            )

        # 维护分支
        for pred_id in event.predecessor_ids:
            if pred_id not in self._branches:
                self._branches[pred_id] = []
            self._branches[pred_id].append(event.id)

    def get_event(self, event_id: str) -> Optional[CognitiveEvent]:
        return self._events.get(event_id)

    def get_branches(self, root_id: str) -> List[CognitiveEvent]:
        """获取某事件的所有分支"""
        branch_ids = self._branches.get(root_id, [])
        return [self._events[eid] for eid in branch_ids if eid in self._events]

    def get_lineage(self, event_id: str) -> List[CognitiveEvent]:
        """获取某事件的上溯谱系"""
        lineage = []
        current = self._events.get(event_id)
        while current:
            lineage.append(current)
            if current.predecessor_ids:
                current = self._events.get(current.predecessor_ids[0])
            else:
                break
        return lineage

    @property
    def count(self) -> int:
        return len(self._events)


# ═══════════════════════════════════════════════════════════════
# 认知防火墙
# ═══════════════════════════════════════════════════════════════

class CognitiveFirewall:
    """
    认知防火墙 — 防止认知无限递归/自指爆炸

    三级防护:
      1. THROTTLE: 递归深度 > warn_level → 限速
      2. BLOCK:   递归深度 > max_level → 阻断
      3. DEAD_ZERO: ℐ < θ → 熔断

    普朗克阈值类比:
      认知的"普朗克时间" = 最小有意义的认知步骤
      低于此阈值的事件被死零熔断
    """

    def __init__(
        self,
        theta_dead: float = 0.15,
        warn_recursion: int = 5,
        max_recursion: int = 10,
        planck_threshold: float = 0.01,
    ):
        self.theta_dead = theta_dead
        self.warn_recursion = warn_recursion
        self.max_recursion = max_recursion
        self.planck_threshold = planck_threshold
        self._block_log: List[Dict[str, Any]] = []

    def evaluate(
        self, event: CognitiveEvent, theta_dead: float = 0.15
    ) -> FirewallVerdict:
        """
        评估认知事件是否放行

        优先级: DEAD_ZERO > BLOCK > THROTTLE > ALLOW
        """
        # 1. 死零熔断 (最高优先级)
        actual_theta = theta_dead if theta_dead > 0 else self.theta_dead
        if event.cognitive_iota < actual_theta:
            self._log_block(event, "dead_zero", event.cognitive_iota)
            return FirewallVerdict.DEAD_ZERO

        # 2. 自指检测
        if self._is_self_referential(event):
            self._log_block(event, "self_reference", event.recursion_depth)
            return FirewallVerdict.BLOCK

        # 3. 无限递归阻断
        if event.recursion_depth >= self.max_recursion:
            self._log_block(event, "max_recursion", event.recursion_depth)
            return FirewallVerdict.BLOCK

        # 4. 限速警告
        if event.recursion_depth >= self.warn_recursion:
            return FirewallVerdict.THROTTLE

        # 5. 普朗克阈值检查
        if event.cognitive_iota < self.planck_threshold:
            self._log_block(event, "planck_threshold", event.cognitive_iota)
            return FirewallVerdict.DEAD_ZERO

        return FirewallVerdict.ALLOW

    def _is_self_referential(self, event: CognitiveEvent) -> bool:
        """检测自指: 事件内容是否引用自身 ID"""
        return event.id in event.content

    def _log_block(
        self, event: CognitiveEvent, reason: str, value: Any
    ) -> None:
        self._block_log.append({
            "event_id": event.id,
            "reason": reason,
            "value": value,
            "timestamp": time.time(),
        })

    @property
    def block_log(self) -> List[Dict[str, Any]]:
        return list(self._block_log)

    @property
    def block_count(self) -> int:
        return len(self._block_log)


# ═══════════════════════════════════════════════════════════════
# 双时序对齐器
# ═══════════════════════════════════════════════════════════════

class DualTimelineAligner:
    """
    双时序对齐器

    将外部因果时间与内部认知时间对齐:
      - 因果事件可触发认知事件 (observation → hypothesis)
      - 认知事件可影响因果事件 (inference → action)
      - 死零熔断在两个时间线上同步生效
    """

    def __init__(
        self,
        external: ExternalTimeline,
        internal: InternalTimeline,
        firewall: CognitiveFirewall,
    ):
        self.external = external
        self.internal = internal
        self.firewall = firewall
        self._links: Dict[str, str] = {}  # causal_id ↔ cognitive_id
        self._singularity_reports: List[SingularityReport] = []

    def link_events(
        self, causal_id: str, cognitive_id: str
    ) -> None:
        """关联因果事件和认知事件"""
        self._links[causal_id] = cognitive_id

    def align_and_evaluate(
        self, cognitive_event: CognitiveEvent, theta_dead: float = 0.15
    ) -> Tuple[FirewallVerdict, Optional[SingularityReport]]:
        """
        对齐评估: 认知事件 → 防火墙 → 奇点检测

        Returns:
            (verdict, singularity_report)
        """
        # 1. 防火墙评估
        verdict = self.firewall.evaluate(cognitive_event, theta_dead)

        # 2. 奇点检测
        singularity = None
        if verdict in (FirewallVerdict.BLOCK, FirewallVerdict.DEAD_ZERO):
            singularity = SingularityReport(
                event_id=cognitive_event.id,
                domain=TimeDomain.INTERNAL,
                singularity_type=self._classify_singularity(cognitive_event),
                resolved=True,
                resolution="dead_zero" if verdict == FirewallVerdict.DEAD_ZERO else "firewall_block",
                risk_level=self._compute_risk(cognitive_event),
            )
            self._singularity_reports.append(singularity)

        # 3. 若放行，添加到内部时间线
        if verdict in (FirewallVerdict.ALLOW, FirewallVerdict.THROTTLE):
            self.internal.add_event(cognitive_event)

        return verdict, singularity

    def _classify_singularity(self, event: CognitiveEvent) -> str:
        if event.recursion_depth >= 10:
            return "infinite_recursion"
        if self.firewall._is_self_referential(event):
            return "self_reference"
        return "cognitive_divergence"

    def _compute_risk(self, event: CognitiveEvent) -> float:
        """计算奇点风险等级 [0, 1]"""
        risk = 0.0
        risk += min(event.recursion_depth / self.firewall.max_recursion, 1.0) * 0.5
        risk += max(0, 1.0 - event.cognitive_iota) * 0.5
        return min(risk, 1.0)

    @property
    def singularity_reports(self) -> List[SingularityReport]:
        return list(self._singularity_reports)

    @property
    def alignment_stats(self) -> Dict[str, Any]:
        return {
            "external_events": self.external.count,
            "internal_events": self.internal.count,
            "links": len(self._links),
            "singularities": len(self._singularity_reports),
            "firewall_blocks": self.firewall.block_count,
        }


# ═══════════════════════════════════════════════════════════════
# 双时间维度引擎 (顶层接口)
# ═══════════════════════════════════════════════════════════════

class DualTimelineEngine:
    """
    双时间维度引擎 — 顶层接口

    整合:
      - ExternalTimeline (因果流)
      - InternalTimeline (认知流)
      - CognitiveFirewall (认知防火墙)
      - DualTimelineAligner (对齐器)
    """

    def __init__(
        self,
        theta_dead: float = 0.15,
        max_recursion: int = 10,
        warn_recursion: int = 5,
        planck_threshold: float = 0.01,
    ):
        self.external = ExternalTimeline()
        self.internal = InternalTimeline(max_recursion=max_recursion)
        self.firewall = CognitiveFirewall(
            theta_dead=theta_dead,
            warn_recursion=warn_recursion,
            max_recursion=max_recursion,
            planck_threshold=planck_threshold,
        )
        self.aligner = DualTimelineAligner(
            self.external, self.internal, self.firewall
        )
        self.theta_dead = theta_dead

    # ── 因果事件 ────────────────────────────────────────────

    def observe(self, event_id: str, payload: Dict[str, Any] = None,
                iota: float = 0.5) -> CausalEvent:
        """添加观察事件"""
        event = CausalEvent(
            id=event_id,
            event_type=CausalEventType.OBSERVATION,
            payload=payload or {},
            causal_iota=iota,
        )
        self.external.add_event(event)
        return event

    def act(self, event_id: str, payload: Dict[str, Any] = None,
            predecessor: str = None, iota: float = 0.5) -> CausalEvent:
        """添加行动事件"""
        event = CausalEvent(
            id=event_id,
            event_type=CausalEventType.ACTION,
            payload=payload or {},
            predecessor_id=predecessor,
            causal_iota=iota,
        )
        self.external.add_event(event)
        return event

    # ── 认知事件 ────────────────────────────────────────────

    def think(
        self,
        event_id: str,
        content: str,
        iota: float = 0.5,
        recursion: int = 0,
        predecessors: List[str] = None,
        linked_causal: str = None,
    ) -> Tuple[FirewallVerdict, Optional[SingularityReport]]:
        """
        添加认知事件 (经过防火墙)

        Returns:
            (verdict, singularity_report)
        """
        event = CognitiveEvent(
            id=event_id,
            event_type=CognitiveEventType.HYPOTHESIS,
            content=content,
            cognitive_iota=iota,
            recursion_depth=recursion,
            predecessor_ids=predecessors or [],
            linked_causal_id=linked_causal,
        )
        verdict, singularity = self.aligner.align_and_evaluate(event, self.theta_dead)

        if verdict == FirewallVerdict.ALLOW:
            logger.debug(f"[DualTimeline] Cognitive event {event_id} ALLOWED")
        elif verdict == FirewallVerdict.DEAD_ZERO:
            logger.info(f"[DualTimeline] Cognitive event {event_id} DEAD-ZERO (ℐ={iota:.3f})")
        elif verdict == FirewallVerdict.BLOCK:
            logger.warning(f"[DualTimeline] Cognitive event {event_id} BLOCKED (recursion={recursion})")

        return verdict, singularity

    # ── 统计 ────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "external_events": self.external.count,
            "internal_events": self.internal.count,
            "firewall_blocks": self.firewall.block_count,
            "singularities_resolved": len(self.aligner.singularity_reports),
            "theta_dead": self.theta_dead,
            "max_recursion": self.firewall.max_recursion,
        }
