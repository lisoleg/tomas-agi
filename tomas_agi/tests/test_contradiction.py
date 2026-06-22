"""
TOMAS-MemOS 矛盾检测器三层架构测试

测试 ContradictionDetector 的三层检测架构：
- Layer 1: 否定词检测
- Layer 2: NLP 主谓宾提取
- Layer 3: EML 语义相似度
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, '.')

from sim.contradiction_detector import ContradictionDetector, SPO


# ============================================================
# Layer 1: 否定词检测（5个测试）
# ============================================================

class TestLayer1Negation:
    """Layer 1: 否定词检测"""

    def _make_detector(self):
        return ContradictionDetector(enable_nlp=False, enable_eml=False)

    def test_layer1_negation_detected(self):
        """一个包含否定词，另一个不包含 → 矛盾"""
        detector = self._make_detector()
        assert detector.is_contradictory("心主神明", "心不主神明") is True

    def test_layer1_no_negation(self):
        """两个都不含否定词 → 不矛盾"""
        detector = self._make_detector()
        assert detector.is_contradictory("心主神明", "肝藏血") is False

    def test_layer1_double_negation_different(self):
        """两个都包含否定词，但否定词不同 → 矛盾"""
        detector = self._make_detector()
        # "不是" vs "否认" 是不同的否定词
        assert detector.is_contradictory("这不是对的", "这否认它是错的") is True

    def test_layer1_both_negation_same(self):
        """两个都包含相同的否定词 → 不矛盾（Layer1 不判定）"""
        detector = self._make_detector()
        # 相同否定词集合（都不含"错误"等额外否定词），Layer1 不判矛盾
        result = detector._layer1_negation("这不合适", "这不妥当")
        assert result is False

    def test_layer1_negation_only_r2(self):
        """只有 r2 含否定词 → 矛盾"""
        detector = self._make_detector()
        assert detector.is_contradictory("心主神明", "心不是神明") is True


# ============================================================
# Layer 2: NLP 主谓宾提取（5个测试）
# ============================================================

class TestLayer2NLP:
    """Layer 2: NLP 主谓宾提取"""

    def _make_detector(self):
        return ContradictionDetector(enable_nlp=True, enable_eml=False)

    def test_layer2_opposite_subject(self):
        """主语不同，但谓宾相同 → 矛盾"""
        detector = self._make_detector()
        # "心主神明" vs "肝主神明": 主语不同，谓宾相同
        assert detector.is_contradictory("心主神明", "肝主神明") is True

    def test_layer2_different_object(self):
        """主谓相同，宾语不同 → 矛盾"""
        detector = self._make_detector()
        # "心主神明" vs "心主血脉": 主谓相同，宾语不同
        assert detector.is_contradictory("心主神明", "心主血脉") is True

    def test_layer2_no_contradiction(self):
        """无矛盾关系 → 不矛盾"""
        detector = self._make_detector()
        assert detector.is_contradictory("心主神明", "肝藏血") is False

    def test_extract_spo_basic(self):
        """提取 SPO 基本功能"""
        detector = self._make_detector()
        spo = detector._extract_spo("心主神明")

        assert spo.subject == "心"
        assert spo.predicate == "主"
        assert spo.object == "神明"

    def test_extract_spo_short(self):
        """短文本 SPO 提取（2字符→整体主语）"""
        detector = self._make_detector()
        spo = detector._extract_spo("AB")

        assert spo.subject == "AB"
        assert spo.predicate == ""
        assert spo.object == ""


# ============================================================
# Layer 3: EML 语义相似度（7个测试）
# ============================================================

class TestLayer3EML:
    """Layer 3: EML 语义相似度检测"""

    def _make_detector_no_eml(self):
        return ContradictionDetector(enable_nlp=False, enable_eml=False)

    def _make_detector_with_fake_eml(self):
        """创建带假 EML 数据的检测器（用于测试 Layer3 逻辑）"""
        detector = ContradictionDetector(enable_nlp=False, enable_eml=True)
        # 手动设置 eml_loaded 和相关结构
        detector.eml_loaded = True
        detector._concept_to_vids = {
            "心": [1],
            "肝": [2],
            "神明": [3],
        }
        detector._edge_asym = {
            (1, 2): 0.5,
            (2, 1): 0.5,
        }
        detector._concept_adj = {
            "心": {"肝"},
            "肝": {"心"},
        }
        return detector

    def test_layer3_disabled_without_eml(self):
        """未启用 EML 时 Layer3 不检测"""
        detector = self._make_detector_no_eml()
        assert detector._layer3_eml("心主神明", "肝藏血") is False

    def test_layer3_no_concepts(self):
        """关系文本中无 EML 已知概念 → 不矛盾"""
        detector = self._make_detector_with_fake_eml()
        # "XYZ" 不在概念词典中
        assert detector._layer3_eml("XYZ123", "ABC456") is False

    def test_layer3_extract_concepts(self):
        """从关系文本中提取概念"""
        detector = self._make_detector_with_fake_eml()
        concepts = detector._extract_named_concepts("心主神明")

        assert "心" in concepts
        assert "神明" in concepts

    def test_layer3_eml_not_loaded(self):
        """EML 未加载时 is_contradictory 不触发 Layer3"""
        detector = ContradictionDetector(enable_nlp=False, enable_eml=True)
        detector.eml_loaded = False
        # 即使 enable_eml=True，eml_loaded=False 也不检测
        assert detector._layer3_eml("心主神明", "肝藏血") is False

    def test_layer3_init_no_file(self):
        """EML 文件路径不存在 → eml_loaded=False"""
        detector = ContradictionDetector(
            enable_nlp=False,
            enable_eml=True,
            eml_path="nonexistent_file.eml",
        )
        assert detector.eml_loaded is False

    def test_layer3_init_bad_path(self):
        """EML 路径为目录 → eml_loaded=False"""
        detector = ContradictionDetector(
            enable_nlp=False,
            enable_eml=True,
            eml_path="/nonexistent/path/",
        )
        assert detector.eml_loaded is False

    def test_is_contradictory_integration(self):
        """集成测试：is_contradictory 主入口"""
        detector = self._make_detector_no_eml()
        # 仅 Layer1 触发
        assert detector.is_contradictory("心主神明", "心不主神明") is True
        assert detector.is_contradictory("心主神明", "肝藏血") is False


# ============================================================
# 集成 + 基础测试（2个测试）
# ============================================================

class TestContradictionIntegration:
    """矛盾检测器集成测试"""

    def test_contradiction_flow(self):
        """完整矛盾检测流程"""
        detector = ContradictionDetector(enable_nlp=True, enable_eml=False)

        # 测试1: 否定词触发
        result1 = detector.is_contradictory("这是对的", "这不是对的")
        assert result1 is True

        # 测试2: 不矛盾
        result2 = detector.is_contradictory("心主神明", "肝藏血")
        assert result2 is False

    def test_spo_equality(self):
        """SPO 相等性判断"""
        spo1 = SPO(subject="心", predicate="主", object="神明")
        spo2 = SPO(subject="心", predicate="主", object="神明")
        spo3 = SPO(subject="肝", predicate="主", object="神明")

        assert spo1 == spo2
        assert spo1 != spo3
