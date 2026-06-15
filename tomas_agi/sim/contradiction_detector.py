"""
TOMAS-MemOS 矛盾检测器（三层架构）

三层检测架构：
- Layer 1: 否定词检测（V1.1）— 快速检测肯定/否定矛盾
- Layer 2: NLP 主谓宾提取（V1.2）— 使用 jieba 提取 SPO 三元组
- Layer 3: EML 语义相似度（V2.0）— 查询 EML 图的 asym 值

Author: Zhang Feng / TOMAS Team
Date: 2026-06-16
"""

from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class SPO:
    """主谓宾三元组"""
    subject: str    # 主语（如 "心"）
    predicate: str  # 谓语（如 "主"）
    object: str     # 宾语（如 "神明"）
    
    def __eq__(self, other):
        if not isinstance(other, SPO):
            return False
        return (self.subject == other.subject and
                self.predicate == other.predicate and
                self.object == other.object)
    
    def __repr__(self):
        return f"SPO({self.subject}, {self.predicate}, {self.object})"


class ContradictionDetector:
    """
    矛盾检测器（三层架构）
    
    层级：
    - Layer 1: 否定词检测（V1.1）
    - Layer 2: NLP 主谓宾提取（V1.2）
    - Layer 3: EML 语义相似度（V2.0）
    """
    
    def __init__(self, enable_nlp: bool = True, enable_eml: bool = False):
        """
        初始化矛盾检测器
        
        Args:
            enable_nlp: 是否启用 NLP 主谓宾提取（V1.2）
            enable_eml: 是否启用 EML 语义相似度（V2.0）
        """
        self.enable_nlp = enable_nlp
        self.enable_eml = enable_eml
        
        # 否定词词典（Layer 1）
        self.negation_words = ["不", "不是", "不可能", "错误", "不对", "否认", "没有", "并非"]
        
        # NLP 工具（Layer 2）
        if enable_nlp:
            self._init_nlp()
        
        # EML 加载器（Layer 3）
        if enable_eml:
            self._init_eml()
    
    def is_contradictory(self, relation1: str, relation2: str) -> bool:
        """
        检测两个关系是否矛盾（主入口）
        
        检测顺序：
        1. Layer 1: 否定词检测（快速）
        2. Layer 2: NLP 主谓宾提取（中等）
        3. Layer 3: EML 语义相似度（慢速）
        
        Args:
            relation1: 第一个关系文本
            relation2: 第二个关系文本
            
        Returns:
            是否矛盾
        """
        # Layer 1: 否定词检测
        if self._layer1_negation(relation1, relation2):
            return True
        
        # Layer 2: NLP 主谓宾提取
        if self.enable_nlp:
            if self._layer2_nlp(relation1, relation2):
                return True
        
        # Layer 3: EML 语义相似度
        if self.enable_eml:
            if self._layer3_eml(relation1, relation2):
                return True
        
        return False
    
    def _layer1_negation(self, relation1: str, relation2: str) -> bool:
        """
        Layer 1: 否定词检测
        
        规则：
        - 如果一个关系包含否定词，另一个不包含 → 可能矛盾
        - 如果两个关系包含不同的否定词组合 → 可能矛盾
        
        Args:
            relation1: 第一个关系文本
            relation2: 第二个关系文本
            
        Returns:
            是否检测到否定词矛盾
        """
        # 提取两个关系中的否定词
        neg1 = [w for w in self.negation_words if w in relation1]
        neg2 = [w for w in self.negation_words if w in relation2]
        
        # 情况1：一个包含否定词，另一个不包含
        if neg1 and not neg2:
            return True
        if neg2 and not neg1:
            return True
        
        # 情况2：两个都包含否定词，但是不同的否定词
        if neg1 and neg2:
            # 如果否定词集合不同，可能矛盾
            if set(neg1) != set(neg2):
                return True
        
        return False
    
    def _init_nlp(self):
        """初始化 NLP 工具（jieba + 规则）"""
        try:
            import jieba
            self.jieba = jieba
            self.jieba_initialized = True
        except ImportError:
            print("Warning: jieba not installed. Run: pip install jieba")
            self.jieba = None
            self.jieba_initialized = False
            self.enable_nlp = False
    
    def _extract_spo(self, relation: str) -> SPO:
        """
        提取主谓宾三元组（简化版）
        
        使用 jieba 分词 + 规则提取：
        - 主语：通常是第一个词（或 "的" 前的词）
        - 谓语：通常是动词或 "主"/"是"/"为" 等
        - 宾语：通常是最后一个词（或 "的" 后的词）
        
        Args:
            relation: 关系文本（如 "心主神明"）
            
        Returns:
            SPO 三元组
        """
        # 简化版：使用规则提取（不依赖 jieba）
        # 适用于中文三字符结构："主语+谓语+宾语"
        
        if len(relation) >= 3:
            # 三字符结构：ABC → 主语=A, 谓语=B, 宾语=C
            subject = relation[0]
            predicate = relation[1]
            obj = relation[2:]
        else:
            # 回退：整个关系作为主语
            subject = relation
            predicate = ""
            obj = ""
        
        return SPO(subject=subject, predicate=predicate, object=obj)
    
    def _layer2_nlp(self, relation1: str, relation2: str) -> bool:
        """
        Layer 2: 基于主谓宾检测矛盾
        
        规则：
        - 如果主语不同，但谓语+宾语相同 → 矛盾
        - 如果主语+宾语相同，但谓语相反 → 矛盾
        - 如果主语+谓语相同，但宾语不同 → 矛盾（新增）
        
        Args:
            relation1: 第一个关系文本
            relation2: 第二个关系文本
            
        Returns:
            是否检测到主谓宾矛盾
        """
        # 提取主谓宾
        spo1 = self._extract_spo(relation1)
        spo2 = self._extract_spo(relation2)
        
        # 规则1：主语不同，但谓语+宾语相同 → 矛盾
        if (spo1.subject != spo2.subject and
            spo1.predicate == spo2.predicate and
            spo1.object == spo2.object):
            return True
        
        # 规则2：主语+宾语相同，但谓语相反 → 矛盾
        if (spo1.subject == spo2.subject and
            spo1.object == spo2.object and
            spo1.predicate != spo2.predicate):
            # 检查谓语是否相反（简化：检查是否一个包含否定词）
            pred1_neg = any(w in spo1.predicate for w in self.negation_words)
            pred2_neg = any(w in spo2.predicate for w in self.negation_words)
            if pred1_neg != pred2_neg:
                return True
        
        # 规则3：主语+谓语相同，但宾语不同 → 矛盾（新增）
        if (spo1.subject == spo2.subject and
            spo1.predicate == spo2.predicate and
            spo1.object != spo2.object):
            return True
        
        return False
    
    def _init_eml(self):
        """初始化 EML 加载器（占位符，V2.0 实现）"""
        # TODO V2.0: 加载 EML 文件（.eml + .concepts.json）
        self.eml_loaded = False
        print("Info: EML semantic similarity (Layer 3) not yet implemented. Will be available in V2.0")
    
    def _layer3_eml(self, relation1: str, relation2: str) -> bool:
        """
        Layer 3: EML 语义相似度检测（占位符）
        
        未来实现：
        - 查询 EML 图计算概念相似度
        - 如果 asym != 0 → 矛盾
        
        Args:
            relation1: 第一个关系文本
            relation2: 第二个关系文本
            
        Returns:
            是否检测到 EML 语义矛盾
        """
        # TODO V2.0: 实现 EML 查询
        # 示例：
        # spo1 = self._extract_spo(relation1)
        # spo2 = self._extract_spo(relation2)
        # asym = query_eml_asym(spo1.subject, spo2.subject)
        # return abs(asym) > 0.01
        
        return False
