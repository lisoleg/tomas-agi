"""
NASGA 八元数运算模块 (NASGA Octonion Module)
==============================================

基于 TOMAS 内核的 NASGA（神经-符号图架构）和八元数（Octonion）超复数，
实现 EML 超图的八元数空间表示和运算。

八元数是 8 维超复数，乘法非结合、非交换，但满足交替性。
是实可除代数（实数、复数、四元数、八元数）的最后一员。

使用 Cayley-Dickson 构造递归实现，确保乘法表准确无误。

Author: Zhang Feng (TOMAS Project)
"""

import math
import random
from typing import List, Dict, Optional, Tuple


# ============================================================
#  八元数（Octonion）核心类 — 递归 Cayley-Dickson 实现
# ============================================================

class Octonion:
    """
    八元数（Octonion）— 3 级 Cayley-Dickson 构造

    数学定义（递归）：
    - 级别 0（实数）: R
    - 级别 1（复数）: C = R ⊕ R*j,  j^2 = -1
    - 级别 2（四元数）: H = C ⊕ C*l,  l^2 = -1
    - 级别 3（八元数）: O = H ⊕ H*m,  m^2 = -1

    存储：8 个实数分量 [a0, a1, ..., a7]
    对应：a0 + a1*i + a2*j + a3*k + a4*l + a5*il + a6*jl + a7*kl
    """

    def __init__(self, a0=0.0, a1=0.0, a2=0.0, a3=0.0,
                 a4=0.0, a5=0.0, a6=0.0, a7=0.0):
        self.a0, self.a1, self.a2, self.a3 = a0, a1, a2, a3
        self.a4, self.a5, self.a6, self.a7 = a4, a5, a6, a7

    @classmethod
    def zero(cls):
        return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    @classmethod
    def one(cls):
        return cls(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    @property
    def real(self):
        return self.a0

    @property
    def imag(self):
        return [self.a1, self.a2, self.a3, self.a4, self.a5, self.a6, self.a7]

    @property
    def vector(self):
        return [self.a0, self.a1, self.a2, self.a3,
                self.a4, self.a5, self.a6, self.a7]

    @property
    def norm(self):
        return math.sqrt(sum(x*x for x in self.vector))

    @property
    def norm_sq(self):
        return sum(x*x for x in self.vector)

    def conjugate(self):
        return Octonion(self.a0, -self.a1, -self.a2, -self.a3,
                        -self.a4, -self.a5, -self.a6, -self.a7)

    def inverse(self):
        n2 = self.norm_sq
        if n2 < 1e-12:
            raise ZeroDivisionError("零八元数没有逆元")
        c = self.conjugate()
        s = 1.0 / n2
        return Octonion(c.a0*s, c.a1*s, c.a2*s, c.a3*s,
                        c.a4*s, c.a5*s, c.a6*s, c.a7*s)

    def __add__(self, other):
        return Octonion(self.a0+other.a0, self.a1+other.a1, self.a2+other.a2, self.a3+other.a3,
                        self.a4+other.a4, self.a5+other.a5, self.a6+other.a6, self.a7+other.a7)

    def __sub__(self, other):
        return Octonion(self.a0-other.a0, self.a1-other.a1, self.a2-other.a2, self.a3-other.a3,
                        self.a4-other.a4, self.a5-other.a5, self.a6-other.a6, self.a7-other.a7)

    def __neg__(self):
        return Octonion(-self.a0, -self.a1, -self.a2, -self.a3,
                         -self.a4, -self.a5, -self.a6, -self.a7)

    def __mul__(self, other):
        """八元数乘法 — 支持 Octonion 和标量"""
        # 标量乘法
        if isinstance(other, (int, float)):
            return Octonion(
                self.a0*other, self.a1*other, self.a2*other, self.a3*other,
                self.a4*other, self.a5*other, self.a6*other, self.a7*other,
            )
        # 八元数乘法（Cayley-Dickson）
        a = (self.a0, self.a1, self.a2, self.a3)
        b = (self.a4, self.a5, self.a6, self.a7)
        c = (other.a0, other.a1, other.a2, other.a3)
        d = (other.a4, other.a5, other.a6, other.a7)

        def q_mul(q1, q2):
            w1,x1,y1,z1 = q1
            w2,x2,y2,z2 = q2
            return (w1*w2 - x1*x2 - y1*y2 - z1*z2,
                    w1*x2 + x1*w2 + y1*z2 - z1*y2,
                    w1*y2 - x1*z2 + y1*w2 + z1*x2,
                    w1*z2 + x1*y2 - y1*x2 + z1*w2)

        def q_conj(q):
            return (q[0], -q[1], -q[2], -q[3])

        ac  = q_mul(a, c)
        dbj = q_mul(d, q_conj(b))
        da  = q_mul(d, a)
        bcj = q_mul(b, q_conj(c))

        p1 = (ac[0]-dbj[0], ac[1]-dbj[1], ac[2]-dbj[2], ac[3]-dbj[3])
        p2 = (da[0]+bcj[0], da[1]+bcj[1], da[2]+bcj[2], da[3]+bcj[3])

        return Octonion(p1[0], p1[1], p1[2], p1[3],
                         p2[0], p2[1], p2[2], p2[3])

    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    def __truediv__(self, other):
        return self * other.inverse()

    def dot(self, other):
        return sum(a*b for a,b in zip(self.vector, other.vector))

    def is_real(self, tol=1e-9):
        return all(abs(x) < tol for x in self.imag)

    def is_imag(self, tol=1e-9):
        return abs(self.a0) < tol

    def __repr__(self):
        parts = []
        if abs(self.a0) > 1e-12:
            parts.append(f"{self.a0:.4f}")
        names = ['i','j','k','l','il','jl','kl']
        for coeff, name in zip(self.imag, names):
            if abs(coeff) > 1e-12:
                sign = "+" if coeff >= 0 and parts else ""
                parts.append(f"{sign}{coeff:.4f}*{name}")
        return "".join(parts).replace("+-", "-") if parts else "0"

    def __eq__(self, other):
        if not isinstance(other, Octonion):
            return False
        return all(abs(a-b) < 1e-9 for a,b in zip(self.vector, other.vector))

    def __hash__(self):
        return hash(tuple(round(x,6) for x in self.vector))


# ============================================================
#  NASGA 引擎（神经-符号图架构）
# ============================================================

class NASGAEngine:
    """
    NASGA 引擎 — 使用八元数作为 EML 超图的计算基底
    """

    def __init__(self, kappa=4.0, dead_zero_theta=0.15):
        self.kappa = kappa
        self.dead_zero_theta = dead_zero_theta
        self.concept_embeddings: Dict[str, Octonion] = {}
        self.edge_transforms: Dict[str, list] = {}

    def embed_concept(self, concept_name, init_vec=None):
        if concept_name in self.concept_embeddings:
            return self.concept_embeddings[concept_name]
        if init_vec is None:
            v = [random.gauss(0,1) for _ in range(8)]
            norm = math.sqrt(sum(x*x for x in v))
            v = [x/norm for x in v]
        else:
            v = init_vec
        o = Octonion(*v)
        self.concept_embeddings[concept_name] = o
        return o

    def compute_edge_potential(self, edge_id, source_concepts, target_concepts):
        for c in source_concepts + target_concepts:
            if c not in self.concept_embeddings:
                self.embed_concept(c)
        n1, n2 = len(source_concepts), len(target_concepts)
        src = sum((self.concept_embeddings[c] for c in source_concepts), Octonion.zero()) * (1.0/n1)
        tgt = sum((self.concept_embeddings[c] for c in target_concepts), Octonion.zero()) * (1.0/n2)
        try:
            pot = tgt * src.inverse()
        except ZeroDivisionError:
            pot = Octonion.zero()
        self.edge_transforms[edge_id] = [src, tgt, pot]
        return pot

    def compute_i_val(self, potential):
        return math.tanh(potential.norm)

    def check_dead_zero(self, i_val):
        return i_val < self.dead_zero_theta

    def check_mus(self, concept_pairs, potentials_dict):
        paradoxes = []
        for c1, c2 in concept_pairs:
            if c1 in potentials_dict and c2 in potentials_dict:
                p1, p2 = potentials_dict[c1], potentials_dict[c2]
                if p1.real * p2.real < 0 and p1.norm > self.dead_zero_theta and p2.norm > self.dead_zero_theta:
                    dot = sum(a*b for a,b in zip(p1.imag, p2.imag))
                    if abs(dot) > 0.1:
                        paradoxes.append(f"MUS: {c1}(Re={p1.real:.3f}) vs {c2}(Re={p2.real:.3f})")
        return len(paradoxes) > 0, paradoxes

    def embed_eml_graph(self, vertices, edges):
        for v in vertices:
            concept = v.get('concept', f"v{v.get('vid',0)}")
            i_val = v.get('i_val', 0.5)
            init_vec = self._i_val_to_embedding(i_val, v.get('vid', 0))
            self.embed_concept(concept, init_vec)
        for e in edges:
            eid = e.get('eid', 'unknown')
            nodes = e.get('nodes', [])
            if len(nodes) >= 2:
                self.compute_edge_potential(eid, [nodes[0]], [nodes[1]])

    def _i_val_to_embedding(self, i_val, seed=0):
        random.seed(seed)
        v = [random.gauss(0,1) for _ in range(8)]
        norm = math.sqrt(sum(x*x for x in v))
        scale = math.sqrt(i_val) * 2.0
        return [x/norm*scale for x in v]

    def kappa_snap(self, edges_with_potentials):
        """
        κ-Snap 决策：优先最高 I 值的边，若平局且 MUS 激活则保留延续性
        """
        scored = [(eid, self.compute_i_val(p)) for eid, p in edges_with_potentials]
        scored.sort(key=lambda x: x[1], reverse=True)
        if not scored:
            return []
        if len(scored) >= 2 and abs(scored[0][1] - scored[1][1]) < 0.01:
            top_i_val = scored[0][1]
            selected = [eid for eid, val in scored if abs(val - top_i_val) < 0.01]
            return selected
        return [scored[0][0]]

    def generate_nasga_report(self):
        return {
            'kappa': self.kappa,
            'dead_zero_theta': self.dead_zero_theta,
            'n_concepts': len(self.concept_embeddings),
            'n_edges': len(self.edge_transforms),
        }


# ============================================================
#  演示
# ============================================================

def demo_octonion():
    print("=== 八元数演示 ===\n")
    i = Octonion(0,1,0,0,0,0,0,0)
    j = Octonion(0,0,1,0,0,0,0,0)
    k = Octonion(0,0,0,1,0,0,0,0)
    l = Octonion(0,0,0,0,1,0,0,0)

    print(f"i*j = {(i*j)} | expect: k")
    print(f"j*i = {(j*i)} | expect: -k")
    print(f"非交换性: {abs(((i*j)+(j*i)).norm) < 1e-6}")

    # 非结合性: (i*j)*l vs i*(j*l)
    left  = (i * j) * l
    right = i * (j * l)
    print(f"(i*j)*l = {left}")
    print(f"i*(j*l) = {right}")
    print(f"非结合性: {abs((left - right).norm) > 1e-6}")

    a = Octonion(1,2,3,4,5,6,7,8)
    print(f"\n|a| = {a.norm:.4f}")
    print(f"a * a^-1 = {a * a.inverse()} | expect: 1")
    print(f"l*l = {l*l} | expect: -1")


def demo_nasga():
    print("\n=== NASGA 引擎演示 ===\n")
    engine = NASGAEngine(kappa=4.0, dead_zero_theta=0.15)
    for c in ["心", "肾", "火", "水"]:
        engine.embed_concept(c)
    p = engine.compute_edge_potential("e1", ["心"], ["肾"])
    i_val = engine.compute_i_val(p)
    print(f"心→肾 势能范数: {p.norm:.4f}, I={i_val:.4f}")
    print(f"死零校验拒答: {engine.check_dead_zero(i_val)}")


if __name__ == '__main__':
    demo_octonion()
    demo_nasga()
