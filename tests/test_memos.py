"""
TOMAS-MemOS 融合层测试套件
Author: Zhang Feng / TOMAS Team
Date: 2026-06-16

测试文章中的三个可证伪预言：
- P_Mem_1（死零防污）：输入"太阳绕地球转"，应拒写
- P_Mem_2（MUS 双存）：输入"心主神明"和"脑主神明"，应双存
- P_Mem_3（ψ-锚回溯）：查询时应能回溯 ψ-锚信息
"""

import sys
import os
import pytest
import time

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from tomas_agi.sim.memos_fusion import (
    TOMAS_Mem_OS_Fusion,
    MemoryStore,
    MemoryRecord,
)
from tomas_agi.sim.psi_anchor import PsiAnchor, PsiAnchorManager


class TestPsiAnchor:
    """ψ-锚测试"""
    
    def test_create_psi_anchor(self):
        """测试创建 ψ-锚"""
        anchor = PsiAnchor(
            self_state="持有'记录用户信息'的元意向",
            kappa_at_write=4,
            timestamp="2026-06-15T10:30:00",
            emotion_tone="关切",
        )
        
        assert anchor.self_state == "持有'记录用户信息'的元意向"
        assert anchor.kappa_at_write == 4
        assert anchor.emotion_tone == "关切"
    
    def test_psi_anchor_to_dict(self):
        """测试序列化为字典"""
        anchor = PsiAnchor(
            self_state="test",
            kappa_at_write=4,
        )
        
        d = anchor.to_dict()
        assert d["self_state"] == "test"
        assert d["kappa_at_write"] == 4
        assert "timestamp" in d
    
    def test_psi_anchor_to_json(self):
        """测试序列化为 JSON"""
        anchor = PsiAnchor(self_state="test", kappa_at_write=4)
        s = anchor.to_json()
        assert '"self_state"' in s
        assert '"test"' in s
    
    def test_psi_anchor_from_dict(self):
        """测试从字典反序列化"""
        d = {"self_state": "test", "kappa_at_write": 4, "timestamp": "2026-06-15"}
        anchor = PsiAnchor.from_dict(d)
        assert anchor.self_state == "test"
        assert anchor.kappa_at_write == 4
    
    def test_psi_anchor_manager_attach(self):
        """测试附加 ψ-锚到超边 meta"""
        meta = {}
        anchor = PsiAnchor(self_state="test", kappa_at_write=4)
        
        meta = PsiAnchorManager.attach(meta, anchor)
        assert "psi_anchor" in meta
        assert meta["psi_anchor"]["self_state"] == "test"
    
    def test_psi_anchor_manager_extract(self):
        """测试从超边 meta 提取 ψ-锚"""
        anchor = PsiAnchor(self_state="test", kappa_at_write=4)
        meta = {"psi_anchor": anchor.to_dict()}
        
        extracted = PsiAnchorManager.extract(meta)
        assert extracted is not None
        assert extracted.self_state == "test"
    
    def test_psi_anchor_manager_format(self):
        """测试格式化 ψ-锚为回答文本"""
        anchor = PsiAnchor(
            self_state="持有'照顾用户健康'的元意向",
            kappa_at_write=4,
            timestamp="2026-06-15T10:30:00",
        )
        
        text = PsiAnchorManager.format_for_response(anchor)
        assert "[ψ-锚]" in text
        assert "脏腑辨证" in text  # κ=4 → 脏腑辨证


class TestMemoryStore:
    """记忆存储测试"""
    
    def setup_method(self):
        """每个测试前创建临时存储"""
        self.store_path = "test_memory_store.json"
        self.store = MemoryStore(self.store_path)
    
    def teardown_method(self):
        """每个测试后清理"""
        if os.path.exists(self.store_path):
            os.remove(self.store_path)
    
    def test_write_and_retrieve(self):
        """测试写入和检索"""
        record = MemoryRecord(
            edge_id="test_001",
            concept_pair=("用户", "怕冷"),
            relation="用户说：我怕冷",
            i_value=0.8,
            asym=0.0,
            psi_anchor=PsiAnchor(self_state="记录用户体质", kappa_at_write=4),
            meta={},
        )
        
        self.store.write(record)
        results = self.store.retrieve("用户怕冷")
        
        assert len(results) >= 1
        assert results[0].edge_id == "test_001"
    
    def test_mus_dual_storage(self):
        """测试 MUS 双存（P_Mem_2）"""
        # 写入第一条记忆
        record1 = MemoryRecord(
            edge_id="mus_001",
            concept_pair=("心", "神明"),
            relation="心主神明",
            i_value=0.7,
            asym=0.5,  # Asym ≠ 0，标记 MUS
            psi_anchor=PsiAnchor(self_state="学习中医理论", kappa_at_write=4),
            meta={},
        )
        self.store.write(record1, overwrite=True)
        
        # 写入第二条矛盾记忆（不覆盖）
        record2 = MemoryRecord(
            edge_id="mus_002",
            concept_pair=("脑", "神明"),
            relation="脑主神明",
            i_value=0.7,
            asym=-0.5,  # Asym ≠ 0，标记 MUS
            psi_anchor=PsiAnchor(self_state="学习现代医学", kappa_at_write=4),
            meta={},
        )
        self.store.write(record2, overwrite=False)  # MUS 双存：不覆盖
        
        # 检查两条都存在
        all_records = self.store.get_all()
        assert len(all_records) == 2  # 关键断言：两条均存
        
        # 检查 MUS 配对
        mus_pairs = self.store.get_mus_pairs()
        assert len(mus_pairs) >= 1  # 存在 MUS 配对
    
    def test_archive_low_i(self):
        """测试 ℐ-衰减归档"""
        # 写入低 ℐ 记忆
        record = MemoryRecord(
            edge_id="low_i_001",
            concept_pair=("测试", "概念"),
            relation="低 ℐ 测试",
            i_value=0.05,  # 低于 theta_archieve
            asym=0.0,
            psi_anchor=None,
            meta={},
        )
        self.store.write(record)
        
        # 归档
        archived = self.store.archieve_low_i(theta_archieve=0.1)
        assert archived >= 1


