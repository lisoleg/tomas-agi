"""
EML 上下文注入器 — 构建注入到 LLM 系统提示词中的 EML 执行上下文

基于章锋《开源大模型军备竞赛下的 TOMAS 战略》(2026-06-15):
  "LLM 只是'舌头'，TOMAS 内核（EML + NASGA + 死零/MUS）不可外包。
   每一轮 LLM 调用都需要注入 EML 执行上下文（κ、θ_dead、MUS Tags）以保其不幻、不崩。"

Author: Zhang Feng
Version: 2.0
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EMLContext:
    """EML 执行上下文数据容器"""
    kappa: float = 4.0
    dead_zero_theta: float = 0.15
    mus_tags: List[str] = field(default_factory=lambda: ["Asym!=0 double-exist"])
    kappa_snap_rule: str = "Prefer highest I(e); if tie & MUS => Retain Continuation."
    arbitration_rule: str = "Do NOT hallucinate unsupported claims. If unsure => Request arbitration."

    def to_dict(self) -> dict:
        return {
            "kappa": self.kappa,
            "dead_zero_theta": self.dead_zero_theta,
            "mus_tags": self.mus_tags,
            "kappa_snap_rule": self.kappa_snap_rule,
            "arbitration_rule": self.arbitration_rule,
        }


class EMLInjector:
    """EML 执行上下文注入器

    负责三件事：
    1. 生成 TOMAS v2.0 系统提示词（κ, θ_dead, MUS Tags）
    2. 构建 EML 知识图谱上下文块（concepts + edges）
    3. 包装完整消息列表 [system_eml, system_context, user_query]
    """

    # ── v2.0 系统提示词模板 ──
    SYSPROMPT_TEMPLATE = """# TOMAS EML Execution Context (v2.0)
- kappa (Spectral Fold Depth): {kappa}
- Dead-Zero Threshold (theta_dead): {dead_zero_theta}
  -> If I(e) < theta_dead => Output [DEAD_ZERO_REJECT: Reason]
- MUS Tags Active: {mus_tags}
  -> If paradox pair detected (Asym!=0) => Output [MUS_ACTIVE: <pair>]
- kappa-Snap Rule: {kappa_snap_rule}
- {arbitration_rule}"""

    # ── 上下文块模板 ──
    CONTEXT_TEMPLATE = """以下是 EML 知识图谱中的相关概念和关系（可用于 factual grounding）：

## 匹配概念（按 I 值降序）
{concepts}

## 关联超边
{edges}

