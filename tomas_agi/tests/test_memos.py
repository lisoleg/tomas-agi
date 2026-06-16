"""
TOMAS-MemOS 融合层测试

测试 MemoryRecord、MemoryStore、TOMAS_Mem_OS_Fusion 三大组件。
"""

import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, '.')

from tomas_agi.sim.memos_fusion import (
    MemoryRecord,
    MemoryStore,
    TOMAS_Mem_OS_Fusion,
)
from tomas_agi.sim.psi_anchor import PsiAnchor, PsiAnchorManager


# ============================================================
# MemoryRecord 测试
# ============================================================

class TestMemoryRecord:
    """MemoryRecord 序列化/反序列化测试"""

    def _make_record(self):
        psi = PsiAnchor(
            self_state="测试元意向",
            kappa_at_write=4,
            emotion_tone="平静",
            continuation_branch="心主神明",
        )
        return MemoryRecord(
            edge_id="test_edge_001",
            concept_pair=("心", "神明"),
            relation="心主神明",
            i_value=0.85,
            asym=0.0,
            psi_anchor=psi,
            meta={"source": "test"},
        )

    def test_memory_record_to_dict(self):
        """验证 to_dict() 序列化"""
        record = self._make_record()
        d = record.to_dict()

        assert d["edge_id"] == "test_edge_001"
        assert d["concept_pair"] == ["心", "神明"]
        assert d["relation"] == "心主神明"
        assert d["i_value"] == 0.85
        assert d["asym"] == 0.0
        assert d["psi_anchor"] is not None
        assert d["psi_anchor"]["self_state"] == "测试元意向"
        assert d["psi_anchor"]["kappa_at_write"] == 4
        assert d["access_count"] == 0

    def test_memory_record_from_dict(self):
        """验证 from_dict() 反序列化"""
        d = {
            "edge_id": "test_edge_002",
            "concept_pair": ["肝", "藏血"],
            "relation": "肝藏血",
            "i_value": 0.72,
            "asym": 0.0,
            "psi_anchor": {
                "self_state": "元意向2",
                "kappa_at_write": 3,
            },
            "meta": {},
            "created_at": "2026-01-01T00:00:00",
            "last_accessed": "2026-01-01T00:00:00",
            "access_count": 5,
        }
        record = MemoryRecord.from_dict(d)

        assert record.edge_id == "test_edge_002"
        assert record.concept_pair == ("肝", "藏血")
        assert record.relation == "肝藏血"
        assert record.i_value == 0.72
        assert record.psi_anchor is not None
        assert record.psi_anchor.self_state == "元意向2"
        assert record.psi_anchor.kappa_at_write == 3
        assert record.access_count == 5

    def test_memory_record_roundtrip(self):
        """序列化往返一致"""
        record = self._make_record()
        d = record.to_dict()
        restored = MemoryRecord.from_dict(d)

        assert restored.edge_id == record.edge_id
        assert restored.concept_pair == record.concept_pair
        assert restored.relation == record.relation
        assert restored.i_value == record.i_value
        assert restored.asym == record.asym
        assert restored.psi_anchor.self_state == record.psi_anchor.self_state
        assert restored.psi_anchor.kappa_at_write == record.psi_anchor.kappa_at_write
        assert restored.access_count == record.access_count


# ============================================================
# MemoryStore 测试
# ============================================================

