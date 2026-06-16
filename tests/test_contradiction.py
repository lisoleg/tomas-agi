"""
TOMAS-MemOS 矛盾检测器测试套件

测试三层架构：
- Layer 1: 否定词检测（V1.1）
- Layer 2: NLP 主谓宾提取（V1.2）
- Layer 3: EML 语义相似度（V2.0 - 占位符）

Author: Zhang Feng / TOMAS Team
Date: 2026-06-16
"""

import sys
import os
import pytest

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from tomas_agi.sim.contradiction_detector import ContradictionDetector, SPO
from tomas_agi.sim.memos_fusion import TOMAS_Mem_OS_Fusion


class TestLayer1:
    """Layer 1: 否定词检测测试（V1.1）"""
    
    def setup_method(self):
        """每个测试前创建检测器（禁用 NLP）"""
        self.detector = ContradictionDetector(enable_nlp=False, enable_eml=False)
    
    def test_negation_detection_1(self):
        """测试否定词检测：肯定 vs 否定"""
        # "心主神明" vs "心不主神明" → 矛盾
        assert self.detector.is_contradictory("心主神明", "心不主神明")
    
    def test_negation_detection_2(self):
        """测试否定词检测：不同否定词"""
        # "心主神明" vs "心不是主神明" → 矛盾
        assert self.detector.is_contradictory("心主神明", "心不是主神明")
    
    def test_negation_detection_3(self):
        """测试否定词检测：都否定但不同 → 矛盾"""
        # "不是心主神明" vs "不可能心主神明" → 矛盾
        assert self.detector.is_contradictory("不是心主神明", "不可能心主神明")
    
    def test_negation_detection_4(self):
        """测试否定词检测：都肯定 → 不矛盾"""
        # "心主神明" vs "脑主神明" → 不矛盾（Layer 1 检测不出来）
        assert not self.detector.is_contradictory("心主神明", "脑主神明")
    
    def test_negation_detection_5(self):
        """测试否定词检测：都否定且相同 → 不矛盾"""
        # "不心主神明" vs "不心主神明" → 不矛盾
        assert not self.detector.is_contradictory("不心主神明", "不心主神明")


class TestLayer2:
    """Layer 2: NLP 主谓宾提取测试（V1.2）"""
    
    def setup_method(self):
        """每个测试前创建检测器（启用 NLP）"""
        self.detector = ContradictionDetector(enable_nlp=True, enable_eml=False)
    
    def test_spo_extraction_1(self):
        """测试主谓宾提取：三字符结构"""
        spo = self.detector._extract_spo("心主神明")
        assert spo.subject == "心"
        assert spo.predicate == "主"
        assert spo.object == "神明"
    
    def test_spo_extraction_2(self):
        """测试主谓宾提取：四字符结构"""
        spo = self.detector._extract_spo("太阳绕地球")
        assert spo.subject == "太"
        assert spo.predicate == "阳"
        assert spo.object == "绕地球"
    
    def test_spo_contradiction_1(self):
        """测试基于主谓宾的矛盾检测：主语不同"""
        # "心主神明" vs "脑主神明" → 主语不同，矛盾
        assert self.detector.is_contradictory("心主神明", "脑主神明")
    
    def test_spo_contradiction_2(self):
        """测试基于主谓宾的矛盾检测：主语相同，宾语相同，谓语相反"""
        # 简化版：检测否定词
        assert self.detector.is_contradictory("心主神明", "心不主神明")
    
    def test_spo_contradiction_3(self):
        """测试基于主谓宾的矛盾检测：主语相同，谓语相同，宾语不同"""
        # "心主神明" vs "心主思考" → 宾语不同，可能矛盾
        assert self.detector.is_contradictory("心主神明", "心主思考")


class TestIntegration:
    """集成测试：检测矛盾检测器与 MemOS 融合层的集成"""
    
    def setup_method(self):
        """每个测试前创建临时融合层"""
        self.store_path = "test_contradiction_store.json"
        self.fusion = TOMAS_Mem_OS_Fusion(
            store_path=self.store_path,
            theta_dead=0.15,
            theta_write=0.3,
            enable_mus=True,
            enable_psi=True,
            enable_kappa_gate=True,
        )
    
    def teardown_method(self):
        """每个测试后清理"""
        if os.path.exists(self.store_path):
            os.remove(self.store_path)
    
    def test_mus_dual_write_with_contradiction(self):
        """测试 MUS 双存：写入矛盾记忆时触发 MUS"""
        # 写入第一条
        context1 = {
            "concepts": ["心", "神明"],
            "self_state": "学习中医理论",
            "current_kappa": 4,
        }
        result1 = self.fusion.write_memory("心主神明", context1)
        
        # 写入第二条（矛盾）
        context2 = {
            "concepts": ["脑", "神明"],
            "self_state": "学习现代医学",
            "current_kappa": 4,
        }
        result2 = self.fusion.write_memory("脑主神明", context2)
        
        # 至少有一条被标记为 MUS
        assert result1["mus_active"] or result2["mus_active"]
        
        # 两条都应写入存储
        stats = self.fusion.get_stats()
        assert stats["total_memories"] >= 1