请优先基于以上 EML 上下文回答用户问题。如上下文不足，请注明后基于你的知识进行扩展。"""

    def __init__(self,
                 kappa: float = 4.0,
                 dead_zero_theta: float = 0.15,
                 mus_tags: Optional[List[str]] = None,
                 kappa_snap_rule: Optional[str] = None,
                 arbitration_rule: Optional[str] = None):
        """初始化注入器

        Args:
            kappa: 谱折叠深度（κ-Gate 语义剪枝阈值）
            dead_zero_theta: 死零阈值（I(e) < θ_dead 视为死零）
            mus_tags: MUS 激活标签列表
            kappa_snap_rule: κ-Snap 规则
            arbitration_rule: 仲裁规则
        """
        self.ctx = EMLContext(
            kappa=kappa,
            dead_zero_theta=dead_zero_theta,
            mus_tags=mus_tags or ["Asym!=0 double-exist"],
            kappa_snap_rule=kappa_snap_rule or "Prefer highest I(e); if tie & MUS => Retain Continuation.",
            arbitration_rule=arbitration_rule or "Do NOT hallucinate unsupported claims. If unsure => Request arbitration.",
        )

    # ── 公共 API ──

    def build_sysprompt(self) -> str:
        """生成 v2.0 格式的 EML 系统提示词

        Returns:
            格式化的 EML 执行上下文提示词文本
        """
        return self.SYSPROMPT_TEMPLATE.format(
            kappa=self.ctx.kappa,
            dead_zero_theta=self.ctx.dead_zero_theta,
            mus_tags=", ".join(self.ctx.mus_tags),
            kappa_snap_rule=self.ctx.kappa_snap_rule,
            arbitration_rule=self.ctx.arbitration_rule,
        )

    def build_context_block(self,
                            matched_concepts: List[dict],
                            related_edges: List[dict]) -> str:
        """构建 EML 知识图谱上下文块

        Args:
            matched_concepts: 匹配的概念列表 [{"concept": str, "i_val": float}, ...]
            related_edges: 关联的超边列表 [{"nodes": [str], "i_val": float, "type": str}, ...]

        Returns:
            格式化的 EML 上下文文本（用于作为 system 消息注入 LLM）
        """
        # 格式化概念
        concept_lines = []
        for c in matched_concepts[:10]:  # 最多 10 个概念
            name = c.get("concept", c.get("name", "?"))
            i_val = c.get("i_val", 0)
            concept_lines.append(f"- [{name}] I={i_val:.4f}")

        # 格式化超边
        edge_lines = []
        for e in related_edges[:10]:  # 最多 10 条边
            nodes = e.get("nodes", e.get("vertices", []))
            i_val = e.get("i_val", 0)
            edge_type = e.get("type", e.get("relation", "relates"))
            nodes_str = " → ".join(str(n) for n in nodes)
            edge_lines.append(f"- ({edge_type}) {nodes_str} I={i_val:.4f}")

        return self.CONTEXT_TEMPLATE.format(
            concepts="\n".join(concept_lines) if concept_lines else "(无匹配概念)",
            edges="\n".join(edge_lines) if edge_lines else "(无关联超边)",
        )

    def wrap_query(self,
                   query: str,
                   concepts: Optional[List[dict]] = None,
                   edges: Optional[List[dict]] = None,
                   base_sysprompt: Optional[str] = None) -> List[dict]:
        """构建完整的消息列表 [system_eml, system_context?, user_query]

        Args:
            query: 用户查询文本
            concepts: 匹配的 EML 概念列表
            edges: 关联的 EML 超边列表
            base_sysprompt: 基础系统提示词（如角色定义），可选

        Returns:
            OpenAI 兼容的消息列表 [{"role": "system"|"user", "content": str}, ...]
        """
        messages = []

        # Layer 1: EML 执行上下文（必须）
        messages.append({"role": "system", "content": self.build_sysprompt()})

        # Layer 2: 基础角色提示词（可选）
        if base_sysprompt:
            messages.append({"role": "system", "content": base_sysprompt})

        # Layer 3: EML 知识图谱上下文（有则注入）
        if concepts or edges:
            ctx_block = self.build_context_block(concepts or [], edges or [])
            messages.append({"role": "system", "content": ctx_block})

        # Layer 4: 用户查询
        messages.append({"role": "user", "content": query})

        return messages

    def build_plain_messages(self,
                             query: str,
                             sys_prompt: Optional[str] = None) -> List[dict]:
        """构建简洁消息列表（无 EML 上下文时使用）

        Args:
            query: 用户查询
            sys_prompt: 可选系统提示词

        Returns:
            [system_eml, system_role?, user_query]
        """
        messages = [{"role": "system", "content": self.build_sysprompt()}]
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": query})
        return messages

    # ── 参数更新 ──

    def update_params(self,
                      kappa: Optional[float] = None,
                      dead_zero_theta: Optional[float] = None,
                      mus_tags: Optional[List[str]] = None) -> "EMLInjector":
        """运行时更新注入参数（用于 κ-Gate 动态调节等场景）

        Returns:
            self（支持链式调用）
        """
        if kappa is not None:
            self.ctx.kappa = kappa
        if dead_zero_theta is not None:
            self.ctx.dead_zero_theta = dead_zero_theta
        if mus_tags is not None:
            self.ctx.mus_tags = mus_tags
        return self
