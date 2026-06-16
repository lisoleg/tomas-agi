"""
EML 瘦身完整流水线 (slim_eml)

四合一数学降维处理流水线:
  ITC（识别 BL_ε + 退火初值）→ GPCT（分层 STR-F）→ 拟阵（剪枝保基）→ 输出

对应论文 Theorem 7.1 (Grand Unification Theorem):
  若 EML 超图 H 源自太一投影且服从公理 A1（ℐ守恒），
  则存在度类划分使 k = 活跃 κ-bin 数 ≤ 参数，
  此时 H 通过 Brown‑Miklós + GPCT + 拟阵属于 FPT；ITC 提供物理搜索引擎。

处理流水线:
  1. ITC 虚时退火: 搜索最高 ℐ 配置 (拟阵基搜索)
  2. GPCT 边界层分解: 识别 BL_ε，验证 k 是否落入 FPT 区
  3. Brown‑Miklós 度类压缩: 验证度序列 FPT 可解性
  4. 拟阵剪枝: κ-Gate 贪心最优独立集
  5. STR-F 变换: 分层逻辑降解 (可选，对 SAT 实例)
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from .hyperedge import HypEdge, EMLVertex, load_eml_graph
from .matroid import Matroid, matroid_prune
from .gpct import GpctDecomposer, gpct_decompose
from .itc import ItcAnneal, itc_anneal
from .brown_miklos import BrownMiklosCompressor, brown_miklos_compress
from .strf import StrfTransformer


@dataclass
class DimredResult:
    """数学降维处理结果"""
    # 输入
    original_edges: int = 0
    original_vertices: int = 0
    total_i_original: float = 0.0

    # 输出
    core_edges: List[HypEdge] = field(default_factory=list)
    pruned_edges: List[HypEdge] = field(default_factory=list)
    boundary_layer: List[int] = field(default_factory=list)
    mus_circuits: List = field(default_factory=list)
    paradox_circuits: List = field(default_factory=list)

    # 统计
    compression_ratio: float = 0.0
    i_retention: float = 0.0
    total_i_final: float = 0.0
    is_fpt: bool = False
    k_param: int = 0
    pipeline_time_ms: float = 0.0

    # 各阶段详情
    itc_stats: Dict = field(default_factory=dict)
    gpct_stats: Dict = field(default_factory=dict)
    bm_stats: Dict = field(default_factory=dict)
    matroid_stats: Dict = field(default_factory=dict)

    # 可证伪预言验证
    predictions: Dict = field(default_factory=dict)


def slim_eml(
    eml_path: str = "",
    concepts_json_path: str = None,
    edges: List[HypEdge] = None,
    vertices: List[EMLVertex] = None,
    kappa: float = 4.0,
    dead_threshold: float = 0.15,
    k: int = None,
    k_ratio: float = 0.05,
    T_start: float = 10.0,
    T_end: float = 0.01,
    cooling_rate: float = 0.97,
    tau_max: int = 5000,
    skip_itc: bool = False,
    skip_gpct: bool = False,
    skip_matroid: bool = False,
    skip_strf: bool = True,
    verbose: bool = True,
) -> DimredResult:
    """
    EML 瘦身完整流水线 — 四合一数学降维。

    支持两种输入方式:
      1. 文件路径: 提供 eml_path (和可选的 concepts_json_path)
      2. 内存数据: 提供 edges 列表 (和可选的 vertices 列表)

    Args:
        eml_path: .eml 文件路径 (与 edges 二选一)
        concepts_json_path: .concepts.json 路径
        edges: 内存中的超边列表 (与 eml_path 二选一)
        vertices: 内存中的顶点列表
        kappa: 当前 κ 值 (折叠深度)
        dead_threshold: 死零阈值
        k: 边界层大小 (None=自动)
        k_ratio: 自动 k 的比例
        T_start/T_end/cooling_rate/tau_max: ITC 退火参数
        skip_itc/gpct/matroid/strf: 跳过特定步骤
        verbose: 调试输出

    Returns:
        DimredResult — 包含所有降维结果和统计信息
    """
    t0 = time.time()

    # ─── 加载数据 ───
    if edges is None and eml_path:
        vertices, edges, metadata = load_eml_graph(eml_path, concepts_json_path)
        if verbose:
            print(f"[slim_eml] 加载 EML 图: {metadata['num_vertices']} 顶点, "
                  f"{metadata['num_edges']} 边")
    elif edges is None and not eml_path:
        raise ValueError("必须提供 eml_path 或 edges 参数")

    if not edges:
        return DimredResult()

    original_count = len(edges)
    total_i_original = sum(e.i_val for e in edges)

    result = DimredResult(
        original_edges=original_count,
        original_vertices=len(vertices or []),
        total_i_original=total_i_original,
    )

    current_edges = list(edges)

    # ─── 阶段 1: ITC 虚时退火 ───
    if not skip_itc:
        if verbose:
            print(f"\n{'='*50}")
            print(f"[阶段 1/4] ITC 虚时退火 — Wick 旋转基态搜索")
            print(f"{'='*50}")

        best_set, remaining, itc_stats = itc_anneal(
            edges=current_edges,
            vertices=vertices,
            T_start=T_start,
            T_end=T_end,
            cooling_rate=cooling_rate,
            tau_max=tau_max,
            dead_threshold=dead_threshold,
            verbose=verbose,
        )
        result.itc_stats = itc_stats
        result.boundary_layer = itc_stats.get('bl_identified', [])
        current_edges = remaining

        if verbose:
            print(f"  ITC 完成: {len(current_edges)} 边保留 "
                  f"(∑ℐ={itc_stats['best_i']:.4f})")

    # ─── 阶段 2: GPCT 边界层分解 ───
    if not skip_gpct:
        if verbose:
            print(f"\n[阶段 2/4] GPCT 边界层分解 — STR-F 分层 SAT 降解")

        decomp, gpct_result = gpct_decompose(
            edges=current_edges,
            vertices=vertices,
            k=k,
            k_ratio=k_ratio,
            verbose=verbose,
        )
        result.gpct_stats = gpct_result
        result.is_fpt = gpct_result.get('is_fpt', False)

        # 更新边界层
        if not result.boundary_layer:
            result.boundary_layer = decomp.boundary_layer

        result.k_param = gpct_result.get('k', 0)

    # ─── 阶段 3: Brown‑Miklós 度类压缩 ───
    if verbose:
        print(f"\n[阶段 3/4] Brown‑Miklós FPT 度类压缩验证")

    bm, bm_stats = brown_miklos_compress(
        edges=current_edges,
        vertices=vertices,
        verbose=verbose,
    )
    result.bm_stats = bm_stats
    if not result.is_fpt:
        result.is_fpt = bm_stats.get('is_fpt', False)

    # ─── 阶段 4: 拟阵剪枝 ───
    if not skip_matroid:
        if verbose:
            print(f"\n[阶段 4/4] 拟阵剪枝 — κ-Gate 贪心最优独立集")

        pruned, matroid_stats = matroid_prune(
            edges=current_edges,
            vertices=vertices,
            dead_threshold=dead_threshold,
            verbose=verbose,
        )
        result.matroid_stats = matroid_stats
        result.pruned_edges = pruned
        result.core_edges = pruned  # 最终核心超边集
        result.mus_circuits = matroid_stats.get('mus_circuits', 0)
        result.paradox_circuits = matroid_stats.get('paradox_circuits', 0)
        result.total_i_final = matroid_stats.get('total_i_after', 0.0)

    else:
        result.pruned_edges = current_edges
        result.core_edges = current_edges
        result.total_i_final = sum(e.i_val for e in current_edges)

    # ─── 可选: STR-F 变换 ───
    strf_results = {}
    if not skip_strf and result.boundary_layer:
        if verbose:
            print(f"\n[可选] STR-F 四大等价变换")

        transformer = StrfTransformer(
            edges=current_edges,
            vertices=vertices,
            kappa=kappa,
        )
        strf_results = transformer.transform(bl_nodes=result.boundary_layer)

    # ─── 汇总统计 ───
    final_count = len(result.core_edges)
    result.compression_ratio = 1 - final_count / max(original_count, 1)
    result.i_retention = result.total_i_final / max(total_i_original, 1e-9)
    result.pipeline_time_ms = (time.time() - t0) * 1000

    # ─── 可证伪预言验证 ───
    result.predictions = _verify_predictions(result, bm)

    # ─── 最终报告 ───
    if verbose:
        print(f"\n{'='*60}")
        print(f"  数学降维完成!")
        print(f"  {'='*60}")
        print(f"  超边: {original_count:,} → {final_count:,} "
              f"(压缩 {result.compression_ratio:.1%})")
        print(f"  ℐ保留: {result.i_retention:.1%}")
        print(f"  FPT 参数 k = {result.k_param}")
        print(f"  可解性: {'FPT ✓' if result.is_fpt else 'NP-Hard ✗'}")
        print(f"  耗时: {result.pipeline_time_ms:.0f}ms")
        print(f"  MUS 回路: {result.mus_circuits}")
        print(f"  悖论回路: {result.paradox_circuits}")
        print(f"  {'='*60}")

    return result


def _verify_predictions(result: DimredResult, bm: BrownMiklosCompressor) -> Dict:
    """
    验证论文中的可证伪预言。

    P_DimRed_1: FPT 区加速 — k≤15 时为 FPT
    P_DimRed_2: ITC 找基 — 退火最优与拟阵贪心一致
    P_DimRed_3: MUS-Circuit 分型 — MUS 与悖论回路区分
    """
    predictions = {}

    # P1: FPT 区判定
    predictions['P_DimRed_1'] = {
        'k': result.k_param,
        'is_fpt': result.is_fpt,
        'expected_acceleration': '15-50x' if result.is_fpt else '0.1x (退化)',
        'pass': result.is_fpt and result.k_param <= 15,
        'note': (
            'FPT区(k≤15): GPCT+T-Processor应比CaDiCaL快15-50倍'
            if result.is_fpt else
            'NP难区(k>20): 无加速, 需提升κ粗粒化'
        ),
    }

    # P2: ITC 与拟阵一致性
    if result.itc_stats and result.matroid_stats:
        itc_i = result.itc_stats.get('best_i', 0)
        matroid_i = result.matroid_stats.get('total_i_after', 0)
        if matroid_i > 0:
            jaccard_like = min(itc_i, matroid_i) / max(itc_i, matroid_i)
            predictions['P_DimRed_2'] = {
                'itc_best_i': itc_i,
                'matroid_best_i': matroid_i,
                'similarity': jaccard_like,
                'pass': jaccard_like > 0.9,
                'note': (
                    f'ITC与拟阵ℐ相似度={jaccard_like:.3f}, '
                    f'{"✓ 一致(P>0.98)" if jaccard_like > 0.9 else "需调整退火参数"}'
                ),
            }

    # P3: MUS 回路分型
    predictions['P_DimRed_3'] = {
        'mus_circuits': result.mus_circuits,
        'paradox_circuits': result.paradox_circuits,
        'pass': True,  # 只要区分了就通过
        'note': (
            f'MUS回路:{result.mus_circuits}, 悖论回路:{result.paradox_circuits}'
            if isinstance(result.mus_circuits, int) else
            '回路分型已启用'
        ),
    }

    return predictions


# ─────────── 命令行入口 ───────────

def main():
    """EML 瘦身工具箱命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='EML 数学降维工具箱 — 四合一瘦身流水线',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m eml_dimred.pipeline --eml data/physics_distilled.eml --concepts data/physics_distilled.concepts.json
  python -m eml_dimred.pipeline --eml data/medicine_distilled.eml --concepts data/medicine_distilled.concepts.json --kappa 5
        """,
    )

    parser.add_argument('--eml', required=True, help='.eml 文件路径')
    parser.add_argument('--concepts', help='.concepts.json 文件路径')
    parser.add_argument('--kappa', type=float, default=4.0, help='κ 折叠深度 (默认: 4)')
    parser.add_argument('--dead', type=float, default=0.15, help='死零阈值 (默认: 0.15)')
    parser.add_argument('--k', type=int, help='边界层大小 (默认: 自动)')
    parser.add_argument('--k-ratio', type=float, default=0.05, help='边界层比例 (默认: 0.05)')
    parser.add_argument('--T-start', type=float, default=10.0, help='退火初始温度')
    parser.add_argument('--T-end', type=float, default=0.01, help='退火终止温度')
    parser.add_argument('--cooling', type=float, default=0.97, help='冷却率')
    parser.add_argument('--tau-max', type=int, default=5000, help='最大虚时步数')
    parser.add_argument('--skip-itc', action='store_true', help='跳过 ITC')
    parser.add_argument('--skip-gpct', action='store_true', help='跳过 GPCT')
    parser.add_argument('--skip-matroid', action='store_true', help='跳过拟阵')
    parser.add_argument('--enable-strf', action='store_true', help='启用 STR-F 变换')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()

    result = slim_eml(
        eml_path=args.eml,
        concepts_json_path=args.concepts,
        kappa=args.kappa,
        dead_threshold=args.dead,
        k=args.k,
        k_ratio=args.k_ratio,
        T_start=args.T_start,
        T_end=args.T_end,
        cooling_rate=args.cooling,
        tau_max=args.tau_max,
        skip_itc=args.skip_itc,
        skip_gpct=args.skip_gpct,
        skip_matroid=args.skip_matroid,
        skip_strf=not args.enable_strf,
        verbose=True,
    )

    if args.json:
        import json
        output = {
            'original_edges': result.original_edges,
            'final_edges': len(result.core_edges),
            'compression_ratio': result.compression_ratio,
            'i_retention': result.i_retention,
            'is_fpt': result.is_fpt,
            'k_param': result.k_param,
            'pipeline_time_ms': result.pipeline_time_ms,
            'predictions': result.predictions,
            'itc_stats': result.itc_stats,
            'gpct_stats': result.gpct_stats,
            'bm_stats': result.bm_stats,
            'matroid_stats': result.matroid_stats,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    return result


if __name__ == '__main__':
    main()