class TestMemoryStore:
    """MemoryStore 读写检索测试"""

    def _make_store(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        store = MemoryStore(store_path=path)
        self._temp_path = path
        return store

    def teardown_method(self, method):
        path = getattr(self, '_temp_path', None)
        if path and os.path.exists(path):
            os.unlink(path)

    def _make_record(self, edge_id, concept_pair, relation, i_value=0.8, asym=0.0):
        return MemoryRecord(
            edge_id=edge_id,
            concept_pair=concept_pair,
            relation=relation,
            i_value=i_value,
            asym=asym,
            psi_anchor=None,
            meta={},
        )

    def test_store_write(self):
        """写入记录并验证"""
        store = self._make_store()
        rec = self._make_record("e1", ("A", "B"), "A与B相关")
        result = store.write(rec)

        assert result is True
        assert "e1" in store._records
        assert store._records["e1"].relation == "A与B相关"

    def test_store_write_no_overwrite(self):
        """overwrite=False 不覆盖已存在的记录"""
        store = self._make_store()
        rec1 = self._make_record("e1", ("A", "B"), "原始关系", i_value=0.9)
        store.write(rec1)

        rec2 = self._make_record("e1", ("A", "B"), "新关系", i_value=0.5)
        result = store.write(rec2, overwrite=False)

        assert result is False
        assert store._records["e1"].relation == "原始关系"
        assert store._records["e1"].i_value == 0.9

    def test_store_retrieve(self):
        """按 i_value*access_count 排序检索"""
        store = self._make_store()
        store.write(self._make_record("e_low", ("X", "Y"), "低优先", i_value=0.1, asym=0.0))
        store.write(self._make_record("e_high", ("M", "N"), "高优先", i_value=0.9, asym=0.0))

        results = store.retrieve("test", top_k=10)
        # 高优先应排前面（i_value * (1+access_count) 更大）
        # access_count 在 retrieve 时 +1
        # e_high: 0.9 * (1+0) = 0.9 > e_low: 0.1 * (1+0) = 0.1
        assert len(results) == 2
        assert results[0].edge_id == "e_high"

    def test_store_retrieve_by_concepts(self):
        """按概念精确匹配"""
        store = self._make_store()
        store.write(self._make_record("e1", ("心", "神明"), "心主神明", i_value=0.8))
        store.write(self._make_record("e2", ("肝", "藏血"), "肝藏血", i_value=0.7))
        store.write(self._make_record("e3", ("脾", "统血"), "脾统血", i_value=0.6))

        results = store.retrieve_by_concepts(["心"])
        assert len(results) == 1
        assert results[0].edge_id == "e1"

        results2 = store.retrieve_by_concepts(["心", "肝"])
        assert len(results2) == 2

    def test_store_archieve_low_i(self):
        """归档低 I 值非 MUS 记忆"""
        store = self._make_store()
        store.write(self._make_record("e_low", ("X", "Y"), "低优先", i_value=0.05, asym=0.0))
        store.write(self._make_record("e_mus", ("A", "B"), "MUS记录", i_value=0.05, asym=0.5))
        store.write(self._make_record("e_high", ("M", "N"), "正常记录", i_value=0.8, asym=0.0))

        archived = store.archieve_low_i(theta_archieve=0.1)
        assert archived == 1
        assert "e_low" not in store._records
        assert "e_mus" in store._records  # MUS 不归档
        assert "e_high" in store._records


# ============================================================
# TOMAS_Mem_OS_Fusion 测试
# ============================================================

class TestTOMASFusion:
    """TOMAS-MemOS 融合层五点升维测试"""

    def _make_fusion(self, **kwargs):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self._temp_path = path
        return TOMAS_Mem_OS_Fusion(store_path=path, **kwargs)

    def teardown_method(self, method):
        path = getattr(self, '_temp_path', None)
        if path and os.path.exists(path):
            os.unlink(path)

    def test_dead_zero_reject(self):
        """I 值低于 theta_dead 时拒绝（用"太阳绕地球"触发）"""
        fusion = self._make_fusion(theta_dead=0.15)
        result = fusion.write_memory("太阳绕地球转", {"concepts": ["太阳", "地球"]})

        assert result["status"] == "rejected"
        assert result["reason"] == "DEAD_ZERO_REJECT"
        assert result["i_value"] < 0.15

    def test_normal_write(self):
        """正常 I 值写入成功"""
        fusion = self._make_fusion(theta_dead=0.15)
        context = {
            "concepts": ["心", "神明"],
            "eml_matches": 3,
            "self_state": "测试意向",
            "current_kappa": 4,
        }
        result = fusion.write_memory("心主神明是中医的基本理论", context)

        assert result["status"] == "written"
        assert "edge_id" in result
        assert result["i_value"] >= 0.15

    def test_mus_dual_store(self):
        """矛盾记忆 MUS 双存"""
        fusion = self._make_fusion(theta_dead=0.15, enable_mus=True)

        # 先写入第一条记忆
        context1 = {
            "concepts": ["心", "神明"],
            "self_state": "意向1",
            "current_kappa": 4,
            "asym": 0.5,
        }
        result1 = fusion.write_memory("心主神明", context1)
        assert result1["status"] == "written"

        # 写入矛盾记忆（含否定词触发 Layer1）
        context2 = {
            "concepts": ["心", "神明"],
            "self_state": "意向2",
            "current_kappa": 3,
            "asym": -0.5,
        }
        result2 = fusion.write_memory("心不主神明", context2)

        # 第二条写入应触发 MUS
        assert result2["status"] == "written"
        assert result2["mus_active"] is True

    def test_psi_anchor_attached(self):
        """psi-锚正确附加"""
        fusion = self._make_fusion(enable_psi=True)
        context = {
            "concepts": ["肝", "藏血"],
            "self_state": "持有关怀意向",
            "current_kappa": 4,
            "emotion_tone": "平静",
        }
        result = fusion.write_memory("肝藏血是中医理论", context)

        assert result["status"] == "written"
        assert result["psi_anchor"] is not None
        assert result["psi_anchor"]["self_state"] == "持有关怀意向"
        assert result["psi_anchor"]["kappa_at_write"] == 4
        assert result["psi_anchor"]["emotion_tone"] == "平静"

    def test_kappa_gate_filter(self):
        """kappa-Gate 按 kappa 值过滤"""
        fusion = self._make_fusion(enable_kappa_gate=True, enable_psi=True)

        context = {
            "concepts": ["心", "神明"],
            "self_state": "测试",
            "current_kappa": 4,
        }
        fusion.write_memory("心主神明理论", context)

        candidates = fusion.store.retrieve("心", top_k=10)

        # kappa=4 应激活 kappa_at_write=4 的记忆
        activated = fusion._kappa_gate_filter(candidates, 4)
        assert len(activated) == 1

        # kappa=1 应不激活 kappa_at_write=4 的记忆（差值>1）
        activated_far = fusion._kappa_gate_filter(candidates, 1)
        assert len(activated_far) == 0

    def test_kappa_snap_response(self):
        """kappa-Snap 生成正确回答"""
        fusion = self._make_fusion(enable_kappa_gate=True, enable_psi=True)

        context = {
            "concepts": ["心", "神明"],
            "self_state": "测试意向",
            "current_kappa": 4,
        }
        fusion.write_memory("心主神明理论", context)

        result = fusion.recall_memory("心主神明", current_kappa=4)

        assert result["status"] == "success"
        assert result["activated_count"] == 1
        assert result["response"] is not None
        assert "记忆回溯" in result["response"]

    def test_recall_no_match(self):
        """空存储召回 no_match"""
        fusion = self._make_fusion()

        result = fusion.recall_memory("不存在的内容", current_kappa=4)

        assert result["status"] == "no_match"
        assert "无匹配记忆" in result["message"]

    def test_get_stats(self):
        """统计信息正确"""
        fusion = self._make_fusion(theta_dead=0.15, enable_mus=True, enable_psi=True)

        context = {
            "concepts": ["心", "神明"],
            "self_state": "测试",
            "current_kappa": 4,
        }
        fusion.write_memory("心主神明", context)

        stats = fusion.get_stats()

        assert stats["total_memories"] == 1
        assert stats["mus_pairs"] == 0
        assert stats["avg_i_value"] > 0
        assert stats["theta_dead"] == 0.15
        assert stats["enable_mus"] is True
        assert stats["enable_psi"] is True
        assert stats["enable_kappa_gate"] is True
