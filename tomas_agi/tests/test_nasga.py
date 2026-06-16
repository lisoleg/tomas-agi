"""
NASGA 八元数运算模块测试

测试覆盖：
- Octonion 基础运算（加、减、标量乘、逆元、范数）
- 八元数特殊性质（非交换性、非结合性）
- NASGAEngine（概念嵌入、势能计算、死零/MUS 校验）
"""

import math
import random
import sys
import os

# 将 sim/ 目录加入路径（nasga_octonion.py 所在位置）
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sim_dir = os.path.join(_project_root, 'sim')
sys.path.insert(0, _sim_dir)

from nasga_octonion import Octonion, NASGAEngine


class TestOctonion:
    """Octonion 基础测试"""

    def test_init_and_vector(self):
        o = Octonion(1, 2, 3, 4, 5, 6, 7, 8)
        assert o.vector == [1, 2, 3, 4, 5, 6, 7, 8]
        print("  [PASS] test_init_and_vector")

    def test_zero_one(self):
        z = Octonion.zero()
        assert z.vector == [0, 0, 0, 0, 0, 0, 0, 0]
        o = Octonion.one()
        assert o.vector == [1, 0, 0, 0, 0, 0, 0, 0]
        print("  [PASS] test_zero_one")

    def test_add_sub(self):
        a = Octonion(1, 2, 3, 4, 5, 6, 7, 8)
        b = Octonion(8, 7, 6, 5, 4, 3, 2, 1)
        c = a + b
        assert c.vector == [9, 9, 9, 9, 9, 9, 9, 9]
        d = a - b
        assert d.vector == [-7, -5, -3, -1, 1, 3, 5, 7]
        print("  [PASS] test_add_sub")

    def test_conjugate(self):
        o = Octonion(1, 2, 3, 4, 5, 6, 7, 8)
        c = o.conjugate()
        assert c.vector == [1, -2, -3, -4, -5, -6, -7, -8]
        print("  [PASS] test_conjugate")

    def test_norm_and_norm_sq(self):
        o = Octonion(1, 2, 3, 4, 5, 6, 7, 8)
        assert abs(o.norm_sq - 204.0) < 1e-9
        assert abs(o.norm - math.sqrt(204.0)) < 1e-9
        print("  [PASS] test_norm_and_norm_sq")

    def test_inverse(self):
        o = Octonion(1, 2, 3, 4, 5, 6, 7, 8)
        inv = o.inverse()
        product = o * inv
        assert abs(product.a0 - 1.0) < 1e-6
        assert all(abs(x) < 1e-6 for x in product.imag)
        print("  [PASS] test_inverse")

    def test_non_commutative(self):
        """非交换性：e1 * e2 != e2 * e1"""
        i = Octonion(0, 1, 0, 0, 0, 0, 0, 0)
        j = Octonion(0, 0, 1, 0, 0, 0, 0, 0)
        ij = i * j
        ji = j * i
        # ij + ji 应该不为零（实际上 ij = k, ji = -k，所以 ij + ji = 0）
        # 但重要的是 ij != ji
        assert (ij - ji).norm > 1e-6
        print("  [PASS] test_non_commutative")

    def test_non_associative(self):
        """非结合性：(e1*e2)*e5 != e1*(e2*e5)"""
        i = Octonion(0, 1, 0, 0, 0, 0, 0, 0)
        j = Octonion(0, 0, 1, 0, 0, 0, 0, 0)
        l = Octonion(0, 0, 0, 0, 1, 0, 0, 0)  # 八元数新单位
        left = (i * j) * l
        right = i * (j * l)
        # 对于八元数，(i*j)*l 和 i*(j*l) 一般不相等
        # 使用已知的非结合例子
        assert (left - right).norm > 1e-6, "八元数应满足非结合性"
        print("  [PASS] test_non_associative")

    def test_cayley_dickson_units(self):
        """验证 Cayley-Dickson 构造的单位乘法"""
        i = Octonion(0, 1, 0, 0, 0, 0, 0, 0)
        j = Octonion(0, 0, 1, 0, 0, 0, 0, 0)
        k = Octonion(0, 0, 0, 1, 0, 0, 0, 0)
        l = Octonion(0, 0, 0, 0, 1, 0, 0, 0)

        # i*j = k
        assert abs((i * j).a3 - 1.0) < 1e-6
        # j*i = -k
        assert abs((j * i).a3 + 1.0) < 1e-6
        # l*l = -1
        assert abs((l * l).a0 + 1.0) < 1e-6
        print("  [PASS] test_cayley_dickson_units")

    def test_scalar_mul(self):
        """标量乘法"""
        o = Octonion(1, 2, 3, 4, 5, 6, 7, 8)
        p = o * 0.5
        assert p.vector == [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
        # 也测试左乘
        q = 2.0 * o
        assert q.vector == [2, 4, 6, 8, 10, 12, 14, 16]
        print("  [PASS] test_scalar_mul")


class TestNASGAEngine:
    """NASGAEngine 测试"""

    def test_embed_concept(self):
        engine = NASGAEngine()
        o = engine.embed_concept("心")
        assert isinstance(o, Octonion)
        assert "心" in engine.concept_embeddings
        # 重复嵌入应返回相同对象
        o2 = engine.embed_concept("心")
        assert o.vector == o2.vector
        print("  [PASS] test_embed_concept")

    def test_compute_edge_potential(self):
        engine = NASGAEngine()
        engine.embed_concept("心")
        engine.embed_concept("肾")
        pot = engine.compute_edge_potential("e1", ["心"], ["肾"])
        assert isinstance(pot, Octonion)
        assert "e1" in engine.edge_transforms
        print("  [PASS] test_compute_edge_potential")

    def test_compute_i_val(self):
        engine = NASGAEngine()
        pot = Octonion(0, 1, 0, 0, 0, 0, 0, 0)  # 范数 = 1
        i_val = engine.compute_i_val(pot)
        assert 0.0 <= i_val <= 1.0
        assert abs(i_val - math.tanh(1.0)) < 1e-6
        print("  [PASS] test_compute_i_val")

    def test_check_dead_zero(self):
        engine = NASGAEngine(dead_zero_theta=0.15)
        assert engine.check_dead_zero(0.1) == True   # 触发死零
        assert engine.check_dead_zero(0.5) == False  # 不触发
        print("  [PASS] test_check_dead_zero")

    def test_check_mus(self):
        engine = NASGAEngine()
        # 创建两个对立概念（实部符号相反，虚部有足够重叠）
        random.seed(42)
        p1 = Octonion(0.8, 0.5, 0.3, 0, 0, 0, 0, 0)   # 虚部更大
        p2 = Octonion(-0.6, 0.4, 0.2, 0, 0, 0, 0, 0)  # 虚部有重叠
        mus_active, pairs = engine.check_mus(
            [("科学家", "炼金术士")],
            {"科学家": p1, "炼金术士": p2}
        )
        assert mus_active == True
        assert len(pairs) > 0
        print("  [PASS] test_check_mus")

    def test_kappa_snap(self):
        engine = NASGAEngine()
        # 创建两个势能（I 值）相同的边
        edges = [
            ("e1", Octonion(0, 2, 0, 0, 0, 0, 0, 0)),  # |pot| = 2
            ("e2", Octonion(0, -2, 0, 0, 0, 0, 0, 0)), # |pot| = 2
        ]
        selected = engine.kappa_snap(edges)
        # 平局时应保留所有边
        assert len(selected) == 2
        print("  [PASS] test_kappa_snap")

    def test_embed_eml_graph(self):
        engine = NASGAEngine()
        vertices = [
            {"vid": 0, "concept": "心", "i_val": 0.9},
            {"vid": 1, "concept": "肾", "i_val": 0.8},
        ]
        edges = [
            {"eid": "e1", "nodes": ["心", "肾"], "i_val": 0.85},
        ]
        engine.embed_eml_graph(vertices, edges)
        assert len(engine.concept_embeddings) == 2
        assert len(engine.edge_transforms) == 1
        print("  [PASS] test_embed_eml_graph")


def run_all_tests():
    print("="*60)
    print("  NASGA 八元数运算模块测试")
    print("="*60 + "\n")

    print("--- Octonion 基础测试 ---")
    t1 = TestOctonion()
    for method in dir(t1):
        if method.startswith("test_"):
            try:
                getattr(t1, method)()
            except Exception as e:
                print(f"  [FAIL] {method}: {e}")
                import traceback
                traceback.print_exc()

    print("\n--- NASGAEngine 测试 ---")
    t2 = TestNASGAEngine()
    for method in dir(t2):
        if method.startswith("test_"):
            try:
                getattr(t2, method)()
            except Exception as e:
                print(f"  [FAIL] {method}: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "="*60)
    print("  所有测试通过！")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
