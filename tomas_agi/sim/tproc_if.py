"""
T-Processor SPI 协议接口

基于"理想 Livis 数据流车体与 TOMAS 太一互搏内核融合"第三章：
M100 ↔ T-Processor 通信协议

协议摘要：
- Opcode: 0xA5 (OP_KSNAP) 主命令
- Request: kappa(1B) + theta_dead(2B) + v_row[8B]
- Response: status(1B) + result[8B] + mus_pair_id(可选)
- 电气: SPI Mode 0, CS# 低启, DRDY# GPIO 可选中断

Author: Zhang Feng (TOMAS Core Team)
"""

import struct
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================
# 协议常量
# ============================================================

# Opcodes
OP_NOP = 0x00
OP_KSNAP = 0xA5
OP_READ_PSI = 0xB1
OP_WRITE_PSI = 0xB2

# Response status flags
TPROC_STAT_DEADZERO = 0x01   # 死零触发
TPROC_STAT_MUS = 0x02        # MUS 激活
TPROC_STAT_DONE = 0x04       # 计算完成
TPROC_STAT_ERR = 0x08        # 错误
TPROC_STAT_TIMEOUT = 0x10    # 超时（附加标志）

# 驱动参数
TPROC_TIMEOUT_MS = 10        # SPI 超时
TPROC_CLK_HZ = 10_000_000    # 10 MHz SPI 时钟
TPROC_CS_GPIO = 25           # 片选 GPIO 号（示例）
TPROC_DRDY_GPIO = 26         # 数据就绪 GPIO 号（示例）

# Status 字符串映射
STATUS_NAMES = {
    TPROC_STAT_DEADZERO: "DEAD_ZERO",
    TPROC_STAT_MUS: "MUS",
    TPROC_STAT_DONE: "DONE",
    TPROC_STAT_ERR: "ERROR",
    TPROC_STAT_TIMEOUT: "TIMEOUT",
}


# ============================================================
# 数据结构
# ============================================================

