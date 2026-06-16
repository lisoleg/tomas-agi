"""
FDE 本体构建器 — 道法术器四阶架构 ↔ TOMAS 融合
==================================================

基于何俊《道法术器：从本体构建到工业落地》与 TOMAS AGI 的融合架构。

四阶映射:
  道 (Dao)  — ℐ 自锚 / 第一性原理          → TOMAS Level 5: T-Proc 认知审计
  法 (Fa)   — Gromov-Hausdorff 对齐         → TOMAS Level 4: NASGA 结构对齐
  术 (Shu)  — NASGA 非结合传播              → TOMAS Level 3: EML 超边推理
  器 (Qi)   — EML 壳 / 工业标准接地          → TOMAS Level 2: 语义页封装

ℐ-标定 (Iota Calibration):
  每个本体节点携带 ℐ 值 [0,1]，表示信息存在度。
  ℐ < θ_dead → Dead-Zero 熔断（道层拒答）
  Asym≠0 → MUS 双存（法层保留矛盾对）

工业接地:
  器层必须满足工业标准 (IEC 62443 / ISO 26262 / IEC 61508)
  术层必须通过 NASGA 非结合验证
  法层必须通过 Gromov-Hausdorff 距离阈值
  道层必须通过 ℐ 自锚检验

Author: TOMAS v3.0
Date: 2026-06-16
"""

import json
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

class FDENodeType(Enum):
    """道法术器四阶节点类型"""
    DAO = "道"          # 第一性原理 / ℐ 自锚
    FA = "法"           # Gromov-Hausdorff 对齐
    SHU = "术"          # NASGA 非结合传播
    QI = "器"           # EML 壳 / 工业标准接地


class GroundingStatus(Enum):
    """接地状态"""
    GROUNDED = "GROUNDED"              # 完全接地
    PARTIALLY_GROUNDED = "PARTIAL"      # 部分接地
    UNGROUNDED = "UNGROUNDED"          # 未接地
    DEAD_ZERO = "DEAD_ZERO"            # 死零熔断


class IndustrialStandard(Enum):
    """工业标准"""
    IEC_62443 = "IEC62443"       # 工控安全
    ISO_26262 = "ISO26262"       # 汽车功能安全
    IEC_61508 = "IEC61508"       # 通用功能安全
    IEC_61850 = "IEC61850"       # 电力系统通信
    ISA_99 = "ISA99"             # 自动化安全
    NONE = "NONE"                # 无标准要求


@dataclass
class FDENode:
    """FDE 本体节点"""
    id: str
    name: str
    node_type: FDENodeType
    # ℐ-标定值
    iota_value: float = 0.0
    # 接地状态
    grounding: GroundingStatus = GroundingStatus.UNGROUNDED
    # 工业标准 (器层必须)
    industrial_standard: IndustrialStandard = IndustrialStandard.NONE
    # NASGA 非结合度 (术层)
    nasga_asym: float = 0.0
    # Gromov-Hausdorff 距离 (法层)
    gh_distance: float = float('inf')
    # ℐ 自锚偏差 (道层)
    self_anchor_deviation: float = float('inf')
    # 父节点 ID
    parent_id: Optional[str] = None
    # 子节点 ID 列表
    children_ids: List[str] = field(default_factory=list)
    # 关联的 EML 顶点
    eml_vertex_ids: List[str] = field(default_factory=list)
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 时间戳
    timestamp: float = field(default_factory=time.time)

    def is_dead_zero(self, theta: float = 0.15) -> bool:
        """死零检验: ℐ < θ"""
        return self.iota_value < theta

    def is_mus(self, asym_threshold: float = 0.05) -> bool:
        """MUS 双存检验: Asym≠0"""
        return abs(self.nasga_asym) >= asym_threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "iota_value": self.iota_value,
            "grounding": self.grounding.value,
            "industrial_standard": self.industrial_standard.value,
            "nasga_asym": self.nasga_asym,
            "gh_distance": self.gh_distance,
            "self_anchor_deviation": self.self_anchor_deviation,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
        }


