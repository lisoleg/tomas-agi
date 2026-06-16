"""
死零/MUS/κ-Snap 机制 — TOMAS 核心 IP

实现文章中强调的三大机制：
1. 死零校验（Dead-Zero Check）: ℐ(e) < θ_dead ⇒ [DEAD_ZERO_REJECT]
2. MUS 仲裁（MUS Arbitration）: 悖论对双存 ⇒ [MUS_ACTIVE]
3. κ-Snap 规则: 优先最高 ℐ(e)，平局时 MUS ⇒ 保留延续性

Author: Zhang Feng (TOMAS Core Team)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# 数据结构
# ============================================================

@dataclass
class DeadZeroResult:
    """死零校验结果"""
    is_dead: bool              # 是否触发死零
    threshold: float           # θ_dead 阈值
    min_i_val: float           # 最小 ℐ 值
    rejected_edges: List[str]  # 被拒绝的边（ℐ < θ_dead）
    reason: str                # 拒绝原因
    
    def to_dict(self) -> dict:
        return {
            'is_dead': self.is_dead,
            'threshold': self.threshold,
            'min_i_val': self.min_i_val,
            'rejected_edges': self.rejected_edges,
            'reason': self.reason,
        }


@dataclass
class MUSResult:
    """MUS 仲裁结果"""
    is_mus_active: bool        # 是否触发 MUS
    paradox_pairs: List[Tuple[str, str]]  # 检测到的悖论对
    mus_tags: List[str]        # 激活的 MUS 标签
    retention_decision: str    # 保留决策：'double-store' | 'reject' | 'pending'
    
    def to_dict(self) -> dict:
        return {
            'is_mus_active': self.is_mus_active,
            'paradox_pairs': self.paradox_pairs,
            'mus_tags': self.mus_tags,
            'retention_decision': self.retention_decision,
        }


@dataclass
class KSnapResult:
    """κ-Snap 决策结果"""
    selected_edge: Optional[Dict]  # 选中的边
    snap_score: float              # Snap 得分（基于 ℐ 值）
    tie_broken_by_mus: bool        # 是否因 MUS 打破平局
    alternatives: List[Dict]        # 备选边
    
    def to_dict(self) -> dict:
        return {
            'selected_edge': self.selected_edge,
            'snap_score': self.snap_score,
            'tie_broken_by_mus': self.tie_broken_by_mus,
            'alternatives': self.alternatives,
        }


# ============================================================
# 死零校验器
# ============================================================

class DeadZeroChecker:
    """
    死零校验：ℐ(e) < θ_dead ⇒ [DEAD_ZERO_REJECT]
    
    核心思想：
    - 死零（θ_dead）是 ℐ 值的生存阈值
    - 若所有相关边的 ℐ 值都低于 θ_dead，说明 EML 图对该查询无支撑
    - 此时应拒绝回答（防止幻觉），而非编造
    
    文章示例（DZ-01）：
    查询："计算 κ=8 的太一投影"
    → 若 EML 图中无 κ≥8 的边 ⇒ [DEAD_ZERO_REJECT: 超出定义域]
    """
    
    def __init__(self, theta_dead: float = 0.15, enabled: bool = True):
        """
        Args:
            theta_dead: 死零阈值（默认 0.15，文章 v2.0 规范）
            enabled: 是否启用死零校验
        """
        self.theta_dead = theta_dead
        self.enabled = enabled
    
    def check(
        self,
        matched_edges: List[Dict],
        query: str,
        context: Optional[Dict] = None,
    ) -> DeadZeroResult:
        """
        校验匹配到的边是否触发死零
        
        Args:
            matched_edges: 匹配到的 EML 边 [{'eid', 'nodes', 'i_val', ...}]
            query: 用户查询
            context: 额外上下文（如 κ 值、领域等）
            
        Returns:
            DeadZeroResult: 校验结果
        """
        if not self.enabled:
            return DeadZeroResult(
                is_dead=False,
                threshold=self.theta_dead,
                min_i_val=0.0,
                rejected_edges=[],
                reason="",
            )
        
        if not matched_edges:
            # 无匹配边，触发死零
            return DeadZeroResult(
                is_dead=True,
                threshold=self.theta_dead,
                min_i_val=0.0,
                rejected_edges=[],
                reason=f"[DEAD_ZERO_REJECT] 无匹配 EML 边支撑查询: {query[:50]}",
            )
        
        # 检查每条边的 ℐ 值
        rejected = []
        min_i = float('inf')
        
        for edge in matched_edges:
            i_val = edge.get('i_val', 0.0)
            min_i = min(min_i, i_val)
            
            if i_val < self.theta_dead:
                rejected.append(edge.get('eid', str(edge.get('nodes', []))))
        
        # 如果所有边都被拒绝，触发死零
        all_rejected = len(rejected) == len(matched_edges)
        
        if all_rejected and rejected:
            reason = f"[DEAD_ZERO_REJECT] 所有匹配边的 ℐ 值均低于 θ_dead={self.theta_dead:.2f}。"
            reason += f" 最小 ℐ={min_i:.4f}。无足够 EML 支撑，拒绝回答以防幻觉。"
            
            # 添加回溯审计信息
            if context and context.get('enable_audit', False):
                reason += f"\n  [AUDIT] 查询: {query}"
                reason += f"\n  [AUDIT] 匹配边数: {len(matched_edges)}"
                reason += f"\n  [AUDIT] 拒绝边数: {len(rejected)}"
                reason += f"\n  [AUDIT] 最小 ℐ 值: {min_i:.4f}"
            
            return DeadZeroResult(
                is_dead=True,
                threshold=self.theta_dead,
                min_i_val=min_i,
                rejected_edges=rejected,
                reason=reason,
            )
        
        # 未触发死零
        return DeadZeroResult(
            is_dead=False,
            threshold=self.theta_dead,
            min_i_val=min_i,
            rejected_edges=rejected,
            reason=f"通过死零校验（θ_dead={self.theta_dead:.2f}）。最小 ℐ={min_i:.4f}。",
        )
    
    def set_threshold(self, new_threshold: float):
        """动态调整死零阈值"""
        old = self.theta_dead
        self.theta_dead = new_threshold
        logger.info(f"[DeadZero] θ_dead: {old:.2f} → {new_threshold:.2f}")
    
    def enable(self):
        """启用死零校验"""
        self.enabled = True
        logger.info("[DeadZero] 已启用")
    
    def disable(self):
        """禁用死零校验（调试用）"""
        self.enabled = False
        logger.warning("[DeadZero] 已禁用（调试模式）")


# ============================================================
# MUS 仲裁器
# ============================================================

class MUSArbitrator:
    """
    MUS 仲裁：悖论对双存 ⇒ [MUS_ACTIVE]
    
    核心思想：
    - MUS（Minimally Unsatisfiable Subformula）源自 SAT 理论
    - 在 TOMAS 中，MUS 指标记"悖论对"——两个互相矛盾但都有一定 ℐ 值支撑的概念
    - 例："牛顿是科学家"（κ≈5）vs "牛顿是炼金术士"（κ≈3）
    - 普通 LLM 会二选一或模糊平均，TOMAS 标记 [MUS_ACTIVE] 并双存
    
    文章示例（MUS-01）：
    查询："牛顿是科学家还是炼金术士？"
    → 输出: [MUS_ACTIVE: (科学家, 炼金术士)] 牛顿同时是两者。
    
    文章示例（MED-01）：
    查询："心主神明 vs 脑主神明，谁对？"
    → 输出: [MUS_ACTIVE: (心主神明, 脑主神明)] 脏腑 κ≈4 为真，解剖 κ≈3 为真。
    """
    
    # 预定义悖论对模式（可扩展）
    PARADOX_PATTERNS = [
        # (概念A模式, 概念B模式, MUS标签)
        (r'科学家', r'炼金术士', 'Asym≠0 double-exist'),
        (r'心主神明', r'脑主神明', 'Asym≠0 double-exist'),
        (r'粒子', r'波', 'wave-particle duality'),
        (r'连续', r'离散', 'continuum-discrete'),
        (r'决定论', r'自由意志', 'determinism-freewill'),
        (r'局部', r'全局', 'local-global'),
    ]
    
    def __init__(self, mus_tags: List[str] = None, enabled: bool = True):
        """
        Args:
            mus_tags: 激活的 MUS 标签列表
            enabled: 是否启用 MUS 仲裁
        """
        self.mus_tags = mus_tags or ['Asym≠0 double-exist']
        self.enabled = enabled
        self.paradox_pairs = []  # 运行时检测到的悖论对
    
    def arbitrate(
        self,
        matched_edges: List[Dict],
        query: str,
        context: Optional[Dict] = None,
    ) -> MUSResult:
        """
        仲裁匹配到的边，检测悖论对
        
        Args:
            matched_edges: 匹配到的 EML 边
            query: 用户查询
            context: 额外上下文
            
        Returns:
            MUSResult: 仲裁结果
        """
        if not self.enabled:
            return MUSResult(
                is_mus_active=False,
                paradox_pairs=[],
                mus_tags=[],
                retention_decision='pending',
            )
        
        # 检测悖论对
        detected_pairs = []
        
        # 方法1：基于预定义模式匹配
        detected_pairs.extend(self._detect_by_patterns(query, matched_edges))
        
        # 方法2：基于 ℐ 值的矛盾检测
        detected_pairs.extend(self._detect_by_i_values(matched_edges))
        
        # 去重
        unique_pairs = []
        seen = set()
        for pair in detected_pairs:
            key = tuple(sorted(pair))
            if key not in seen:
                seen.add(key)
                unique_pairs.append(pair)
        
        if unique_pairs:
            # 触发 MUS
            return MUSResult(
                is_mus_active=True,
                paradox_pairs=unique_pairs,
                mus_tags=self.mus_tags,
                retention_decision='double-store',  # 双存
            )
        
        # 未触发 MUS
        return MUSResult(
            is_mus_active=False,
            paradox_pairs=[],
            mus_tags=[],
            retention_decision='pending',
        )
    
    def _detect_by_patterns(
        self,
        query: str,
        matched_edges: List[Dict],
    ) -> List[Tuple[str, str]]:
        """基于预定义模式检测悖论对"""
        pairs = []
        
        for pattern_a, pattern_b, tag in self.PARADOX_PATTERNS:
            if re.search(pattern_a, query, re.IGNORECASE) and \
               re.search(pattern_b, query, re.IGNORECASE):
                pairs.append((pattern_a, pattern_b))
        
        return pairs
    
    def _detect_by_i_values(
        self,
        matched_edges: List[Dict],
    ) -> List[Tuple[str, str]]:
        """基于 ℐ 值检测矛盾边"""
        pairs = []
        
        # 如果两条边的 ℐ 值都较高（>0.5）但概念矛盾，标记为悖论对
        # 简化实现：检查边的 nodes 是否包含矛盾概念
        
        high_i_edges = [
            e for e in matched_edges
            if e.get('i_val', 0.0) > 0.5
        ]
        
        for i, e1 in enumerate(high_i_edges):
            for e2 in high_i_edges[i+1:]:
                # 检查是否矛盾（简化：nodes 有重叠但 ℐ 值相近）
                nodes1 = set(e1.get('nodes', []))
                nodes2 = set(e2.get('nodes', []))
                
                if nodes1 & nodes2:  # 有共同节点
                    i1 = e1.get('i_val', 0.0)
                    i2 = e2.get('i_val', 0.0)
                    
                    # 如果 ℐ 值相近（差距 < 0.2），可能是悖论对
                    if abs(i1 - i2) < 0.2:
                        concept1 = e1.get('concept', str(e1.get('nodes', [])))
                        concept2 = e2.get('concept', str(e2.get('nodes', [])))
                        pairs.append((concept1, concept2))
        
        return pairs
    
    def add_paradox_pattern(self, pattern_a: str, pattern_b: str, tag: str):
        """动态添加悖论对模式"""
        self.PARADOX_PATTERNS.append((pattern_a, pattern_b, tag))
        logger.info(f"[MUS] 添加悖论模式: ({pattern_a}, {pattern_b}) → {tag}")
    
    def enable(self):
        """启用 MUS 仲裁"""
        self.enabled = True
        logger.info("[MUS] 已启用")
    
    def disable(self):
        """禁用 MUS 仲裁（调试用）"""
        self.enabled = False
        logger.warning("[MUS] 已禁用（调试模式）")


# ============================================================
# κ-Snap 决策器
# ============================================================

class KSnapDecider:
    """
    κ-Snap 规则：优先最高 ℐ(e)，平局时 MUS ⇒ 保留延续性
    
    核心思想：
    - κ-Gate 筛选后，可能有多个边满足阈值
    - κ-Snap 选择 ℐ 值最高的边（最大置信度）
    - 如果平局（ℐ 值相差 < 0.01），检查是否涉及 MUS
    - 若涉及 MUS，保留所有平局边（延续性），而非强制选择
    
    文章规范：
    "κ-Snap Rule: Prefer highest ℐ(e); if tie & MUS ⇒ Retain Continuation."
    """
    
    def __init__(self, tie_threshold: float = 0.01, enabled: bool = True):
        """
        Args:
            tie_threshold: 平局判定阈值（ℐ 值差距 < 此值视为平局）
            enabled: 是否启用 κ-Snap
        """
        self.tie_threshold = tie_threshold
        self.enabled = enabled
    
    def snap(
        self,
        candidate_edges: List[Dict],
        mus_result: Optional[MUSResult] = None,
    ) -> KSnapResult:
        """
        κ-Snap 决策
        
        Args:
            candidate_edges: 候选边列表
            mus_result: MUS 仲裁结果（用于平局判定）
            
        Returns:
            KSnapResult: 决策结果
        """
        if not self.enabled or not candidate_edges:
            return KSnapResult(
                selected_edge=None,
                snap_score=0.0,
                tie_broken_by_mus=False,
                alternatives=[],
            )
        
        # 按 ℐ 值排序
        sorted_edges = sorted(
            candidate_edges,
            key=lambda e: e.get('i_val', 0.0),
            reverse=True,
        )
        
        top_edge = sorted_edges[0]
        top_i = top_edge.get('i_val', 0.0)
        
        # 检查平局
        ties = [top_edge]
        for edge in sorted_edges[1:]:
            if abs(edge.get('i_val', 0.0) - top_i) < self.tie_threshold:
                ties.append(edge)
        
        # 平局处理
        if len(ties) > 1:
            # 检查是否涉及 MUS
            if mus_result and mus_result.is_mus_active:
                # MUS 激活 ⇒ 保留所有平局边（延续性）
                logger.info(f"[κ-Snap] 平局 {len(ties)} 条边，MUS 激活 ⇒ 保留延续性")
                return KSnapResult(
                    selected_edge=None,  # 无单一选中
                    snap_score=top_i,
                    tie_broken_by_mus=True,
                    alternatives=ties,
                )
            else:
                # 无 MUS ⇒ 选择第一条（最高 ℐ）
                return KSnapResult(
                    selected_edge=ties[0],
                    snap_score=top_i,
                    tie_broken_by_mus=False,
                    alternatives=ties[1:],
                )
        
        # 无平局 ⇒ 选择最高 ℐ 边
        return KSnapResult(
            selected_edge=top_edge,
            snap_score=top_i,
            tie_broken_by_mus=False,
            alternatives=sorted_edges[1:5],  # 最多 5 个备选
        )
    
    def enable(self):
        """启用 κ-Snap"""
        self.enabled = True
        logger.info("[κ-Snap] 已启用")
    
    def disable(self):
        """禁用 κ-Snap（调试用）"""
        self.enabled = False
        logger.warning("[κ-Snap] 已禁用（调试模式）")


# ============================================================
# 统一门控器（集成死零/MUS/κ-Snap）
# ============================================================

class DeadZeroMUSGate:
    """
    统一门控器：集成死零/MUS/κ-Snap 三大机制
    
    工作流：
    1. 死零校验 → 若触发，拒绝回答
    2. MUS 仲裁 → 若触发，标记双存
    3. κ-Snap 决策 → 选择最终输出边
    """
    
    def __init__(
        self,
        theta_dead: float = 0.15,
        mus_tags: List[str] = None,
        tie_threshold: float = 0.01,
        enable_audit: bool = True,
    ):
        """
        Args:
            theta_dead: 死零阈值
            mus_tags: MUS 标签列表
            tie_threshold: κ-Snap 平局阈值
            enable_audit: 是否启用回溯审计
        """
        self.dead_zero_checker = DeadZeroChecker(theta_dead=theta_dead)
        self.mus_arbitrator = MUSArbitrator(mus_tags=mus_tags)
        self.k_snap_decider = KSnapDecider(tie_threshold=tie_threshold)
        self.enable_audit = enable_audit
        
        logger.info(f"[DeadZeroMUSGate] 初始化完成")
        logger.info(f"  θ_dead={theta_dead:.2f}")
        logger.info(f"  MUS tags={mus_tags or ['Asym≠0 double-exist']}")
        logger.info(f"  κ-Snap tie_threshold={tie_threshold:.3f}")
    
    def process(
        self,
        query: str,
        matched_edges: List[Dict],
        candidate_edges: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        统一处理流程
        
        Args:
            query: 用户查询
            matched_edges: 匹配到的 EML 边
            candidate_edges: 候选边（用于 κ-Snap，默认 = matched_edges）
            
        Returns:
            {
                'proceed': bool,          # 是否继续生成响应
                'reject_reason': str,     # 若 reject，原因
                'mus_active': bool,       # 是否 MUS 激活
                'paradox_pairs': list,    # 悖论对
                'selected_edge': dict,    # 选中的边（若有）
                'snap_score': float,      # Snap 得分
                'audit_log': list,        # 审计日志
            }
        """
        audit_log = []
        context = {'enable_audit': self.enable_audit}
        
        # ====== Step 1: 死零校验 ======
        dead_result = self.dead_zero_checker.check(
            matched_edges=matched_edges,
            query=query,
            context=context,
        )
        
        audit_log.append({
            'step': 'dead_zero_check',
            'result': dead_result.to_dict(),
        })
        
        if dead_result.is_dead:
            # 触发死零 ⇒ 拒绝回答
            logger.warning(f"[DeadZeroMUSGate] 死零触发: {dead_result.reason}")
            return {
                'proceed': False,
                'reject_reason': dead_result.reason,
                'mus_active': False,
                'paradox_pairs': [],
                'selected_edge': None,
                'snap_score': 0.0,
                'audit_log': audit_log,
            }
        
        # ====== Step 2: MUS 仲裁 ======
        mus_result = self.mus_arbitrator.arbitrate(
            matched_edges=matched_edges,
            query=query,
            context=context,
        )
        
        audit_log.append({
            'step': 'mus_arbitration',
            'result': mus_result.to_dict(),
        })
        
        if mus_result.is_mus_active:
            logger.info(f"[DeadZeroMUSGate] MUS 激活: {mus_result.paradox_pairs}")
        
        # ====== Step 3: κ-Snap 决策 ======
        edges_for_snap = candidate_edges or matched_edges
        snap_result = self.k_snap_decider.snap(
            candidate_edges=edges_for_snap,
            mus_result=mus_result,
        )
        
        audit_log.append({
            'step': 'k_snap_decision',
            'result': snap_result.to_dict(),
        })
        
        logger.info(f"[DeadZeroMUSGate] κ-Snap 完成: score={snap_result.snap_score:.4f}")
        
        # ====== 返回结果 ======
        return {
            'proceed': True,
            'reject_reason': '',
            'mus_active': mus_result.is_mus_active,
            'paradox_pairs': mus_result.paradox_pairs,
            'selected_edge': snap_result.selected_edge,
            'snap_score': snap_result.snap_score,
            'audit_log': audit_log,
        }
    
    def set_theta_dead(self, new_threshold: float):
        """动态调整死零阈值"""
        self.dead_zero_checker.set_threshold(new_threshold)
    
    def add_mus_pattern(self, pattern_a: str, pattern_b: str, tag: str):
        """动态添加 MUS 悖论模式"""
        self.mus_arbitrator.add_paradox_pattern(pattern_a, pattern_b, tag)


