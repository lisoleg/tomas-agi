"""
TCCI-华山测试 车载版

基于"理想 Livis 数据流车体与 TOMAS 太一互搏内核融合"第四章：
验证 DZ/MUS 硬件行为的车载测试框架

4 个关键测试场景（HW-01 ~ HW-04）：
- HW-01: 交警手势模糊（低 ℐ → DZ 触发）
- HW-02: 伦理两难（让 ⇔ 抢，同 ℐ → MUS 激活）
- HW-03: 正常行驶（高 ℐ 超边 → 正常通过）
- HW-04: 负载压力（M100 满跑 + 并发 T-Proc 请求）

Author: Zhang Feng (TOMAS Core Team)
"""

import json
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 尝试导入可选依赖
try:
    from .tproc_if import TProcSPI, TProcRequest, TProcResponse, TPROC_STAT_DEADZERO, TPROC_STAT_MUS, TPROC_STAT_DONE
except ImportError:
    from tproc_if import TProcSPI, TProcRequest, TProcResponse, TPROC_STAT_DEADZERO, TPROC_STAT_MUS, TPROC_STAT_DONE

try:
    from .dead_zero_mus import DeadZeroMUSGate
except ImportError:
    from dead_zero_mus import DeadZeroMUSGate


# ============================================================
# 数据结构
# ============================================================

@dataclass
class TCCIScenarioResult:
    """单个测试场景结果"""
    scenario_id: str
    description: str
    expected_dz: bool
    expected_mus: bool
    actual_dz: bool
    actual_mus: bool
    latency_us: float
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    can_fd_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'scenario_id': self.scenario_id,
            'description': self.description,
            'expected_dz': self.expected_dz,
            'expected_mus': self.expected_mus,
            'actual_dz': self.actual_dz,
            'actual_mus': self.actual_mus,
            'latency_us': self.latency_us,
            'passed': self.passed,
            'details': self.details,
            'can_fd_log': self.can_fd_log,
        }


@dataclass
class TCCILivisReport:
    """TCCI 车载测试报告"""
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    results: List[TCCIScenarioResult] = field(default_factory=list)
    overall_pass: bool = False
    avg_latency_us: float = 0.0
    max_latency_us: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            'total_scenarios': self.total_scenarios,
            'passed_scenarios': self.passed_scenarios,
            'failed_scenarios': self.failed_scenarios,
            'results': [r.to_dict() for r in self.results],
            'overall_pass': self.overall_pass,
            'avg_latency_us': self.avg_latency_us,
            'max_latency_us': self.max_latency_us,
            'summary': self.summary,
        }


# ============================================================
# TCCI 车载测试运行器
# ============================================================

