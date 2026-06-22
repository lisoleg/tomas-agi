"""
测试 EMLSemZip v2.1（基于 EMLHypergraph 正确 API）
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sim'))

from eml_semzip import EMLSemZip, EMLHypergraph, EMLNode, HyperEdge, EMLLiteKB


class TestEMLSemZip:
    """测试 EMLSemZip（只测端到端 compress，不逐 stage 测）"""

    def setup_method(self):
        """设置测试固件"""
        self.engine = EMLSemZip()
        self.kb = EMLLiteKB()  # 添加知识库
        # 构建测试超图
        self.hg = EMLHypergraph()
        for vid in range(20):
            node = EMLNode(node_id=f"n{vid}")
            self.hg.add_node(node)
        # 添加超边（每个超边连接 2-3 个节点）
        for i in range(10):
            edge = HyperEdge(
                edge_id=f"e{i}",
                nodes=frozenset([f"n{i}", f"n{(i+1)%20}", f"n{(i+2)%20}"]),
            )
            self.hg.add_edge(edge)

    def test_compress(self):
        """测试端到端压缩"""
        result = self.engine.compress(self.hg, self.kb)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_compress_and_decompress(self):
        """测试压缩后解压恢复"""
        compressed = self.engine.compress(self.hg, self.kb)
        restored = self.engine.decompress(compressed, self.kb)
        assert restored is not None
        assert len(restored.V) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
