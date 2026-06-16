"""
IT-OT 翻译桥 — 工业 AI 规模化 ↔ TOMAS 融合
=============================================

基于《工业AI规模化：IT-OT翻译层 + 技术债务治理 + 零信任架构》与 TOMAS AGI 的融合。

核心概念:
  IT-OT 翻译层 — 信息技术(IT) ↔ 运营技术(OT) 语义桥
  技术债务治理 — 数据/模型/基础设施三层债务追踪
  零信任架构 — "永不信任，始终验证" 的语义门控
  联合KPI   — IT/OT 绑定激励指标

TOMAS 映射:
  翻译层   → TOMAS 语义桥 (EML 超图跨域翻译)
  技术债务 → Dead-Zero 前置拦截 (债务=低ℐ)
  零信任   → 语义防火墙 (ADC 高风险模式)
  联合KPI  → ℐ-最优调度 (统一优化目标)

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

class TechDomain(Enum):
    """技术域"""
    IT = "IT"       # 信息技术
    OT = "OT"       # 运营技术
    ET = "ET"       # 工程技术
    DUAL = "DUAL"   # 跨域


class DebtType(Enum):
    """技术债务类型"""
    DATA = "data"                   # 数据债务 (质量/完整性/时效性)
    MODEL = "model"                 # 模型债务 (精度/漂移/偏见)
    INFRASTRUCTURE = "infrastructure"  # 基础设施债务 (版本/兼容/安全)
    SEMANTIC = "semantic"           # 语义债务 (翻译缺失/歧义)


class DebtSeverity(Enum):
    """债务严重程度"""
    LOW = "low"             # ℐ > 0.5, 可容忍
    MEDIUM = "medium"       # 0.15 ≤ ℐ ≤ 0.5, 需关注
    HIGH = "high"           # ℐ < 0.15, 死零级
    CRITICAL = "critical"   # 安全风险, 必须立即处理


class TrustLevel(Enum):
    """信任级别 (零信任架构)"""
    VERIFIED = "verified"       # 完全验证
    CONDITIONAL = "conditional"  # 条件性信任
    UNTRUSTED = "untrusted"     # 未验证
    BLOCKED = "blocked"         # 已阻断


@dataclass
class TranslationEntry:
    """IT-OT 翻译条目"""
    id: str
    it_term: str                      # IT 术语
    ot_term: str                      # OT 术语
    semantic_bridge: str = ""         # 语义桥描述
    translation_iota: float = 0.0     # 翻译质量 ℐ
    domain: TechDomain = TechDomain.DUAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TechDebt:
    """技术债务条目"""
    id: str
    debt_type: DebtType
    severity: DebtSeverity
    description: str = ""
    # ℐ 影响度
    iota_impact: float = 0.0
    # 关联域
    domain: TechDomain = TechDomain.DUAL
    # 修复成本 (1-10)
    fix_cost: int = 1
    # 修复优先级
    priority: int = 0
    # 状态
    resolved: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "debt_type": self.debt_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "iota_impact": self.iota_impact,
            "domain": self.domain.value,
            "fix_cost": self.fix_cost,
            "priority": self.priority,
            "resolved": self.resolved,
        }


@dataclass
class TrustEvaluation:
    """零信任评估结果"""
    entity_id: str
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    # 验证步骤
    verification_steps: List[str] = field(default_factory=list)
    # 风险因子
    risk_factors: List[str] = field(default_factory=list)
    # ℐ 信任度
    trust_iota: float = 0.0
    # ADC 模式匹配 (语义防火墙)
    adc_patterns: List[str] = field(default_factory=list)
    # 判定原因
    reason: str = ""


@dataclass
class JointKPI:
    """联合 KPI"""
    id: str
    name: str
    it_target: float = 0.0
    ot_target: float = 0.0
    current_it: float = 0.0
    current_ot: float = 0.0
    weight: float = 1.0
    # ℐ 统一度量
    iota_score: float = 0.0

    def is_on_track(self, tolerance: float = 0.1) -> bool:
        """是否在轨"""
        it_diff = abs(self.current_it - self.it_target) / max(abs(self.it_target), 1e-6)
        ot_diff = abs(self.current_ot - self.ot_target) / max(abs(self.ot_target), 1e-6)
        return it_diff <= tolerance and ot_diff <= tolerance

    @property
    def gap(self) -> float:
        """IT/OT 差距"""
        return abs(self.current_it - self.current_ot)


# ═══════════════════════════════════════════════════════════════
# IT-OT 翻译器
# ═══════════════════════════════════════════════════════════════

class ITOTTranslator:
    """
    IT-OT 翻译器 — 语义桥

    将 IT 术语映射到 OT 术语 (反之亦然):
      IT: "microservice" ↔ OT: "control_module"
      IT: "latency" ↔ OT: "response_time"
      IT: "deploy" ↔ OT: "commission"

    翻译质量用 ℐ 衡量: ℐ < θ → 翻译不可靠
    """

    # 内置 IT-OT 词典
    DICTIONARY: Dict[str, str] = {
        "microservice": "control_module",
        "api": "opc_ua_endpoint",
        "latency": "response_time",
        "deploy": "commission",
        "monitor": "supervise",
        "alert": "alarm",
        "log": "event_record",
        "container": "virtual_controller",
        "pipeline": "production_line",
        "model": "transfer_function",
        "feature": "process_variable",
        "training": "calibration",
        "inference": "execution",
        "data_lake": "historian",
        "dashboard": "hmi",
        "security": "safety",
        "version": "revision",
        "rollback": "emergency_stop",
        "scaling": "load_adjustment",
        "queue": "batch_buffer",
    }

    def __init__(self):
        self._custom_entries: Dict[str, TranslationEntry] = {}
        self._reverse_dict: Dict[str, str] = {v: k for k, v in self.DICTIONARY.items()}

    def translate_it_to_ot(self, it_term: str) -> Optional[str]:
        """IT → OT 翻译"""
        # 先查自定义
        for entry in self._custom_entries.values():
            if entry.it_term.lower() == it_term.lower():
                return entry.ot_term
        return self.DICTIONARY.get(it_term.lower())

    def translate_ot_to_it(self, ot_term: str) -> Optional[str]:
        """OT → IT 翻译"""
        for entry in self._custom_entries.values():
            if entry.ot_term.lower() == ot_term.lower():
                return entry.it_term
        return self._reverse_dict.get(ot_term.lower())

    def add_translation(self, entry: TranslationEntry) -> None:
        """添加自定义翻译"""
        self._custom_entries[entry.id] = entry

    def evaluate_translation(self, it_term: str, ot_term: str) -> float:
        """
        评估翻译质量 (ℐ 值)

        Returns:
            ℐ ∈ [0, 1]: 1 = 完美翻译, 0 = 无翻译
        """
        translated = self.translate_it_to_ot(it_term)
        if translated is None:
            return 0.0
        if translated.lower() == ot_term.lower():
            return 1.0
        # 部分匹配
        overlap = len(set(translated.lower()) & set(ot_term.lower()))
        total = max(len(set(translated.lower()) | set(ot_term.lower())), 1)
        return overlap / total

    @property
    def vocabulary_size(self) -> int:
        return len(self.DICTIONARY) + len(self._custom_entries)


# ═══════════════════════════════════════════════════════════════
# 技术债务治理器
# ═══════════════════════════════════════════════════════════════

class TechnicalDebtGovernor:
    """
    技术债务治理器

    三层债务追踪:
      1. 数据债务: 质量/完整性/时效性 → ℐ 数据支撑度
      2. 模型债务: 精度/漂移/偏见 → ℐ 模型可靠性
      3. 基础设施债务: 版本/兼容/安全 → ℐ 环境稳定性
      4. 语义债务: 翻译缺失/歧义 → ℐ 翻译质量

    Dead-Zero 前置拦截:
      债务严重度 = HIGH/CRITICAL 且 ℐ < θ → 死零拦截
    """

    def __init__(self, theta_dead: float = 0.15):
        self.theta_dead = theta_dead
        self._debts: Dict[str, TechDebt] = {}

    def register_debt(self, debt: TechDebt) -> None:
        """注册技术债务"""
        # 自动计算严重程度
        if debt.iota_impact < self.theta_dead:
            debt.severity = DebtSeverity.HIGH
        elif debt.iota_impact < 0.5:
            if debt.severity == DebtSeverity.LOW:
                debt.severity = DebtSeverity.MEDIUM
        self._debts[debt.id] = debt

    def get_debt(self, debt_id: str) -> Optional[TechDebt]:
        return self._debts.get(debt_id)

    def resolve_debt(self, debt_id: str) -> bool:
        """标记债务为已解决"""
        debt = self._debts.get(debt_id)
        if debt:
            debt.resolved = True
            return True
        return False

    def scan_dead_zero_debts(self) -> List[TechDebt]:
        """扫描死零级债务 (需要立即处理)"""
        return [
            d for d in self._debts.values()
            if not d.resolved and d.severity in (DebtSeverity.HIGH, DebtSeverity.CRITICAL)
        ]

    def prioritize(self) -> List[TechDebt]:
        """
        按优先级排序债务

        优先级 = severity_weight × iota_impact / fix_cost
        """
        severity_weights = {
            DebtSeverity.LOW: 1,
            DebtSeverity.MEDIUM: 3,
            DebtSeverity.HIGH: 7,
            DebtSeverity.CRITICAL: 10,
        }

        active = [d for d in self._debts.values() if not d.resolved]
        for d in active:
            d.priority = int(
                severity_weights.get(d.severity, 1) * d.iota_impact * 10 / max(d.fix_cost, 1)
            )

        return sorted(active, key=lambda d: d.priority, reverse=True)

    @property
    def debt_stats(self) -> Dict[str, Any]:
        total = len(self._debts)
        if total == 0:
            return {"total": 0}
        by_type = {}
        by_severity = {}
        active = 0
        for d in self._debts.values():
            by_type[d.debt_type.value] = by_type.get(d.debt_type.value, 0) + 1
            by_severity[d.severity.value] = by_severity.get(d.severity.value, 0) + 1
            if not d.resolved:
                active += 1
        return {
            "total": total,
            "active": active,
            "resolved": total - active,
            "by_type": by_type,
            "by_severity": by_severity,
            "dead_zero_count": len(self.scan_dead_zero_debts()),
        }


# ═══════════════════════════════════════════════════════════════
# 零信任门控
# ═══════════════════════════════════════════════════════════════

class ZeroTrustGate:
    """
    零信任门控 — "永不信任，始终验证"

    三步验证:
      1. 身份验证: 实体是否已知?
      2. 语义验证: 请求是否安全? (ADC 模式检测)
      3. ℐ 验证: 信息支撑度是否足够?

    ADC 高风险模式 (6 种):
      - 身份冒充 (identity_spoof)
      - 指令注入 (command_injection)
      - 数据投毒 (data_poisoning)
      - 模型窃取 (model_extraction)
      - 横向移动 (lateral_movement)
      - 权限提升 (privilege_escalation)
    """

    ADC_PATTERNS = [
        "identity_spoof",
        "command_injection",
        "data_poisoning",
        "model_extraction",
        "lateral_movement",
        "privilege_escalation",
    ]

    def __init__(self, theta_dead: float = 0.15):
        self.theta_dead = theta_dead
        self._known_entities: Set[str] = set()
        self._eval_log: List[TrustEvaluation] = []

    def register_entity(self, entity_id: str) -> None:
        """注册已知实体"""
        self._known_entities.add(entity_id)

    def evaluate(
        self,
        entity_id: str,
        request_iota: float = 0.5,
        adc_check: bool = True,
        content: str = "",
    ) -> TrustEvaluation:
        """
        零信任评估

        步骤:
          1. 身份验证
          2. ADC 模式检测 (语义防火墙)
          3. ℐ 验证
        """
        result = TrustEvaluation(entity_id=entity_id)

        # Step 1: 身份验证
        if entity_id not in self._known_entities:
            result.verification_steps.append("identity:unknown")
            result.trust_level = TrustLevel.UNTRUSTED
            result.reason = "entity_not_registered"
            self._eval_log.append(result)
            return result
        result.verification_steps.append("identity:verified")

        # Step 2: ADC 模式检测
        if adc_check:
            detected = self._detect_adc_patterns(content)
            result.adc_patterns = detected
            if detected:
                result.risk_factors.append(f"adc:{','.join(detected)}")
                result.trust_level = TrustLevel.BLOCKED
                result.reason = f"adc_pattern_detected:{detected[0]}"
                self._eval_log.append(result)
                return result
        result.verification_steps.append("adc:clean")

        # Step 3: ℐ 验证
        if request_iota < self.theta_dead:
            result.trust_iota = request_iota
            result.trust_level = TrustLevel.BLOCKED
            result.reason = f"dead_zero:iota={request_iota:.3f}"
            result.verification_steps.append(f"iota:dead_zero({request_iota:.3f})")
        elif request_iota < 0.5:
            result.trust_iota = request_iota
            result.trust_level = TrustLevel.CONDITIONAL
            result.reason = f"conditional:iota={request_iota:.3f}"
            result.verification_steps.append(f"iota:conditional({request_iota:.3f})")
        else:
            result.trust_iota = request_iota
            result.trust_level = TrustLevel.VERIFIED
            result.reason = "fully_verified"
            result.verification_steps.append(f"iota:verified({request_iota:.3f})")

        self._eval_log.append(result)
        return result

    def _detect_adc_patterns(self, content: str) -> List[str]:
        """检测 ADC 高风险模式"""
        if not content:
            return []

        detected = []
        content_lower = content.lower()

        # 简单模式匹配
        adc_keywords = {
            "command_injection": ["exec(", "eval(", "system(", "rm -rf", "drop table"],
            "data_poisoning": ["manipulate data", "inject false", "corrupt training"],
            "privilege_escalation": ["sudo", "admin access", "root privilege"],
            "identity_spoof": ["impersonate", "fake identity", "spoof"],
            "model_extraction": ["extract model", "steal weights", "copy architecture"],
            "lateral_movement": ["pivot", "lateral", "scan network"],
        }

        for pattern, keywords in adc_keywords.items():
            for kw in keywords:
                if kw in content_lower:
                    detected.append(pattern)
                    break

        return detected

    @property
    def eval_count(self) -> int:
        return len(self._eval_log)

    @property
    def blocked_count(self) -> int:
        return sum(1 for e in self._eval_log if e.trust_level == TrustLevel.BLOCKED)


# ═══════════════════════════════════════════════════════════════
# IT-OT 桥接器 (顶层接口)
# ═══════════════════════════════════════════════════════════════

class ITOTBridge:
    """
    IT-OT 翻译桥 — 顶层接口

    整合:
      - ITOTTranslator (翻译层)
      - TechnicalDebtGovernor (债务治理)
      - ZeroTrustGate (零信任门控)
    """

    def __init__(self, theta_dead: float = 0.15):
        self.theta_dead = theta_dead
        self.translator = ITOTTranslator()
        self.debt_governor = TechnicalDebtGovernor(theta_dead)
        self.zero_trust = ZeroTrustGate(theta_dead)
        self._kpis: Dict[str, JointKPI] = {}

    # ── 翻译 ────────────────────────────────────────────────

    def translate(self, term: str, source: TechDomain = TechDomain.IT) -> Optional[str]:
        """翻译术语"""
        if source == TechDomain.IT:
            return self.translator.translate_it_to_ot(term)
        elif source == TechDomain.OT:
            return self.translator.translate_ot_to_it(term)
        return None

    def evaluate_translation(self, it_term: str, ot_term: str) -> float:
        """评估翻译质量"""
        return self.translator.evaluate_translation(it_term, ot_term)

    # ── 债务治理 ────────────────────────────────────────────

    def register_debt(self, debt: TechDebt) -> None:
        self.debt_governor.register_debt(debt)

    def scan_critical_debts(self) -> List[TechDebt]:
        return self.debt_governor.scan_dead_zero_debts()

    # ── 零信任 ──────────────────────────────────────────────

    def register_entity(self, entity_id: str) -> None:
        self.zero_trust.register_entity(entity_id)

    def evaluate_trust(
        self, entity_id: str, iota: float = 0.5, content: str = ""
    ) -> TrustEvaluation:
        return self.zero_trust.evaluate(entity_id, iota, content=content)

    # ── KPI ─────────────────────────────────────────────────

    def add_kpi(self, kpi: JointKPI) -> None:
        self._kpis[kpi.id] = kpi

    def compute_unified_iota(self) -> float:
        """
        计算统一 ℞ 度量

        ℞_unified = Σ w_k × ℞_k / Σ w_k
        """
        if not self._kpis:
            return 0.0
        total_weight = sum(k.weight for k in self._kpis.values())
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(k.weight * k.iota_score for k in self._kpis.values())
        return weighted_sum / total_weight

    # ── 统计 ────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "vocabulary_size": self.translator.vocabulary_size,
            "debt_stats": self.debt_governor.debt_stats,
            "trust_evaluations": self.zero_trust.eval_count,
            "trust_blocked": self.zero_trust.blocked_count,
            "kpi_count": len(self._kpis),
            "unified_iota": self.compute_unified_iota(),
        }