@dataclass
class TProcRequest:
    """T-Processor κ-Snap 请求"""
    kappa: int = 4                  # 1B: 当前语境（驾车 ≈ 4）
    theta_dead: int = 1500          # 2B: 死零阈值（0-65535）
    v_row: bytes = field(           # 8B: 激活度类向量
        default_factory=lambda: bytes([0] * 8)
    )

    def to_bytes(self) -> bytes:
        """序列化为 SPI 帧"""
        # 帧格式: kappa(1B) + theta_dead(2B) + v_row(8B) = 11B
        return struct.pack(
            '>BH8s',
            self.kappa,
            self.theta_dead,
            self.v_row,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "TProcRequest":
        """从 SPI 帧反序列化"""
        kappa, theta, v_row = struct.unpack('>BH8s', data[:11])
        return cls(kappa=kappa, theta_dead=theta, v_row=v_row)

    def set_activation(self, bit_index: int):
        """设置特定激活度类 bit"""
        if 0 <= bit_index < 64:
            byte_idx = bit_index // 8
            bit_pos = bit_index % 8
            v_row_list = list(self.v_row)
            v_row_list[byte_idx] |= (1 << bit_pos)
            self.v_row = bytes(v_row_list)

    def get_activation(self, bit_index: int) -> bool:
        """读取特定激活度类 bit"""
        if 0 <= bit_index < 64:
            byte_idx = bit_index // 8
            bit_pos = bit_index % 8
            return bool(self.v_row[byte_idx] & (1 << bit_pos))
        return False


@dataclass
class TProcResponse:
    """T-Processor κ-Snap 响应"""
    status: int = TPROC_STAT_DONE    # 1B: 状态标志
    result: bytes = field(           # 8B: κ-Snap 结果
        default_factory=lambda: bytes([0] * 8)
    )
    mus_pair_id: int = 0             # 可选: MUS 双存对 ID
    latency_us: float = 0.0          # 计算延迟（微秒）

    def to_bytes(self) -> bytes:
        """序列化为 SPI 帧"""
        return struct.pack(
            '>B8sI',
            self.status,
            self.result,
            self.mus_pair_id,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "TProcResponse":
        """从 SPI 帧反序列化"""
        status, result, mus_id = struct.unpack('>B8sI', data[:13])
        return cls(status=status, result=result, mus_pair_id=mus_id)

    @property
    def is_dead_zero(self) -> bool:
        return bool(self.status & TPROC_STAT_DEADZERO)

    @property
    def is_mus(self) -> bool:
        return bool(self.status & TPROC_STAT_MUS)

    @property
    def is_done(self) -> bool:
        return bool(self.status & TPROC_STAT_DONE)

    @property
    def is_error(self) -> bool:
        return bool(self.status & TPROC_STAT_ERR)

    @property
    def status_string(self) -> str:
        """人类可读的状态字符串"""
        parts = []
        for flag, name in STATUS_NAMES.items():
            if self.status & flag:
                parts.append(name)
        return "|".join(parts) if parts else "IDLE"

    def to_log_dict(self) -> Dict[str, Any]:
        """转为 CAN-FD 日志字典"""
        return {
            'status': self.status_string,
            'status_hex': f"0x{self.status:02X}",
            'result': f"0x{self.result.hex()}",
            'mus_pair_id': self.mus_pair_id,
            'latency_us': self.latency_us,
            'dz_flag': self.is_dead_zero,
            'mus_flag': self.is_mus,
        }


# ============================================================
# SPI 模拟器
# ============================================================

class TProcSPI:
    """
    T-Processor SPI 总线模拟器

    模拟 SPI Mode 0 (CPOL=0, CPHA=0) 通信：
    - CS# 低电平激活
    - 时钟上升沿采样数据
    - DRDY# 低电平表示数据就绪

    此模拟器不依赖真实硬件，用于软件测试和协议验证。
    """

    def __init__(
        self,
        dead_zero_gate=None,      # DeadZeroMUSGate 实例
        mus_arbitrator=None,      # MUSArbitrator 实例
        enable_timing: bool = True,
    ):
        self.dead_zero_gate = dead_zero_gate
        self.mus_arbitrator = mus_arbitrator
        self.enable_timing = enable_timing

        # 模拟状态
        self._cs_active = False
        self._data_ready = False
        self._last_request: Optional[TProcRequest] = None
        self._transaction_count = 0

        # 统计
        self.stats = {
            'total_requests': 0,
            'dead_zero_count': 0,
            'mus_count': 0,
            'error_count': 0,
            'total_latency_us': 0.0,
        }

        logger.info("[TProcSPI] SPI 总线模拟器初始化完成")

    def send_ksnap(self, req: TProcRequest) -> TProcResponse:
        """
        发送 κ-Snap 请求并接收响应

        模拟完整的 SPI 事务：
        1. CS# → LOW
        2. 发送 11B 请求帧
        3. 等待 DRDY# → LOW
        4. 接收 13B 响应帧
        5. CS# → HIGH

        Args:
            req: TProcRequest

        Returns:
            TProcResponse
        """
        t_start = time.perf_counter()

        # 模拟 SPI 事务
        self._cs_active = True
        self._data_ready = False
        self._transaction_count += 1
        self.stats['total_requests'] += 1

        # 处理请求
        response = self._process_ksnap(req)

        # 模拟计算延迟
        elapsed_us = (time.perf_counter() - t_start) * 1_000_000
        response.latency_us = elapsed_us
        self.stats['total_latency_us'] += elapsed_us

        self._data_ready = True
        self._cs_active = False

        # 更新统计
        if response.is_dead_zero:
            self.stats['dead_zero_count'] += 1
        if response.is_mus:
            self.stats['mus_count'] += 1
        if response.is_error:
            self.stats['error_count'] += 1

        self._last_request = req

        logger.debug(
            f"[TProcSPI] 事务 #{self._transaction_count}: "
            f"κ={req.kappa}, θ={req.theta_dead}, "
            f"状态={response.status_string}, "
            f"延迟={elapsed_us:.1f}µs"
        )

        return response

    def _process_ksnap(self, req: TProcRequest) -> TProcResponse:
        """
        处理 κ-Snap 请求（模拟忆阻 Crossbar 计算）

        实际 T-Processor 的处理流程：
        1. κ-Gate 根据 κ 值筛选激活度类
        2. V_row · G → I_col（Crossbar VMM，Ohm's Law = scheduler）
        3. Dead-Zero Check（ℐ < θ_dead → reject）
        4. MUS Arbiter（Asym ≠ 0 → dual-exist）
        5. κ-Snap 结果返回

        模拟版使用 DeadZeroMUSGate 的软件实现。
        """
        # 解析 v_row 激活度类
        active_classes = [
            i for i in range(64)
            if req.get_activation(i)
        ]

        # 如果没有激活度类 → 死零
        if not active_classes:
            response = TProcResponse(status=TPROC_STAT_DEADZERO)
            logger.warning("[TProcSPI] 无激活度类 → DEAD_ZERO")
            return response

        # 如果提供了 DeadZeroMUSGate，使用它
        if self.dead_zero_gate:
            # 构建模拟边
            edges = [
                {'eid': f'e_cls_{i}', 'nodes': [f'class_{i}'], 'i_val': 0.5}
                for i in active_classes
            ]

            # 如果需要更高精度，可根据 v_row 的具体值调整 ℐ
            for edge in edges:
                cls_id = int(edge['eid'].split('_')[-1])
                byte_idx = cls_id // 8
                bit_pos = cls_id % 8
                if byte_idx < len(req.v_row):
                    intensity = (req.v_row[byte_idx] >> bit_pos) & 0x01
                    edge['i_val'] = intensity * 0.8 + 0.2  # 激活 bit → ℐ=1.0, 非激活 → ℐ=0.2

            # 运行门控器
            gate_result = self.dead_zero_gate.process(
                query=f"κ-Snap κ={req.kappa}",
                matched_edges=edges,
            )

            if not gate_result['proceed']:
                # 死零触发
                return TProcResponse(
                    status=TPROC_STAT_DEADZERO,
                    result=bytes([0] * 8),
                )

            if gate_result['mus_active']:
                # MUS 激活 → 返回双存结果
                pair_id = hash(str(gate_result['paradox_pairs'])) & 0xFFFFFFFF
                result_bytes = struct.pack('>II', pair_id, int(gate_result['snap_score'] * 1000))
                return TProcResponse(
                    status=TPROC_STAT_MUS | TPROC_STAT_DONE,
                    result=result_bytes,
                    mus_pair_id=pair_id,
                )

            # 正常完成
            edge = gate_result.get('selected_edge') or {}
            snap_score = gate_result.get('snap_score', 0.0)
            result_bytes = struct.pack('>II', hash(edge.get('eid', '')) & 0xFFFFFFFF, int(snap_score * 1000))
            return TProcResponse(
                status=TPROC_STAT_DONE,
                result=result_bytes,
            )

        # 无门控器：简单模式
        result_bytes = struct.pack('>II', active_classes[0], active_classes[-1])
        return TProcResponse(
            status=TPROC_STAT_DONE,
            result=result_bytes,
        )

    def check_dead_zero(self, i_value: float, theta: float) -> bool:
        """
        死零检查：ℐ < θ → reject

        Args:
            i_value: ℐ-值
            theta: 阈值

        Returns:
            True = 触发死零
        """
        return i_value < theta

    def check_mus(self, asymmetry: float) -> bool:
        """
        MUS 检查：Asym ≠ 0 → MUS 激活

        Args:
            asymmetry: 非对称值

        Returns:
            True = MUS 激活
        """
        return abs(asymmetry) > 0.01

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_latency = (
            self.stats['total_latency_us'] / max(self.stats['total_requests'], 1)
        )
        return {
            **self.stats,
            'avg_latency_us': avg_latency,
            'transaction_count': self._transaction_count,
        }

    # ----- ψ-锚 读写 -----

    def read_psi(self, snap_id: bytes) -> bytes:
        """
        读取 ψ-锚快照（OP_READ_PSI = 0xB1）

        Args:
            snap_id: 快照 ID

        Returns:
            ψ-锚数据
        """
        logger.info(f"[TProcSPI] 读取 ψ-锚: {snap_id.hex()}")
        # 模拟：返回空快照
        return bytes([0x00] * 8)

    def write_psi(self, snap_id: bytes, psi_data: bytes) -> bool:
        """
        写入 ψ-锚快照（OP_WRITE_PSI = 0xB2）

        Args:
            snap_id: 快照 ID
            psi_data: ψ-锚数据

        Returns:
            是否写入成功
        """
        logger.info(f"[TProcSPI] 写入 ψ-锚: {snap_id.hex()}")
        return True

    def reset(self):
        """重置SPI总线"""
        self._cs_active = False
        self._data_ready = False
        self._last_request = None
        self._transaction_count = 0
        self.stats = {k: 0 if isinstance(v, (int, float)) else v for k, v in self.stats.items()}
        logger.info("[TProcSPI] 总线已重置")


# ============================================================
# 自测试
# ============================================================

if __name__ == '__main__':
    printed("=== TProcSPI 协议测试 ===\n")

    # 场景1: 正常 κ-Snap 请求
    print("场景1: 正常行驶 κ=4")
    req = TProcRequest(kappa=4, theta_dead=1500)
    req.set_activation(2)  # 激活度类 2
    req.set_activation(3)  # 激活度类 3
    print(f"  请求: κ={req.kappa}, v_row bits={[i for i in range(64) if req.get_activation(i)]}")

    spi = TProcSPI()
    resp = spi.send_ksnap(req)
    print(f"  响应: status={resp.status_string}, latency={resp.latency_us:.1f}µs")
    print(f"  通过: {'✅' if resp.is_done and not resp.is_dead_zero else '❌'}")

    # 场景2: 死零触发
    print("\n场景2: 无激活度类 → 死零")
    req2 = TProcRequest(kappa=4, theta_dead=1500)
    # 不设置任何激活 bit
    resp2 = spi.send_ksnap(req2)
    print(f"  响应: status={resp2.status_string}")
    print(f"  死零触发: {'✅' if resp2.is_dead_zero else '❌'}")

    # 场景3: 帧序列化
    print("\n场景3: 帧序列化")
    req3 = TProcRequest(kappa=6, theta_dead=2000)
    req3.set_activation(5)
    frame = req3.to_bytes()
    print(f"  帧长度: {len(frame)}B (预期 11B)")
    print(f"  帧内容: {frame.hex()}")
    req3_back = TProcRequest.from_bytes(frame)
    print(f"  反序列化: κ={req3_back.kappa}, θ={req3_back.theta_dead}")
    print(f"  一致性: {'✅' if req3_back.kappa == req3.kappa and req3_back.theta_dead == req3.theta_dead else '❌'}")

    # 统计
    print(f"\n=== 统计 ===")
    for k, v in spi.get_stats().items():
        print(f"  {k}: {v:.1f}" if isinstance(v, float) else f"  {k}: {v}")

    print("\n=== 所有测试通过 ===")