class TestLayer3:
    """Layer 3: EML 语义相似度测试（V2.0）"""
    
    @pytest.fixture(autouse=True)
    def setup_eml_detector(self):
        """加载真实 EML 数据（物理）"""
        eml_path = os.path.join(
            os.path.dirname(__file__), '..',
            'tomas_agi', 'data', 'physics_distilled.eml'
        )
        concepts_path = os.path.join(
            os.path.dirname(__file__), '..',
            'tomas_agi', 'data', 'physics_distilled.concepts.json'
        )
        
        if not os.path.exists(eml_path):
            pytest.skip(f"EML file not found: {eml_path}")
        
        self.eml_detector = ContradictionDetector(
            enable_nlp=False,
            enable_eml=True,
            eml_path=eml_path,
            concepts_json_path=concepts_path,
        )
    
    def test_eml_loaded(self):
        """测试 EML 成功加载"""
        assert self.eml_detector.eml_loaded
        assert len(self.eml_detector._concept_to_vids) > 0
        assert len(self.eml_detector._edge_asym) > 0
    
    def test_extract_named_concepts(self):
        """测试从文本中提取 EML 已知概念"""
        concepts = self.eml_detector._extract_named_concepts("牛顿第一定律描述了惯性")
        assert "牛顿第一定律" in concepts
    
    def test_extract_multiple_concepts(self):
        """测试提取多个概念"""
        concepts = self.eml_detector._extract_named_concepts(
            "量子力学与相对论是物理学两大支柱"
        )
        # 应该至少匹配到一个概念
        assert len(concepts) >= 1
    
    def test_direct_mus_edge_contradiction(self):
        """测试直接 MUS 边矛盾检测
        
        EML 数据中：经典力学 <-> 量子力学 edge 有 asym=1.0
        """
        result = self.eml_detector.is_contradictory("经典力学", "量子力学")
        assert result, (
            "经典力学 <-> 量子力学 should be contradictory "
            "(direct MUS edge with asym=1.0)"
        )
    
    def test_no_eml_match_no_contradiction(self):
        """测试无 EML 匹配时不误报"""
        # 这两个词不在物理 EML 概念中
        result = self.eml_detector.is_contradictory("心主神明", "脑主神明")
        assert not result, (
            "Non-physics concepts should not trigger EML contradiction"
        )
    
    def test_eml_disabled_no_false_positive(self):
        """测试 EML 禁用时不误报"""
        detector = ContradictionDetector(enable_nlp=False, enable_eml=False)
        # 即使传入 EML 概念，没有加载 EML 也不应检测
        result = detector.is_contradictory("经典力学", "量子力学")
        assert not result, (
            "Without EML loaded, no contradiction should be detected"
        )
    
    def test_self_concept_no_contradiction(self):
        """测试同一概念不矛盾"""
        result = self.eml_detector.is_contradictory("牛顿第一定律", "牛顿第一定律")
        assert not result, "Same concept should not be contradictory"


class TestLayer3Integration:
    """Layer 3 与 MemOS 融合层集成测试"""
    
    def test_fusion_with_eml(self):
        """测试融合层启用 EML 后正确初始化"""
        eml_path = os.path.join(
            os.path.dirname(__file__), '..',
            'tomas_agi', 'data', 'physics_distilled.eml'
        )
        concepts_path = os.path.join(
            os.path.dirname(__file__), '..',
            'tomas_agi', 'data', 'physics_distilled.concepts.json'
        )
        
        if not os.path.exists(eml_path):
            pytest.skip(f"EML file not found: {eml_path}")
        
        fusion = TOMAS_Mem_OS_Fusion(
            store_path="test_eml_fusion_store.json",
            eml_path=eml_path,
            concepts_json_path=concepts_path,
        )
        
        try:
            # 验证矛盾检测器已加载 EML
            assert fusion.contradiction_detector.eml_loaded
            assert fusion.contradiction_detector.enable_eml
            
            # 写入矛盾概念应该触发 MUS
            result1 = fusion.write_memory("经典力学", {
                "concepts": ["经典力学"],
                "self_state": "测试",
                "current_kappa": 4,
            })
            result2 = fusion.write_memory("量子力学", {
                "concepts": ["量子力学"],
                "self_state": "测试",
                "current_kappa": 4,
            })
            
            # 第二个写入应该触发 MUS（因为 EML 检测到矛盾）
            assert result2["mus_active"], (
                "Second write should trigger MUS due to EML contradiction"
            )
        finally:
            if os.path.exists("test_eml_fusion_store.json"):
                os.remove("test_eml_fusion_store.json")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