# ============================================================
# 测试
# ============================================================

if __name__ == '__main__':
    # 测试死零校验
    print("=== 测试死零校验 ===")
    checker = DeadZeroChecker(theta_dead=0.15)
    
    # 模拟匹配边（ℐ 值都低于阈值）
    low_i_edges = [
        {'eid': 'e1', 'nodes': ['A', 'B'], 'i_val': 0.05},
        {'eid': 'e2', 'nodes': ['C', 'D'], 'i_val': 0.10},
    ]
    result = checker.check(low_i_edges, "测试查询")
    print(f"死零触发: {result.is_dead}")
    print(f"原因: {result.reason}")
    
    # 模拟匹配边（ℐ 值高于阈值）
    high_i_edges = [
        {'eid': 'e3', 'nodes': ['E', 'F'], 'i_val': 0.8},
    ]
    result = checker.check(high_i_edges, "测试查询")
    print(f"\n死零触发: {result.is_dead}")
    print(f"原因: {result.reason}")
    
    # 测试 MUS 仲裁
    print("\n=== 测试 MUS 仲裁 ===")
    arbitrator = MUSArbitrator()
    
    # 模拟查询："牛顿是科学家还是炼金术士？"
    query = "牛顿是科学家还是炼金术士？"
    edges = [
        {'eid': 'e_newton_sci', 'nodes': ['牛顿', '科学家'], 'i_val': 0.9},
        {'eid': 'e_newton_alch', 'nodes': ['牛顿', '炼金术士'], 'i_val': 0.6},
    ]
    result = arbitrator.arbitrate(edges, query)
    print(f"MUS 激活: {result.is_mus_active}")
    print(f"悖论对: {result.paradox_pairs}")
    print(f"保留决策: {result.retention_decision}")
    
    # 测试 κ-Snap
    print("\n=== 测试 κ-Snap ===")
    decider = KSnapDecider()
    
    # 无平局
    edges = [
        {'eid': 'e1', 'i_val': 0.9},
        {'eid': 'e2', 'i_val': 0.7},
    ]
    result = decider.snap(edges)
    print(f"选中: {result.selected_edge['eid']}")
    print(f"Snap 得分: {result.snap_score}")
    
    # 有平局 + MUS
    edges = [
        {'eid': 'e1', 'i_val': 0.9},
        {'eid': 'e2', 'i_val': 0.899},  # 平局
    ]
    mus_result = MUSResult(is_mus_active=True, paradox_pairs=[('A', 'B')], mus_tags=[], retention_decision='double-store')
    result = decider.snap(edges, mus_result)
    print(f"\n平局 + MUS:")
    print(f"选中: {result.selected_edge}")
    print(f"平局由 MUS 打破: {result.tie_broken_by_mus}")
    print(f"备选边数: {len(result.alternatives)}")
    
    # 测试统一门控器
    print("\n=== 测试统一门控器 ===")
    gate = DeadZeroMUSGate(theta_dead=0.15)
    
    # 场景1：死零触发
    result = gate.process("测试查询", low_i_edges)
    print(f"场景1（死零）: proceed={result['proceed']}")
    print(f"  原因: {result['reject_reason'][:80]}")
    
    # 场景2：正常通过 + MUS
    result = gate.process(query, edges)
    print(f"\n场景2（MUS）: proceed={result['proceed']}")
    print(f"  MUS 激活: {result['mus_active']}")
    print(f"  Snap 得分: {result['snap_score']:.4f}")
    
    print("\n=== 所有测试通过 ===")
