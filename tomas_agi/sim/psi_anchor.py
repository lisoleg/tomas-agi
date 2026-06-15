"""
ψ-锚（Self-Snapshot）数据结构
Author: Zhang Feng / TOMAS Team
Date: 2026-06-16

ψ-锚让记忆从"用户说…"变成"我记得我当时怎么想"。
每个 ψ-锚附加到 EML 超边上，记录写入时的自我状态。
"""

import json
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class PsiAnchor:
    """
    ψ-锚数据结构
    
    字段说明：
    - self_state: 写入时 AI 的元意向（如"持有'照顾用户健康'的元意向"）
    - kappa_at_write: 写入时的 κ 值（语境深度）
    - timestamp: 写入时间戳（ISO 8601 格式）
    - emotion_tone: 写入时的情感色调（可选，如"平静"、"关切"）
    - continuation_branch: 是否属于 MUS 潜存分支（可选）
    """
    self_state: str
    kappa_at_write: int
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    emotion_tone: Optional[str] = None
    continuation_branch: Optional[str] = None  # 如 "心主神明" 或 "脑主神明"
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PsiAnchor":
        """从字典反序列化"""
        return cls(**d)
    
    @classmethod
    def from_json(cls, s: str) -> "PsiAnchor":
        """从 JSON 字符串反序列化"""
        return cls.from_dict(json.loads(s))
    
    def __str__(self) -> str:
        lines = [
            f"  self_state: {self.self_state}",
            f"  kappa_at_write: {self.kappa_at_write}",
            f"  timestamp: {self.timestamp}",
        ]
        if self.emotion_tone:
            lines.append(f"  emotion_tone: {self.emotion_tone}")
        if self.continuation_branch:
            lines.append(f"  continuation_branch: {self.continuation_branch}")
        return "\n".join(lines)


class PsiAnchorManager:
    """
    ψ-锚管理器：附加到 EML 超边，或从超边读取
    
    EML 超边的 meta 字段格式：
    {
        "psi_anchor": {
            "self_state": "...",
            "kappa_at_write": 4,
            "timestamp": "2026-06-15T10:30:00"
        }
    }
    """
    
    @staticmethod
    def attach(edge_meta: Dict[str, Any], anchor: PsiAnchor) -> Dict[str, Any]:
        """
        将 ψ-锚附加到超边的 meta 字段
        
        Args:
            edge_meta: 现有 meta 字典（可能为空）
            anchor: ψ-锚实例
            
        Returns:
            更新后的 meta 字典
        """
        if edge_meta is None:
            edge_meta = {}
        edge_meta["psi_anchor"] = anchor.to_dict()
        return edge_meta
    
    @staticmethod
    def extract(edge_meta: Dict[str, Any]) -> Optional[PsiAnchor]:
        """
        从超边的 meta 字段提取 ψ-锚
        
        Args:
            edge_meta: 超边的 meta 字典
            
        Returns:
            ψ-锚实例，若不存在则返回 None
        """
        if not edge_meta:
            return None
        psi_dict = edge_meta.get("psi_anchor")
        if not psi_dict:
            return None
        try:
            return PsiAnchor.from_dict(psi_dict)
        except Exception:
            return None
    
    @staticmethod
    def format_for_response(anchor: PsiAnchor) -> str:
        """
        将 ψ-锚格式化为回答文本（用于 LLM 提示词注入）
        
        Args:
            anchor: ψ-锚实例
            
        Returns:
            格式化的文本片段
        """
        kappa_names = {
            1: "节律感知",
            2: "藏象辨证", 
            3: "经络演进",
            4: "脏腑辨证",
            5: "溯因推理",
            6: "太极回溯",
        }
        kappa_name = kappa_names.get(anchor.kappa_at_write, f"κ={anchor.kappa_at_write}")
        
        parts = [
            f"[ψ-锚]",
            f"我当时持有「{anchor.self_state}」的元意向",
            f"处于{kappa_name}模式（κ={anchor.kappa_at_write}）",
            f"时间：{anchor.timestamp}",
        ]
        if anchor.emotion_tone:
            parts.append(f"情感色调：{anchor.emotion_tone}")
        if anchor.continuation_branch:
            parts.append(f"潜存分支：{anchor.continuation_branch}")
        
        return " | ".join(parts)


# 导出
__all__ = ["PsiAnchor", "PsiAnchorManager"]
