"""
EML 数学降维工具箱 (EML Slimming Toolkit)
===========================================

基于章锋《数学降维与 EML 超图可解性：GPCT 边界层降解 · 虚时计算(ITC) · 拟阵(Matroid) · Brown‑Miklós FPT》
(2026-06-15, 复合体理学)

四合一架构：
  ITC（识别边界层+退火初值）→ GPCT（分层STR-F）→ 拟阵（剪枝保基）→ 输出

统一主定理：若 EML 超图 H 源自太一投影且服从公理 A1（ℐ守恒），
则存在度类划分使 k = 活跃 κ-bin 数 ≤ 参数，
此时 H 通过 Brown‑Miklós + GPCT + 拟阵属于 FPT；ITC 提供物理搜索引擎。

核心模块：
  - hyperedge: HypEdge 超边数据模型
  - matroid: 拟阵贪心剪枝 (κ-Gate 最优独立集)
  - gpct: GPCT 边界层分解 (STR-F 分层 SAT 降解)
  - itc: ITC 虚时退火 (Wick 旋转基态搜索)
  - brown_miklos: Brown‑Miklós FPT 度类压缩
  - strf: STR-F 四大等价变换
  - pipeline: slim_eml 完整瘦身流水线
"""

from .hyperedge import HypEdge, EMLVertex, load_eml_graph
from .matroid import Matroid, matroid_prune
from .gpct import GpctDecomposer, gpct_decompose
from .itc import ItcAnneal, itc_anneal
from .brown_miklos import BrownMiklosCompressor, brown_miklos_compress
from .strf import StrfTransformer
from .pipeline import slim_eml, DimredResult

__all__ = [
    "HypEdge",
    "EMLVertex",
    "load_eml_graph",
    "Matroid",
    "matroid_prune",
    "GpctDecomposer",
    "gpct_decompose",
    "ItcAnneal",
    "itc_anneal",
    "BrownMiklosCompressor",
    "brown_miklos_compress",
    "StrfTransformer",
    "slim_eml",
    "DimredResult",
]

__version__ = "1.0.0"