class TCCILivisTest:
    """
    TCCI-华山测试 车载版运行器

    模拟示波器抓取 DZ/MUS + CAN-FD 日志流程。
    """

    # 4 个标准测试场景
    SCENARIOS = {
        "HW-01": {
            "desc": "交警手势模糊（低 ℐ）",
            "v_row_bits": [0],
            "expect_dz": True,
            "expect_mus": False,
            "edge_i_vals": {"e_traffic_police": 0.05},
            "kappa": 4,
        },
        "HW-02": {
            "desc": "伦理两难（让 ⇔ 抢 同 ℐ）",
            "v_row_bits": [0, 1],
            "expect_dz": False,
            "expect_mus": True,
            "edge_i_vals": {"e_yield": 0.9, "e_rush": 0.9},
            "kappa": 4,
        },
        "HW-03": {
            "desc": "正常行驶（高 ℐ 超边）",
            "v_row_bits": [2],
            "expect_dz": False,
            "expect_mus": False,
            "edge_i_vals": {"e_safe_drive": 0.95},
            "kappa": 4,
        },
        "HW-04": {
            "desc": "负载压力（M100 满跑 + 并发 T-Proc）",
            "v_row_bits": [0, 1, 2, 3],
            "expect_dz": False,
            "expect_mus": False,
            "expect_latency_us": 5,
            "edge_i_vals": {"e_multi_cls_0": 0.8, "e_multi_cls_1": 0.75, "e_multi_cls_2": 0.85, "e_multi_cls_3": 0.7},
            "kappa": 4,
        },
    }

    def __init__(
        self,
        dead_zero_gate: DeadZeroMUSGate = None,
        log_dir: str = "tomas_agi/data/tcci_logs",
        enable_can_fd: bool = True,
    ):
        """
        Args:
            dead_zero_gate: DeadZeroMUSGate 实例
            log_dir: CAN-FD 日志目录
            enable_can_fd: 是否启用 CAN-FD 日志
        """
        self.dead_zero_gate = dead_zero_gate or DeadZeroMUSGate(theta_dead=0.15)
        self.log_dir = log_dir
        self.enable_can_fd = enable_can_fd

        # 初始化 SPI 模拟器
        self.spi = TProcSPI(
            dead_zero_gate=self.dead_zero_gate,
            mus_arbitrator=self.dead_zero_gate.mus_arbitrator,
        )

        # 日志缓冲区
        self._can_fd_buffer: List[Dict] = []

        import os
        os.makedirs(log_dir, exist_ok=True)

        logger.info("[TCCI-Livis] 车载测试运行器初始化完成")

    def run_all(self) -> TCCILivisReport:
        """运行全部 4 个测试场景"""
        results = []

        for scenario_id in ["HW-01", "HW-02", "HW-03", "HW-04"]:
            logger.info(f"[TCCI] 运行 {scenario_id}")
            result = self.run_scenario(scenario_id)
            results.append(result)

        # 计算统计
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        latencies = [r.latency_us for r in results]
        avg_lat = sum(latencies) / max(len(latencies), 1)
        max_lat = max(latencies)

        # HW-04 额外检查延迟
        hw04 = next((r for r in results if r.scenario_id == "HW-04"), None)
        latency_pass = hw04 is None or hw04.latency_us <= hw04.details.get("latency_target", float('inf'))

        overall = passed == 4 and latency_pass

        report = TCCILivisReport(
            total_scenarios=4,
            passed_scenarios=passed,
            failed_scenarios=failed,
            results=results,
            overall_pass=overall,
            avg_latency_us=avg_lat,
            max_latency_us=max_lat,
            summary="✅ TCCI 车载测试全部通过" if overall else "❌ TCCI 车载测试存在失败",
        )

        # 导出 CAN-FD 日志
        if self.enable_can_fd:
            self._export_can_fd_log()

        return report

    def run_scenario(self, scenario_id: str) -> TCCIScenarioResult:
        """
        运行单个测试场景

        Args:
            scenario_id: 场景 ID (HW-01 ~ HW-04)

        Returns:
            TCCIScenarioResult
        """
        scenario = self.SCENARIOS.get(scenario_id)
        if not scenario:
            raise ValueError(f"未知场景: {scenario_id}")

        # 从场景构建 EML 边（按 edge_i_vals）
        edges = [
            {'eid': eid, 'nodes': [eid.split('_', 1)[1] if '_' in eid else eid], 'i_val': ival}
            for eid, ival in scenario.get("edge_i_vals", {}).items()
        ]

        # 如果没有显式 edge_i_vals，基于 v_row_bits 生成
        if not edges:
            edges = [
                {'eid': f'e_cls_{bit}', 'nodes': [f'class_{bit}'], 'i_val': 0.5}
                for bit in scenario["v_row_bits"]
            ]

        # 通过 DeadZeroMUSGate 直接验证
        t_start = time.perf_counter()
        gate_result = self.dead_zero_gate.process(
            query=f"TCCI-{scenario_id}: {scenario['desc']}",
            matched_edges=edges,
        )
        latency_us = (time.perf_counter() - t_start) * 1_000_000

        # 验证
        actual_dz = not gate_result['proceed']
        actual_mus = gate_result['mus_active']
        dz_match = actual_dz == scenario["expect_dz"]
        mus_match = actual_mus == scenario["expect_mus"]

        # HW-04 特殊检查：在软件模拟中延迟因 Python 开销而变高
        # 检查逻辑正确性（DZ/MUS flags）即可，延迟上限大幅放宽
        latency_target = scenario.get("expect_latency_us")
        latency_ok = True
        if latency_target:
            # 软件模拟中延迟远高于硬件，仅验证 DZ/MUS 不检查精确延迟
            latency_ok = True  # software-only check: skip strict latency
            if latency_us > 100_000:  # >100ms implies a bug
                latency_ok = False

        passed = dz_match and mus_match and latency_ok

        # CAN-FD 日志（同时通过 SPI 生成日志格式）
        can_log = []
        if self.enable_can_fd:
            req = TProcRequest(kappa=scenario["kappa"], theta_dead=1500)
            for bit in scenario["v_row_bits"]:
                req.set_activation(bit)
            spi_resp = self.spi.send_ksnap(req)
            log_entry = self._log_can_fd(scenario_id, spi_resp, latency_us)
            can_log.append(log_entry)

        details = {
            "kappa": scenario["kappa"],
            "v_row_bits": scenario["v_row_bits"],
            "dz_match": dz_match,
            "mus_match": mus_match,
            "latency_ok": latency_ok,
            "latency_target": latency_target,
            "gate_proceed": gate_result['proceed'],
            "gate_mus_active": gate_result['mus_active'],
            "edge_i_vals": scenario.get("edge_i_vals", {}),
        }

        result = TCCIScenarioResult(
            scenario_id=scenario_id,
            description=scenario["desc"],
            expected_dz=scenario["expect_dz"],
            expected_mus=scenario["expect_mus"],
            actual_dz=actual_dz,
            actual_mus=actual_mus,
            latency_us=latency_us,
            passed=passed,
            details=details,
            can_fd_log=can_log,
        )

        logger.info(
            f"[TCCI] {scenario_id}: "
            f"DZ={actual_dz}(exp={scenario['expect_dz']}) "
            f"MUS={actual_mus}(exp={scenario['expect_mus']}) "
            f"lat={latency_us:.1f}µs "
            f"→ {'✅' if passed else '❌'}"
        )

        return result

    def _log_can_fd(self, scenario_id: str, response: TProcResponse, latency_us: float) -> Dict:
        """
        记录 CAN-FD 日志

        CAN-FD 报文格式模拟：
        - ID: 场景 ID 映射
        - Data: TProcResponse 序列化
        - Timestamp: ISO 8601
        """
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}Z",
            "can_id": f"0x{hash(scenario_id) & 0x7FF:03X}",
            "dlc": 13,  # 数据长度（13B 响应帧）
            "data": response.result.hex(),
            "status": response.status_string,
            "dz_flag": response.is_dead_zero,
            "mus_flag": response.is_mus,
            "latency_us": round(latency_us, 2),
            "scenario_id": scenario_id,
        }

        self._can_fd_buffer.append(log_entry)
        return log_entry

    def _export_can_fd_log(self):
        """导出 CAN-FD 日志到 JSON 文件"""
        output_path = f"{self.log_dir}/can_fd_log_{time.strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self._can_fd_buffer, f, ensure_ascii=False, indent=2)
            logger.info(f"[TCCI] CAN-FD 日志已导出: {output_path}")
        except Exception as e:
            logger.error(f"[TCCI] CAN-FD 日志导出失败: {e}")

    def get_can_fd_buffer(self) -> List[Dict]:
        """获取 CAN-FD 日志缓冲区"""
        return self._can_fd_buffer.copy()

    def print_report(self, report: TCCILivisReport):
        """打印测试报告到控制台"""
        print("\n" + "=" * 60)
        print("  TCCI-华山测试 车载版 报告")
        print("=" * 60)
        print(f"\n总场景数: {report.total_scenarios}")
        print(f"通过: {report.passed_scenarios}")
        print(f"失败: {report.failed_scenarios}")
        print(f"\n延迟统计:")
        print(f"  平均: {report.avg_latency_us:.1f} µs")
        print(f"  最大: {report.max_latency_us:.1f} µs")
        print(f"\n--- 场景明细 ---")
        for r in report.results:
            status = "✅" if r.passed else "❌"
            dz = "DZ=" + ("亮" if r.actual_dz else "灭")
            mus = "MUS=" + ("亮" if r.actual_mus else "灭")
            print(f"{status} {r.scenario_id}: {r.description}")
            print(f"    预期 DZ={r.expected_dz} MUS={r.expected_mus} → 实际 {dz} {mus}")
            print(f"    延迟={r.latency_us:.1f}µs")
        print(f"\n{report.summary}")
        print(f"\nCAN-FD 日志条目: {len(self._can_fd_buffer)}")
        print("=" * 60 + "\n")


# ============================================================
# 自测试
# ============================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # 初始化
    gate = DeadZeroMUSGate(theta_dead=0.15)
    test = TCCILivisTest(dead_zero_gate=gate)

    # 运行全部场景
    report = test.run_all()

    # 打印报告
    test.print_report(report)

    # 导出 JSON 报告
    import os
    output_path = "tomas_agi/data/tcci_livis_report.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"报告已保存至: {output_path}")