@dataclass
class EchoContext:
    """
    回声上下文 — IT/OT/ET 三域信息
    IT: 信息技术域 (软件/数据/算法)
    OT: 运营技术域 (PLC/传感器/执行器)
    ET: 工程技术域 (设计/仿真/验证)
    """
    it_context: str = ""
    ot_context: str = ""
    et_context: str = ""
    # 跨域翻译置信度
    translation_confidence: float = 0.0
    # 域间冲突标记
    cross_domain_conflicts: List[str] = field(default_factory=list)

    def is_aligned(self, threshold: float = 0.7) -> bool:
        return self.translation_confidence >= threshold and len(self.cross_domain_conflicts) == 0


@dataclass
class FDEValidationResult:
    """FDE 四阶验证结果"""
    node_id: str
    node_type: FDENodeType
    # 器层验证
    qi_pass: bool = False
    qi_reason: str = ""
    # 术层验证
    shu_pass: bool = False
    shu_reason: str = ""
    # 法层验证
    fa_pass: bool = False
    fa_reason: str = ""
    # 道层验证
    dao_pass: bool = False
    dao_reason: str = ""
    # 总体判定
    overall: GroundingStatus = GroundingStatus.UNGROUNDED

    @property
    def all_pass(self) -> bool:
        return self.qi_pass and self.shu_pass and self.fa_pass and self.dao_pass


# ═══════════════════════════════════════════════════════════════
# FDE 本体构建器
# ═══════════════════════════════════════════════════════════════

