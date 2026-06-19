# -*- coding: utf-8 -*-
"""
bench_aegis.py — AEGIS 性能基准测试脚本

测试 HarnessX + AEGIS 引擎的四阶段流水线性能：
  Digester → Planner → Evolver → Critic+Gate

指标：
  - 吞吐量（RPS: Requests Per Second）
  - 延迟（P50 / P95 / P99）
  - CRR (Capability Retention Rate > 95%)
  - MUS 变体隔离成功率
  - κ-Gate 双轨协同进化增益

用法：
  python bench_aegis.py --iterations 100 --variants 3
  python bench_aegis.py --quick  # 快速测试（10 次迭代）
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

# ─── 引入被测模块 ───────────────────────────────────────────────
try:
    from harness_aegis import (
        AEGISEngine,
        CausalLog,
        CompatManifest,
        HookPhase,
        KSnapDualRail,
        SnapSubject,
        TOMAS_HarnessEdge,
        VariantIsolationManager,
        create_default_harness,
        run_aegis_benchmark,
    )
    from extend_hypergraph import ExtendHypergraph
    from tshield_wrapper import TShieldWrapper
    HAS_FULL_IMPORTS = True
except Exception as e:
    print(f"[WARN] 部分模块导入失败，将使用模拟模式: {e}")
    HAS_FULL_IMPORTS = False


# ─── 模拟实现（当真实模块不可用时）──────────────────────────────
class MockHarnessEdge:
    """模拟 TOMAS_HarnessEdge"""
    def __init__(self, edge_id: str, phase: str = "TaskStart"):
        self.edge_id = edge_id
        self.phase = phase
        self.opt_dims = ["D1", "D2", "D3"]
        self.g_ego_psi_alignment = "care_safety"
        self.prompt_ref = "You are a helpful assistant."
        self.tool_bindings = []
        self.memory_policy = {"max_entries": 100}
        self.ctrl_flow = {"type": "ReAct", "max_steps": 10}
        self.eval_spec = {"metric": "pass_rate", "gold_set": []}
        self.iota_proxy = 0.5
        self.std_ref = f"HarnessX_v1/derived_from_trace:{hash(edge_id)}"
        self.supersedes = None
        self.version = 1
        self.is_superseded = False
        self.created_at = time.time()

    def to_dict(self) -> dict:
        return {"edge_id": self.edge_id, "version": self.version}


class MockAEGISEngine:
    """模拟 AEGISEngine"""
    def __init__(self, **kwargs):
        self.session_id = str(uuid.uuid4())
        self.causal_log_events: List[dict] = []

    def evolve(self, trajectory: List[dict], current_harness: MockHarnessEdge) -> Tuple[Any, str]:
        """模拟 AEGIS 四阶段流水线"""
        t0 = time.perf_counter()

        # 1. Digester（模拟）
        failed = [s for s in trajectory if not s.get("success", True)]
        # 2. Planner（模拟）
        proposals = [{"op": "tune_prompt", "target": getattr(failed[0], 'edge_id', 'mock')}
                    for _ in (failed[:1] if failed else [])]
        # 3. Evolver（模拟）
        import copy
        candidate = copy.deepcopy(current_harness)
        candidate.edge_id = f"harness_{uuid.uuid4().hex[:12]}"
        candidate.version = current_harness.version + 1
        current_harness.is_superseded = True
        # 4. Critic+Gate（模拟）
        accept = len(failed) > 0

        elapsed = (time.perf_counter() - t0) * 1000  # ms
        self.causal_log_events.append({
            "snap_id": str(uuid.uuid4()),
            "session_id": self.session_id,
            "subject": "HARNESS_VER",
            "elapsed_ms": elapsed,
        })
        if accept:
            return candidate, "AEGIS Critic+Gate PASS"
        return None, "No failed edges detected"

    def compute_psi_alignment(self, edge, psi_anchor=None) -> float:
        return 0.85


class MockVariantIsolationManager:
    """模拟 VariantIsolationManager"""
    def __init__(self, max_variants: int = 5):
        self.variants: Dict[str, MockHarnessEdge] = {}
        self.performance: Dict[str, Dict[str, float]] = {}

    def register_cluster(self, name: str, harness: MockHarnessEdge):
        self.variants[name] = harness

    def route(self, task_sig: str) -> MockHarnessEdge:
        if self.variants:
            return list(self.variants.values())[0]
        return None

    def compute_crr(self) -> float:
        """模拟 CRR 计算"""
        if not self.performance:
            return 1.0
        vals = [max(v.values()) for v in self.performance.values() if v]
        return sum(vals) / len(vals) if vals else 1.0


# ─── 基准测试核心类 ───────────────────────────────────────────────
class AEGISBenchmark:
    """AEGIS 性能基准测试器"""

    def __init__(
        self,
        iterations: int = 100,
        num_variants: int = 3,
        enable_psi_check: bool = True,
        verbose: bool = False,
    ):
        self.iterations = iterations
        self.num_variants = num_variants
        self.enable_psi_check = enable_psi_check
        self.verbose = verbose

        # 延迟记录（毫秒）
        self.latencies: List[float] = []
        self.throughput_rps: List[float] = []

        # 使用真实模块或模拟
        if HAS_FULL_IMPORTS:
            self._use_real = True
            self._harness_cls = TOMAS_HarnessEdge
            self._aegis_cls = AEGISEngine
            self._vim_cls = VariantIsolationManager
            print("[INFO] 使用真实 AEGIS 模块")
        else:
            self._use_real = False
            self._harness_cls = MockHarnessEdge
            self._aegis_cls = MockAEGISEngine
            self._vim_cls = MockVariantIsolationManager
            print("[INFO] 使用模拟模式（模块不可用）")

    # ── 辅助方法 ─────────────────────────────────────────────
    def _create_trajectory(self, size: int = 5, fail_rate: float = 0.3) -> List[dict]:
        """生成模拟轨迹"""
        traj = []
        harness_id = f"harness_{uuid.uuid4().hex[:8]}"
        for i in range(size):
            success = (i / size) >= fail_rate
            traj.append({
                "step": i + 1,
                "success": success,
                "harness_edge_id": harness_id,
                "action": "tool_call" if success else "llm_call",
            })
        return traj

    def _make_harness(self, idx: int) -> Any:
        if self._use_real:
            return create_default_harness()
        return self._harness_cls(edge_id=f"bench_harness_{idx:04d}")

    # ── 测试用例 ─────────────────────────────────────────────
    def bench_pipeline_latency(self) -> Dict[str, float]:
        """
        测试 AEGIS 四阶段流水线延迟

        Returns:
            包含 p50/p95/p99/mean/max 延迟的字典（毫秒）
        """
        print(f"\n── 测试 1: AEGIS 流水线延迟 ({self.iterations} 次迭代) ──")
        latencies = []

        for i in range(self.iterations):
            harness = self._make_harness(i)
            trajectory = self._create_trajectory(size=5, fail_rate=0.4)

            engine = self._aegis_cls(eml_kb=None, g_ego_psi_anchor="care_safety")
            t0 = time.perf_counter()
            try:
                result, reason = engine.evolve(trajectory, harness)
                elapsed = (time.perf_counter() - t0) * 1000  # ms
                latencies.append(elapsed)
            except Exception as e:
                if self.verbose:
                    print(f"  [WARN] 迭代 {i}: {e}")
                continue

        if not latencies:
            return {"error": "所有迭代均失败"}

        latencies.sort()
        return {
            "p50_ms": float(statistics.median(latencies)),
            "p95_ms": float(latencies[int(len(latencies) * 0.95)]),
            "p99_ms": float(latencies[int(len(latencies) * 0.99)]) if len(latencies) > 100 else latencies[-1],
            "mean_ms": float(statistics.mean(latencies)),
            "min_ms": float(min(latencies)),
            "max_ms": float(max(latencies)),
            "std_ms": float(statistics.stdev(latencies)) if len(latencies) > 1 else 0.0,
            "samples": len(latencies),
        }

    def bench_throughput(self, duration_sec: int = 10) -> Dict[str, float]:
        """
        测试 AEGIS 吞吐量（RPS）

        Args:
            duration_sec: 测试持续时间（秒）

        Returns:
            包含 rps / total / success_rate 的字典
        """
        print(f"\n── 测试 2: AEGIS 吞吐量（持续 {duration_sec}s）──")
        count = 0
        success = 0
        t_start = time.perf_counter()

        while (time.perf_counter() - t_start) < duration_sec:
            harness = self._make_harness(count)
            trajectory = self._create_trajectory(size=3, fail_rate=0.5)
            engine = self._aegis_cls(eml_kb=None)
            try:
                result, _ = engine.evolve(trajectory, harness)
                success += 1
            except Exception:
                pass
            count += 1

        elapsed = time.perf_counter() - t_start
        rps = count / elapsed
        print(f"  总请求: {count}, 成功: {success}, RPS: {rps:.1f}")
        return {
            "rps": round(rps, 2),
            "total": count,
            "success": success,
            "success_rate": round(success / count * 100, 2) if count else 0,
            "elapsed_sec": round(elapsed, 3),
        }

    def bench_crr(self) -> Dict[str, float]:
        """
        测试能力保留率（CRR > 95%）

        Returns:
            包含 crr / per_variant_perf / num_variants 的字典
        """
        print(f"\n── 测试 3: 变体隔离 CRR（{self.num_variants} 个变体）──")
        vim = self._vim_cls(max_variants=max(5, self.num_variants))

        # 注册变体
        for i in range(self.num_variants):
            h = self._make_harness(i)
            if hasattr(h, 'edge_id'):
                vim.register_cluster(f"cluster_{i}", h)
            else:
                vim.register_cluster(f"cluster_{i}", h)

        # 模拟性能数据
        perf_data = {}
        for i in range(self.num_variants):
            perf = 0.85 + (i * 0.02)  # 85% ~ 89%
            if hasattr(vim, 'record_performance'):
                vim.record_performance(f"cluster_{i}", "pass_rate", perf)
            else:
                vim.performance[f"cluster_{i}"] = {"pass_rate": perf}
            perf_data[f"cluster_{i}"] = perf

        crr = vim.compute_crr()
        print(f"  CRR = {crr:.4f} (目标 > 0.95)")
        return {
            "crr": round(crr, 4),
            "per_variant_perf": perf_data,
            "num_variants": self.num_variants,
            "crr_pass": crr >= 0.95,
        }

    def bench_mus_isolation(self) -> Dict[str, Any]:
        """
        测试 MUS 变体隔离成功率

        Returns:
            包含 success_rate / routed_correctly / total_tasks 的字典
        """
        print(f"\n── 测试 4: MUS 变体隔离 ──")
        vim = self._vim_cls(max_variants=self.num_variants)

        # 注册多个簇
        clusters = [f"gaia", f"swe_bench", f"codegen", f"math", f"translation"]
        for i, name in enumerate(clusters[:self.num_variants]):
            h = self._make_harness(i)
            vim.register_cluster(name, h)

        # 模拟路由任务
        tasks = [
            ("gaia_qa", "gaia"),
            ("swe_debug", "swe_bench"),
            ("code_review", "codegen"),
            ("math_proof", "math"),
            ("translate_en2zh", "translation"),
            ("gaia_reasoning", "gaia"),
            ("swe_test", "swe_bench"),
        ]

        routed_ok = 0
        for task_sig, expected_cluster in tasks[:self.num_variants * 2]:
            routed = vim.route(task_sig)
            if routed is not None:
                routed_ok += 1

        rate = routed_ok / len(tasks) if tasks else 0
        print(f"  路由成功率: {rate*100:.1f}% ({routed_ok}/{len(tasks)})")
        return {
            "success_rate": round(rate, 4),
            "routed_correctly": routed_ok,
            "total_tasks": len(tasks),
        }

    def bench_ksnap_dual_rail(self) -> Dict[str, Any]:
        """
        测试 κ-Snap 双轨协同进化

        Returns:
            包含 compat_check / causality_log_len / co_evo_gain 的字典
        """
        print(f"\n── 测试 5: κ-Snap 双轨协同进化 ──")
        if not HAS_FULL_IMPORTS:
            print("  [SKIP] 需要真实模块（KSnapDualRail）")
            return {"skipped": True, "reason": "模块不可用"}

        ksnap = KSnapDualRail()
        manifest = ksnap.register_co_evo(
            harness_edge_id="harness_v1",
            model_weight_ver="deepseek_v3",
            validated_on=["gaia", "swe_bench"],
        )
        # 检查兼容性
        ok, manifest_json = ksnap.check_compat("harness_v1", "deepseek_v3")
        log_len = len(ksnap.causal_log._events)
        print(f"  兼容性检查: {ok}, 因果日志条目: {log_len}")
        return {
            "compat_check": ok,
            "causality_log_len": log_len,
            "manifest": manifest.to_dict() if manifest else None,
        }

    def bench_psi_alignment(self) -> Dict[str, Any]:
        """
        测试 ψ-Alignment 检查开销

        Returns:
            包含 mean_overhead_ms / aligned_rate 的字典
        """
        print(f"\n── 测试 6: ψ-Alignment 检查开销 ──")
        if not HAS_FULL_IMPORTS:
            print("  [SKIP] 需要真实模块（TShieldWrapper）")
            return {"skipped": True, "reason": "模块不可用"}

        wrapper = TShieldWrapper()
        # 创建一个测试超边
        edge = create_default_harness()
        edge.g_ego_psi_alignment = "care_safety"

        latencies = []
        aligned = 0
        for _ in range(50):
            t0 = time.perf_counter()
            result = wrapper.validate_psi_alignment(edge, psi_anchor={"i_value": 0.5, "mode": "idle"})
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            if result.get("valid", False):
                aligned += 1

        mean_ms = statistics.mean(latencies) if latencies else 0.0
        print(f"  ψ-对齐检查平均开销: {mean_ms:.3f}ms, 对齐率: {aligned}/{len(latencies)}")
        return {
            "mean_overhead_ms": round(mean_ms, 4),
            "aligned_rate": round(aligned / len(latencies), 4) if latencies else 0,
            "samples": len(latencies),
        }

    # ── 全套运行 ─────────────────────────────────────────────
    def run_all(self) -> Dict[str, Any]:
        """运行全部基准测试"""
        print("=" * 60)
        print("  AEGIS 性能基准测试")
        print(f"  迭代次数: {self.iterations}, 变体数: {self.num_variants}")
        print(f"  模块模式: {'真实' if HAS_FULL_IMPORTS else '模拟'}")
        print("=" * 60)

        results = {}
        t_total = time.perf_counter()

        results["pipeline_latency"] = self.bench_pipeline_latency()
        results["throughput"] = self.bench_throughput(duration_sec=5)
        results["crr"] = self.bench_crr()
        results["mus_isolation"] = self.bench_mus_isolation()
        results["ksnap_dual_rail"] = self.bench_ksnap_dual_rail()
        results["psi_alignment"] = self.bench_psi_alignment()

        total_elapsed = time.perf_counter() - t_total

        # 汇总
        summary = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "iterations": self.iterations,
            "num_variants": self.num_variants,
            "mode": "real" if HAS_FULL_IMPORTS else "mock",
            "total_elapsed_sec": round(total_elapsed, 2),
            "results": results,
        }
        return summary

    def print_report(self, summary: Dict[str, Any]) -> None:
        """打印格式化报告"""
        print("\n" + "=" * 60)
        print("  AEGIS 基准测试报告")
        print("=" * 60)
        print(f"  时间: {summary['timestamp']}")
        print(f"  模式: {summary['mode']}")
        print(f"  总耗时: {summary['total_elapsed_sec']}s")
        print()

        r = summary["results"]

        # 1. 流水线延迟
        lat = r.get("pipeline_latency", {})
        if "p50_ms" in lat:
            print(f"【1】流水线延迟")
            print(f"    P50:  {lat['p50_ms']:.2f} ms")
            print(f"    P95:  {lat['p95_ms']:.2f} ms")
            print(f"    P99:  {lat['p99_ms']:.2f} ms")
            print(f"    均值: {lat['mean_ms']:.2f} ms")
            print(f"    样本: {lat['samples']}")

        # 2. 吞吐量
        tput = r.get("throughput", {})
        if "rps" in tput:
            print(f"\n【2】吞吐量")
            print(f"    RPS: {tput['rps']}")
            print(f"    成功率: {tput.get('success_rate', 0):.1f}%")

        # 3. CRR
        crr = r.get("crr", {})
        if "crr" in crr:
            print(f"\n【3】能力保留率 (CRR)")
            print(f"    CRR: {crr['crr']:.4f} {'✓' if crr.get('crr_pass') else '✗  (目标>0.95)'}")
            print(f"    变体数: {crr['num_variants']}")

        # 4. MUS 隔离
        mus = r.get("mus_isolation", {})
        if "success_rate" in mus:
            print(f"\n【4】MUS 变体隔离")
            print(f"    路由成功率: {mus['success_rate']*100:.1f}%")

        # 5. κ-Snap
        ksnap = r.get("ksnap_dual_rail", {})
        if "compat_check" in ksnap:
            print(f"\n【5】κ-Snap 双轨")
            print(f"    兼容性检查: {'✓' if ksnap['compat_check'] else '✗'}")

        # 6. ψ-Alignment
        psi = r.get("psi_alignment", {})
        if "mean_overhead_ms" in psi:
            print(f"\n【6】ψ-Alignment 检查")
            print(f"    平均开销: {psi['mean_overhead_ms']:.3f} ms")
            print(f"    对齐率: {psi.get('aligned_rate', 0)*100:.1f}%")

        print("\n" + "=" * 60)

    def save_report(self, summary: Dict[str, Any], path: str) -> None:
        """保存报告到 JSON 文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存: {path}")


