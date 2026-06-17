"""
T-Processor + T-Shield 集成模块
================================

将 T-Processor v1.0 硬件仿真器与 T-Shield 认知安全层集成为统一推理管道。

架构:
    输入 → T-Processor (计算) → T-Shield (安全检查) → 输出
           ↓                                          ↓
      RRAM Crossbar                           Dead-Zero + MUS

应用场景:
    - 视觉目标检测 + 认知安全保障
    - 自主系统 (无人机、机器人) 的安全性推理
    - 工业检测 (实时 + 安全)

作者: 寇豆码（Kou）· 工程师
日期: 2026-06-17
版本: 1.0.0
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np
import time


# ============================================================
# 导入依赖模块
# ============================================================

from .tshield_wrapper import (
    TShieldWrapper, DetectionBox, SceneAssessment,
    DZLevel, MUSStatus,
    ISceneEstimator, DeadZeroGraft, MUSBoxMarker, KSnapScheduler,
)

from .tprocessor_sim import (
    TProcessorV1, RRAMCrossbar, DeadZeroComparator,
    MUSArbiter, KSnapScheduler as TProcessorKSnapScheduler,
)


# ============================================================
# T-Processor + T-Shield 联合推理器
# ============================================================

@dataclass
class JointInferenceResult:
    """联合推理结果"""
    # T-Processor 输出
    i_out: np.ndarray          # 输出电流向量
    dz_levels: List[DZLevel]   # 死零等级

    # T-Shield 输出
    scene_assessment: Dict     # 场景评估
    safety_veto: bool          # 安全否决 (True = 停止推理)
    recommendations: List[str] # 建议操作

    # 性能指标
    processor_latency_ms: float
    shield_latency_ms: float
    total_latency_ms: float

    # 元数据
    timestamp: float
    config_id: int


class TProcessorV1WithTShield:
    """
    T-Processor v1.0 硬件仿真器 + T-Shield 认知安全层联合推理器

    工作流程:
    1. T-Processor 前向计算 (RRAM Crossbar 存算一体)
    2. T-Shield 安全检查 (Dead-Zero Grafting + MUS 标记)
    3. 安全投票 (Safety Voting)
    4. 输出联合推理结果

    示例用法:
        >>> tp = TProcessorV1WithTShield()
        >>> tp.define_crossbar(32, 16, conductance_min=1e-6, conductance_max=1e-3)
        >>> result = tp.tick_with_shield(v_in, detections, image)
        >>> print(f"安全: {result.safety_veto}")
    """

    def __init__(self, dead_zero_epsilon: float = 1e-3):
        """
        初始化联合推理器

        Args:
            dead_zero_epsilon: Dead-Zero 比较器阈值 (共享)
        """
        self.tprocessor = TProcessorV1()
        self.tshield = TShieldWrapper()

        # 共享配置
        self.dead_zero_epsilon = dead_zero_epsilon
        self.safety_threshold = 0.3  # 安全阈值 (低于此值触发否决)

        # 统计
        self.stats = {
            "n_ticks": 0,
            "n_vetos": 0,
            "n_normal": 0,
            "total_processor_time": 0.0,
            "total_shield_time": 0.0,
        }

    def define_crossbar(
        self,
        n_rows: int,
        n_cols: int,
        conductance_min: float = 1e-6,
        conductance_max: float = 1e-3,
    ):
        """
        定义 RRAM Crossbar

        Args:
            n_rows: 行数 (输入维度)
            n_cols: 列数 (输出维度)
            conductance_min: 最小电导
            conductance_max: 最大电导
        """
        self.tprocessor.define_crossbar(n_rows, n_cols, conductance_min, conductance_max)

    def tick_with_shield(
        self,
        v_in: np.ndarray,
        detections: List[Dict],
        image: Optional[np.ndarray] = None,
    ) -> JointInferenceResult:
        """
        联合推理: T-Processor 计算 + T-Shield 安全检查

        Args:
            v_in: 输入电压向量 (用于 T-Processor)
            detections: 检测结果列表 (用于 T-Shield)
            image: 输入图像 (可选, 用于 I-Scene 估计)

        Returns:
            JointInferenceResult: 联合推理结果
        """
        timestamp = time.time()
        self.stats["n_ticks"] += 1

        # ============================================================
        # 阶段 1: T-Processor 前向计算
        # ============================================================
        t0 = time.perf_counter()
        proc_result = self.tprocessor.tick(v_in)
        processor_latency = time.perf_counter() - t0
        self.stats["total_processor_time"] += processor_latency

        # ============================================================
        # 阶段 2: Dead-Zero 比较 (T-Processor 输出)
        # ============================================================
        dz_comparator = DeadZeroComparator(epsilon=self.dead_zero_epsilon)
        dz_levels = dz_comparator.batch_check(proc_result["i_out"])

        # ============================================================
        # 阶段 3: T-Shield 安全检查
        # ============================================================
        t0 = time.perf_counter()

        if image is None:
            # 如果没有图像，用模拟特征
            image_features = np.random.random(512) * 0.5
        else:
            image_features = image.reshape(-1)[:512].astype(np.float64) / 255.0

        shield_result = self.tshield.infer(image_features.reshape(1, -1, 1), detections)
        shield_latency = time.perf_counter() - t0
        self.stats["total_shield_time"] += shield_latency

        # ============================================================
        # 阶段 4: 安全投票 (Safety Voting)
        # ============================================================
        safety_veto = False
        recommendations = []

        # 4.1: Dead-Zero 否决
        dead_count = sum(1 for level in dz_levels if level == DZLevel.DEAD)
        if dead_count > len(dz_levels) * 0.5:
            safety_veto = True
            recommendations.append(
                f"死零否决: {dead_count}/{len(dz_levels)} 通道处于死零状态"
            )

        # 4.2: I-Scene 否决
        i_scene = shield_result.get("i_scene", 0.0)
        if i_scene < self.safety_threshold:
            safety_veto = True
            recommendations.append(f"I-Scene 否决: 场景显著性 {i_scene:.3f} 低于阈值 {self.safety_threshold}")

        # 4.3: MUS 歧义否决
        n_ambiguous = len(shield_result.get("ambiguous_pairs", []))
        if n_ambiguous > 3:
            recommendations.append(f"MUS 警告: {n_ambiguous} 个歧义对")

        # 4.4: 死零检测框
        dead_indices = shield_result.get("dead_indices", [])
        if len(dead_indices) > 0:
            recommendations.append(f"死零嫁接: {len(dead_indices)} 个低置信度检测框")

        # ============================================================
        # 阶段 5: 组装联合结果
        # ============================================================
        if safety_veto:
            self.stats["n_vetos"] += 1
        else:
            self.stats["n_normal"] += 1

        return JointInferenceResult(
            i_out=proc_result["i_out"],
            dz_levels=list(dz_levels),
            scene_assessment={
                "i_scene": i_scene,
                "dead_zones": shield_result.get("scene_assessment", {}).get("dead_zones", []),
                "ambiguous_boxes": shield_result.get("scene_assessment", {}).get("ambiguous_boxes", []),
            },
            safety_veto=safety_veto,
            recommendations=recommendations,
            processor_latency_ms=processor_latency * 1000,
            shield_latency_ms=shield_latency * 1000,
            total_latency_ms=(processor_latency + shield_latency) * 1000,
            timestamp=timestamp,
            config_id=shield_result.get("config", 0),
        )

    def tick_batch(
        self,
        v_in_batch: np.ndarray,
        detections_batch: List[List[Dict]],
        images_batch: Optional[np.ndarray] = None,
    ) -> List[JointInferenceResult]:
        """
        批量联合推理

        Args:
            v_in_batch: 多帧输入电压 (B, N)
            detections_batch: 多帧检测结果
            images_batch: 多张图像 (B, H, W, C)

        Returns:
            联合推理结果列表
        """
        n = len(detections_batch)
        results = []
        for i in range(n):
            v_in = v_in_batch[i] if v_in_batch.ndim == 2 else v_in_batch
            image = images_batch[i] if images_batch is not None and images_batch.ndim == 4 else None
            result = self.tick_with_shield(v_in, detections_batch[i], image)
            results.append(result)
        return results

    def profile(self, n_iters: int = 100) -> Dict:
        """
        性能基准测试

        Args:
            n_iters: 迭代次数

        Returns:
            性能基准结果
        """
        # 确保 Crossbar 已定义
        if self.tprocessor.rram_crossbar is None:
            self.define_crossbar(32, 16)

        # 生成测试数据
        n = self.tprocessor.rram_crossbar.n_rows
        test_vectors = np.random.random((n_iters, n)).astype(np.float64)

        test_detections = [
            {"box": [0.1, 0.1, 0.3, 0.3], "label": "person", "confidence": np.random.random()},
        ]

        # 性能测试
        times = []
        for i in range(n_iters):
            t0 = time.perf_counter()
            self.tick_with_shield(test_vectors[i], test_detections)
            dt = time.perf_counter() - t0
            times.append(dt)

        times = np.array(times)
        return {
            "n_iters": n_iters,
            "mean_ms": float(np.mean(times) * 1000),
            "median_ms": float(np.median(times) * 1000),
            "std_ms": float(np.std(times) * 1000),
            "min_ms": float(np.min(times) * 1000),
            "max_ms": float(np.max(times) * 1000),
            "throughput_fps": float(n_iters / np.sum(times)),
        }

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "processor": self.tprocessor.get_stats() if hasattr(self.tprocessor, "get_stats") else {},
            "shield": self.tshield.get_stats(),
        }

    def reset_stats(self):
        """重置统计"""
        self.stats = {k: 0.0 if isinstance(v, float) else 0 for k, v in self.stats.items()}


# ============================================================
# 安全包装器 (Safe Execution Wrapper)
# ============================================================

class SafeExecutionWrapper:
    """
    安全执行包装器

    在标准推理管道外层包装 T-Shield 安全检查，
    确保任何推理结果都经过认知安全验证。

    设计模式: 装饰器模式 (Decorator Pattern)
    """

    def __init__(self, model: Any, shield: TProcessorV1WithTShield):
        """
        初始化安全包装器

        Args:
            model: 下游模型 (YOLO, DETR, etc.)
            shield: T-Processor + T-Shield 联合推理器
        """
        self.model = model
        self.shield = shield
        self.blocked_inferences = 0

    def __call__(self, image: np.ndarray) -> Dict:
        """
        调用包装器

        Args:
            image: 输入图像

        Returns:
            {
                "detections": [...],    # 安全增强的检测结果
                "safety_veto": bool,    # 安全否决标志
                "recommendations": [...],  # 安全建议
            }
        """
        # 1. 模型前向推理
        model_output = self.model(image)

        # 2. 提取检测框
        detections = model_output.get("detections", [])
        if len(detections) == 0:
            return model_output

        # 3. T-Shield 安全检查
        v_in = image.reshape(-1)[:32].astype(np.float64) / 255.0
        joint_result = self.shield.tick_with_shield(v_in, detections, image)

        # 4. 应用安全增强
        if joint_result.safety_veto:
            self.blocked_inferences += 1
            model_output["safety_veto"] = True
            model_output["blocked"] = True
            model_output["detections"] = []  # 清空检测结果
            model_output["message"] = "安全否决: " + "; ".join(joint_result.recommendations)
        else:
            model_output["safety_veto"] = False
            model_output["blocked"] = False
            model_output["recommendations"] = joint_result.recommendations

            # 标记低置信度检测框
            for i, det in enumerate(model_output["detections"]):
                if i in joint_result.scene_assessment["dead_zone_indices"]:
                    det["dz_warning"] = "低置信度 — 可能死零"

        return model_output


# ============================================================
# 演示函数
# ============================================================

def demo_integration():
    """
    T-Processor + T-Shield 集成演示
    """
    print("=== T-Processor + T-Shield 集成演示 ===\n")

    # 1. 创建联合推理器
    tp = TProcessorV1WithTShield(dead_zero_epsilon=1e-3)
    tp.define_crossbar(32, 16)

    # 2. 模拟输入
    v_in = np.random.random(32).astype(np.float64)
    detections = [
        {"box": [0.1, 0.1, 0.3, 0.3], "label": "person", "confidence": 0.95},
        {"box": [0.4, 0.4, 0.6, 0.6], "label": "car", "confidence": 0.05},  # 低置信度
        {"box": [0.45, 0.45, 0.55, 0.55], "label": "car", "confidence": 0.08},  # 与上一个歧义
    ]

    # 3. 联合推理
    print("[仿真] 联合推理中...")
    result = tp.tick_with_shield(v_in, detections)

    # 4. 输出结果
    print(f"\nT-Processor 输出维度: {len(result.i_out)}")
    print(f"死零通道数: {sum(1 for level in result.dz_levels if level == DZLevel.DEAD)}")
    print(f"场景显著性 I-Scene: {result.scene_assessment['i_scene']:.3f}")
    print(f"安全否决: {result.safety_veto}")
    print(f"建议: {result.recommendations}")
    print(f"延迟: {result.total_latency_ms:.2f} ms (Processor: {result.processor_latency_ms:.2f} ms, Shield: {result.shield_latency_ms:.2f} ms)")

    # 5. 性能基准
    print("\n[基准测试] 运行 50 次联合推理...")
    profile = tp.profile(n_iters=50)
    print(f"平均延迟: {profile['mean_ms']:.3f} ms")
    print(f"吞吐量: {profile['throughput_fps']:.1f} FPS")

    # 6. 统计
    stats = tp.get_stats()
    print(f"\n[统计] 总推理次数: {tp.stats['n_ticks']}, 安全否决: {tp.stats['n_vetos']}")

    print("\n=== 演示完成 ===")
    return result


if __name__ == "__main__":
    demo_integration()