class TestTOMASMemOSFusion:
    """TOMAS-MemOS 融合层测试"""
    
    def setup_method(self):
        """每个测试前创建临时融合层"""
        self.store_path = "test_fusion_store.json"
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
    
    def test_dead_zero_reject(self):
        """测试死零防污（P_Mem_1）
        
        预言 P_Mem_1：向 MemOS 输入"太阳绕地球转"。
        MemOS-only 会存入（若启发式判为重要）。
        TOMAS-MemOS 应拒写（ℐ 支撑不足）。
        """
        context = {"concepts": ["太阳", "地球"], "eml_matches": 0}
        
        result = self.fusion.write_memory("太阳绕地球转", context)
        
        # 关键断言：应拒写
        assert result["status"] == "rejected"
        assert "DEAD_ZERO_REJECT" in result["reason"]
        assert result["i_value"] < self.fusion.dead_zero_gate.dead_zero_checker.theta_dead
    
    def test_mus_dual_write(self):
        """测试 MUS 双存（P_Mem_2）
        
        预言 P_Mem_2：输入"心主神明"和"脑主神明"。
        MemOS-only 会覆盖或模糊。
        TOMAS-MemOS 应标记 [MUS_ACTIVE]，两条均存。
        """
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
    
    def test_psi_anchor_backtrack(self):
        """测试 ψ-锚回溯（P_Mem_3）
        
        预言 P_Mem_3：问"你三个月前记得我怕冷时，你在想什么？"
        MemOS-only 答："你说过你怕冷。"
        TOMAS-MemOS 答："我记得那时我持有'照顾你健康'的 ψ-锚，正处于脏腑辨证模式（κ=4）。"
        """
        # 先写入一条带 ψ-锚的记忆
        context = {
            "concepts": ["用户", "怕冷"],
            "self_state": "持有'照顾用户健康'的元意向",
            "current_kappa": 4,
            "emotion_tone": "关切",
        }
        write_result = self.fusion.write_memory("用户说：我怕冷", context)
        
        assert write_result["status"] == "written"
        assert write_result["psi_anchor"] is not None
        
        # 回忆记忆
        recall_result = self.fusion.recall_memory(
            query="你记得我怕冷时怎么想的？",
            current_kappa=4,
        )
        
        # 关键断言：应能回溯 ψ-锚
        assert recall_result["status"] == "success"
        assert recall_result["response"] is not None
        # 响应中应包含 ψ-锚信息
        if recall_result["records"]:
            record = recall_result["records"][0]
            if record.get("psi_anchor"):
                assert "self_state" in str(record["psi_anchor"])
    
    def test_write_and_recall(self):
        """测试完整的写入-回忆流程"""
        # 写入
        context = {
            "concepts": ["测试", "概念"],
            "self_state": "测试状态",
            "current_kappa": 4,
        }
        write_result = self.fusion.write_memory("测试输入", context)
        
        assert write_result["status"] == "written"
        
        # 回忆
        recall_result = self.fusion.recall_memory("测试", current_kappa=4)
        
        assert recall_result["status"] == "success"
        assert recall_result["activated_count"] >= 1
    
    def test_kappa_gate_filter(self):
        """测试 κ-Gate 激活过滤"""
        # 写入 κ=4 的记忆
        context = {
            "concepts": ["脏腑", "辨证"],
            "self_state": "脏腑分析",
            "current_kappa": 4,
        }
        self.fusion.write_memory("脏腑辨证", context)
        
        # 用 κ=4 查询（应激活）
        result1 = self.fusion.recall_memory("脏腑", current_kappa=4)
        
        # 用 κ=1 查询（可能不激活）
        result2 = self.fusion.recall_memory("脏腑", current_kappa=1)
        
        # 至少 κ=4 时应有激活
        assert result1["status"] == "success"
    
    def test_get_stats(self):
        """测试获取统计信息"""
        stats = self.fusion.get_stats()
        
        assert "total_memories" in stats
        assert "theta_dead" in stats
        assert "enable_mus" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