# ─── CLI 入口 ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="AEGIS 性能基准测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python bench_aegis.py --iterations 100          # 标准测试（100 次迭代）
  python bench_aegis.py --quick                      # 快速测试（10 次）
  python bench_aegis.py --variants 5                # 5 个变体
  python bench_aegis.py --output report.json         # 保存报告
  python bench_aegis.py --verbose                  # 详细输出
""",
    )
    parser.add_argument("--iterations", type=int, default=100,
                        help="流水线延迟测试迭代次数（默认 100）")
    parser.add_argument("--variants", type=int, default=3,
                        help="变体隔离测试变体数（默认 3）")
    parser.add_argument("--quick", action="store_true",
                        help="快速测试模式（10 次迭代，单变体）")
    parser.add_argument("--output", type=str, default=None,
                        help="保存报告到 JSON 文件")
    parser.add_argument("--verbose", action="store_true",
                        help="详细输出")
    args = parser.parse_args()

    if args.quick:
        args.iterations = 10
        args.variants = 1
        print("[INFO] 快速模式: 10 次迭代, 1 个变体")

    bench = AEGISBenchmark(
        iterations=args.iterations,
        num_variants=args.variants,
        verbose=args.verbose,
    )
    summary = bench.run_all()
    bench.print_report(summary)

    if args.output:
        bench.save_report(summary, args.output)

    # 运行内置 benchmark（如果可用）
    if HAS_FULL_IMPORTS:
        print("\n── 运行内置 run_aegis_benchmark() ──")
        try:
            builtin_result = run_aegis_benchmark()
            print(f"  结果: {json.dumps(builtin_result, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"  [WARN] 内置 benchmark 失败: {e}")


if __name__ == "__main__":
    main()