class FDEOntologyBuilder:
    """
    道法术器四阶本体构建器

    构建流程:
      1. 器层 (Qi):   EML 壳封装 → 工业标准接地
      2. 术层 (Shu):  NASGA 非结合传播 → 技能 Asym/MUS 检验
      3. 法层 (Fa):   Gromov-Hausdorff 对齐 → 跨域翻译
      4. 道层 (Dao):  ℐ 自锚检验 → Dead-Zero 熔断

    验证流程 (逆序):
      道 → 法 → 术 → 器 (自顶向下审计)
    """

    # 工业标准映射
    INDUSTRY_STANDARDS: Dict[str, IndustrialStandard] = {
        "scada": IndustrialStandard.IEC_62443,
        "automotive": IndustrialStandard.ISO_26262,
        "safety": IndustrialStandard.IEC_61508,
        "power": IndustrialStandard.IEC_61850,
        "automation": IndustrialStandard.ISA_99,
    }

    def __init__(
        self,
        theta_dead: float = 0.15,
        asym_threshold: float = 0.05,
        gh_threshold: float = 0.3,
        anchor_deviation_threshold: float = 0.2,
    ):
        self.theta_dead = theta_dead
        self.asym_threshold = asym_threshold
        self.gh_threshold = gh_threshold
        self.anchor_deviation_threshold = anchor_deviation_threshold
        self._nodes: Dict[str, FDENode] = {}
        self._echo_contexts: Dict[str, EchoContext] = {}

    # ── 节点管理 ─────────────────────────────────────────────

    def add_node(self, node: FDENode) -> None:
        """添加节点"""
        self._nodes[node.id] = node
        # 维护父子关系
        if node.parent_id and node.parent_id in self._nodes:
            parent = self._nodes[node.parent_id]
            if node.id not in parent.children_ids:
                parent.children_ids.append(node.id)

    def get_node(self, node_id: str) -> Optional[FDENode]:
        return self._nodes.get(node_id)

    @property
    def nodes(self) -> Dict[str, FDENode]:
        return dict(self._nodes)

    # ── ℐ-标定 ─────────────────────────────────────────────

    def calibrate_iota(self, node_id: str, evidence: List[Dict[str, Any]]) -> float:
        """
        ℐ-标定: 基于证据链计算信息存在度

        I(X) = 1.0 + ln(1 + N_evidence) / 10.0 × weight_avg
        """
        if node_id not in self._nodes:
            return 0.0

        n = len(evidence)
        if n == 0:
            self._nodes[node_id].iota_value = 0.0
            self._nodes[node_id].grounding = GroundingStatus.DEAD_ZERO
            return 0.0

        weights = [e.get("weight", 0.5) for e in evidence]
        weight_avg = sum(weights) / len(weights)
        iota = 1.0 + math.log(1 + n) / 10.0 * weight_avg
        iota = max(0.0, min(iota, 1.0))

        self._nodes[node_id].iota_value = iota

        if iota < self.theta_dead:
            self._nodes[node_id].grounding = GroundingStatus.DEAD_ZERO
        elif iota < 0.5:
            self._nodes[node_id].grounding = GroundingStatus.PARTIALLY_GROUNDED
        else:
            self._nodes[node_id].grounding = GroundingStatus.GROUNDED

        return iota

    # ── 器层: EML 壳 + 工业接地 ──────────────────────────────

    def validate_qi(
        self,
        node: FDENode,
        required_standard: Optional[IndustrialStandard] = None,
    ) -> Tuple[bool, str]:
        """
        器层验证: EML 壳封装 + 工业标准接地

        通过条件:
          1. 节点有关联 EML 顶点
          2. 满足指定工业标准 (若有)
          3. ℐ ≥ θ_dead
        """
        if not node.eml_vertex_ids:
            return False, "no_eml_vertex"
        if required_standard and node.industrial_standard != required_standard:
            return False, f"standard_mismatch:{node.industrial_standard.value}!={required_standard.value}"
        if node.is_dead_zero(self.theta_dead):
            return False, f"dead_zero:iota={node.iota_value:.3f}"
        return True, "ok"

    # ── 术层: NASGA 非结合传播 ──────────────────────────────

    def validate_shu(self, node: FDENode) -> Tuple[bool, str]:
        """
        术层验证: NASGA 非结合传播 + Asym/MUS 检验

        通过条件:
          1. NASGA Asym ≠ 0 (允许 MUS)
          2. 若 Asym ≥ 阈值 → 标记 MUS 但不阻断 (双存)
        """
        if abs(node.nasga_asym) < 1e-10:
            return False, "zero_asym:no_nasga_signature"
        return True, "ok" if not node.is_mus(self.asym_threshold) else "mus_active:双存"

    # ── 法层: Gromov-Hausdorff 对齐 ──────────────────────────

    def validate_fa(self, node: FDENode) -> Tuple[bool, str]:
        """
        法层验证: Gromov-Hausdorff 距离对齐

        通过条件:
          d_GH < threshold (两个本体结构足够相似)
        """
        if node.gh_distance == float('inf'):
            return False, "no_alignment"
        if node.gh_distance > self.gh_threshold:
            return False, f"gh_too_large:{node.gh_distance:.3f}>{self.gh_threshold}"
        return True, "ok"

    # ── 道层: ℐ 自锚检验 ───────────────────────────────────

    def validate_dao(self, node: FDENode) -> Tuple[bool, str]:
        """
        道层验证: ℐ 自锚检验

        通过条件:
          ℐ 自锚偏差 < threshold (节点不偏离自身锚定)
          即: |ℐ(X) - ℐ(X)_self_anchor| < ε
        """
        if node.self_anchor_deviation == float('inf'):
            return False, "no_self_anchor"
        if node.self_anchor_deviation > self.anchor_deviation_threshold:
            return False, f"anchor_drift:{node.self_anchor_deviation:.3f}"
        return True, "ok"

    # ── 四阶全验证 ──────────────────────────────────────────

    def validate_full(self, node_id: str) -> FDEValidationResult:
        """
        四阶全链路验证: 器→术→法→道

        任一层失败 → 降级到该层对应的接地状态
        全部通过 → GROUNDED
        """
        node = self._nodes.get(node_id)
        if node is None:
            return FDEValidationResult(
                node_id=node_id,
                node_type=FDENodeType.QI,
                overall=GroundingStatus.UNGROUNDED,
            )

        result = FDEValidationResult(
            node_id=node_id,
            node_type=node.node_type,
        )

        # 器层
        result.qi_pass, result.qi_reason = self.validate_qi(node)
        # 术层
        result.shu_pass, result.shu_reason = self.validate_shu(node)
        # 法层
        result.fa_pass, result.fa_reason = self.validate_fa(node)
        # 道层
        result.dao_pass, result.dao_reason = self.validate_dao(node)

        # 总体判定
        if result.all_pass:
            result.overall = GroundingStatus.GROUNDED
        elif not result.dao_pass:
            result.overall = GroundingStatus.DEAD_ZERO
        elif not result.fa_pass or not result.shu_pass:
            result.overall = GroundingStatus.PARTIALLY_GROUNDED
        else:
            result.overall = GroundingStatus.PARTIALLY_GROUNDED

        return result

    # ── 回声上下文管理 ──────────────────────────────────────

    def set_echo_context(self, node_id: str, ctx: EchoContext) -> None:
        """设置回声上下文 (IT/OT/ET 三域)"""
        self._echo_contexts[node_id] = ctx

    def get_echo_context(self, node_id: str) -> Optional[EchoContext]:
        return self._echo_contexts.get(node_id)

    def check_cross_domain_alignment(
        self, node_id: str, threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        跨域对齐检查

        检查 IT/OT/ET 三域信息是否一致:
          - 翻译置信度 ≥ threshold
          - 无跨域冲突
        """
        ctx = self._echo_contexts.get(node_id)
        if ctx is None:
            return {"aligned": False, "reason": "no_echo_context"}

        aligned = ctx.is_aligned(threshold)
        return {
            "aligned": aligned,
            "confidence": ctx.translation_confidence,
            "conflicts": ctx.cross_domain_conflicts,
            "it": ctx.it_context[:100] if ctx.it_context else "",
            "ot": ctx.ot_context[:100] if ctx.ot_context else "",
            "et": ctx.et_context[:100] if ctx.et_context else "",
        }

    # ── 工业标准接地 ────────────────────────────────────────

    def assign_industry_standard(
        self, node_id: str, domain: str
    ) -> Optional[IndustrialStandard]:
        """
        根据领域自动分配工业标准
        """
        standard = self.INDUSTRY_STANDARDS.get(domain.lower())
        if standard and node_id in self._nodes:
            self._nodes[node_id].industrial_standard = standard
        return standard

    # ── 批量构建 ────────────────────────────────────────────

    def build_from_eml(
        self,
        eml_vertices: List[Dict[str, Any]],
        domain: str = "",
    ) -> List[str]:
        """
        从 EML 数据批量构建 FDE 本体

        每个顶点 → 器层节点 (EML 壳)
        自动设置 ℐ 值和工业标准
        """
        created_ids = []
        for v in eml_vertices:
            node_id = v.get("id", f"fde_{len(self._nodes)}")
            iota = v.get("i_value", v.get("iota", 0.0))
            asym = v.get("asym", 0.0)

            node = FDENode(
                id=node_id,
                name=v.get("name", v.get("concept", node_id)),
                node_type=FDENodeType.QI,
                iota_value=iota,
                nasga_asym=asym,
                eml_vertex_ids=[node_id],
                metadata={"source": "eml_import"},
            )

            # 设置接地状态
            if iota < self.theta_dead:
                node.grounding = GroundingStatus.DEAD_ZERO
            elif iota < 0.5:
                node.grounding = GroundingStatus.PARTIALLY_GROUNDED
            else:
                node.grounding = GroundingStatus.GROUNDED

            # 分配工业标准
            if domain:
                self.assign_industry_standard(node_id, domain)

            self.add_node(node)
            created_ids.append(node_id)

        return created_ids

    # ── 统计 ────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, Any]:
        """构建器统计"""
        n = len(self._nodes)
        if n == 0:
            return {"total": 0}

        by_type = {}
        by_grounding = {}
        dead_count = 0
        mus_count = 0

        for node in self._nodes.values():
            t = node.node_type.value
            by_type[t] = by_type.get(t, 0) + 1

            g = node.grounding.value
            by_grounding[g] = by_grounding.get(g, 0) + 1

            if node.is_dead_zero(self.theta_dead):
                dead_count += 1
            if node.is_mus(self.asym_threshold):
                mus_count += 1

        return {
            "total": n,
            "by_type": by_type,
            "by_grounding": by_grounding,
            "dead_zero_count": dead_count,
            "mus_count": mus_count,
            "echo_contexts": len(self._echo_contexts),
        }
