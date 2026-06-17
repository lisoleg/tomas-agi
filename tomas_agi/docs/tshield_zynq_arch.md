# T-Shield Zynq-7000 硬件架构设计

**作者**: 高见远（Gao）· 架构师  
**日期**: 2026-06-17  
**版本**: 1.0  

---

## 1. 系统概述

### 1.1 Zynq-7000 SoC 架构

```
┌─────────────────────────────────────────────────────┐
│              Zynq-7000 SoC                         │
├─────────────────────────────────────────────────────┤
│  PS (Processing System)                           │
│  ┌─────────────────────────────────────────────┐  │
│  │  ARM Cortex-A9 双核 @ 866 MHz             │  │
│  │  - 运行 Linux 操作系统                    │  │
│  │  - T-Shield 主控制逻辑                   │  │
│  │  - κ-Snap 调度器 (复杂状态机)           │  │
│  └─────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│  PL (Programmable Logic)                          │
│  ┌─────────────────────────────────────────────┐  │
│  │  Artix-7 FPGA                              │  │
│  │  - Dead-Zero 比较器阵列 (并行)           │  │
│  │  - MUS 相似度引擎 (点积加速)            │  │
│  │  - DMA 引擎 (高速数据传输)               │  │
│  └─────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│  接口                                              │
│  - AXI4-Lite: 控制寄存器访问 (低频)              │
│  - AXI4-Stream: 数据流传输 (高速)               │
│  - BRAM: PL 端本地存储 (阈值表、激活值)         │
└─────────────────────────────────────────────────────┘
```

### 1.2 T-Shield 任务划分

| 模块 | 位置 | 理由 |
|------|------|------|
| **Dead-Zero Grafting** | PL (RTL) | 批量比较操作，可完全并行化 |
| **MUS Dual-Box Marking** | PL (RTL) | 矩阵相似度计算，可用并行点积 |
| **κ-Snap Scheduling** | PS (C/Python) | 事件驱动状态机，逻辑复杂，适合软件实现 |
| **I-Scene Estimator** | PS (C + NEON) | 特征向量 norm 计算，可用 NEON SIMD 加速 |

---

## 2. PS-PL 任务划分

### 2.1 PS 端 (ARM Cortex-A9)

**主要职责**：
1. 运行主程序（Python/C）
2. κ-Snap 调度器（状态机逻辑）
3. I-Scene 估计（可用 NEON SIMD 优化）
4. 与 PL 通信（通过 AXI 总线）

**软件栈**：
```
┌─────────────────────────────┐
│   Python 应用层            │  ← TShieldWrapper.infer()
├─────────────────────────────┤
│   C 库 (libtshield.so)    │  ← PS-PL 接口封装
├─────────────────────────────┤
│   Linux 内核               │  ← AXI DMA 驱动
├─────────────────────────────┤
│   硬件抽象层 (HAL)         │  ← 寄存器读写
└─────────────────────────────┘
```

### 2.2 PL 端 (Artix-7 FPGA)

**主要职责**：
1. **Dead-Zero Comparator Array**：并行比较输入向量与阈值
2. **MUS Similarity Engine**：批量计算余弦相似度（点积）
3. **DMA Engine**：高速传输数据（PS ↔ PL）
4. **Control Registers**：接收 PS 命令，返回状态

**RTL 模块划分**：
```
┌──────────────────────────────────────────┐
│           T-Shield PL 顶层             │
├──────────────────────────────────────────┤
│  axi_lite_slave.v                     │  ← AXI4-Lite 从设备
├──────────────────────────────────────────┤
│  deadzone_comp_array.v                │  ← Dead-Zero 比较器阵列
│  - 32 个并行比较器                   │
│  - 每个: 比较 1 个激活值 vs 阈值   │
├──────────────────────────────────────────┤
│  mus_similarity_engine.v               │  ← MUS 相似度引擎
│  - 点积计算阵列                       │
│  - 并行计算 N 个框的相似度          │
├──────────────────────────────────────────┤
│  dma_engine.v                         │  ← DMA 引擎
│  - AXI DMA 封装                      │
│  - 批量传输检测框数据                │
├──────────────────────────────────────────┤
│  bram_threshold.v                     │  ← BRAM 阈值存储
│  - 存储 Dead-Zero 阈值表             │
│  - 存储 MUS 相似度阈值              │
└──────────────────────────────────────────┘
```

---

## 3. AXI 接口定义

### 3.1 AXI4-Lite 控制接口 (PS → PL)

**寄存器映射**（PL 端寄存器）：

| 地址偏移 | 寄存器名 | 读写 | 描述 |
|----------|----------|------|------|
| 0x00 | `CTRL` | RW | 控制寄存器 |
| 0x04 | `STATUS` | R | 状态寄存器 |
| 0x08 | `DZ_THRESH` | RW | Dead-Zero 阈值 (定点数 Q8.8) |
| 0x0C | `MUS_IOU_THRESH` | RW | MUS IoU 阈值 (Q0.16) |
| 0x10 | `MUS_CONF_DIFF` | RW | MUS 置信度差阈值 (Q0.16) |
| 0x14 | `INPUT_LEN` | RW | 输入向量长度 |
| 0x18 | `OUTPUT_LEN` | R | 输出标记数量 |
| 0x20-0x7F | `INPUT_BUF` | W | 输入数据缓冲区 (32x 32-bit) |
| 0x80-0xDF | `OUTPUT_BUF` | R | 输出标记缓冲区 (32x 32-bit) |

**控制寄存器位定义** (`CTRL`, 地址 0x00)：
```
Bit [0]: START - 1=启动计算, 0=空闲
Bit [1]: RESET - 1=复位 PL, 0=正常
Bit [2]: IE (Interrupt Enable) - 1=使能中断, 0=禁用
Bit [3]: MODE - 0=Dead-Zero 模式, 1=MUS 模式
Bits [31:4]: 保留
```

**状态寄存器位定义** (`STATUS`, 地址 0x04)：
```
Bit [0]: READY - 1=PL 就绪, 0=忙碌
Bit [1]: DONE - 1=计算完成, 0=进行中
Bit [2]: ERROR - 1=错误, 0=正常
Bits [31:3]: 保留
```

### 3.2 AXI4-Stream 数据流接口 (PS ↔ PL)

**用于批量数据传输**（比 AXI4-Lite 快）：

```
PS (ARM)                          PL (FPGA)
    │                                 │
    │  1. 写输入数据                 │
    │  ──── AXI DMA ──────────────► │
    │     (检测框坐标、置信度)       │
    │                                 │
    │  2. 启动计算                   │
    │  ──── AXI-Lite (CTRL) ─────► │
    │                                 │
    │  3. 读结果                     │
    │  ◄──── AXI DMA ─────────────── │
    │     (标记后的检测框)           │
    │                                 │
    │  4. 读状态                    │
    │  ◄──── AXI-Lite (STATUS) ──── │
    └─────────────────────────────────┘
```

**数据流协议**：
- **TLAST**: 标记数据包末尾
- **TKEEP**: 标记有效字节
- **TVALID / TREADY**: 握手信号

---

## 4. RTL 模块设计

### 4.1 Dead-Zero Comparator Array (`deadzone_comp_array.v`)

**功能**：并行比较 32 个激活值是否低于阈值。

**接口定义**：
```verilog
module deadzone_comp_array (
    input  wire        clk,
    input  wire        rst_n,
    
    // AXI4-Lite 从接口
    input  wire [31:0] s_axil_awaddr,
    input  wire        s_axil_awvalid,
    output wire        s_axil_awready,
    input  wire [31:0] s_axil_wdata,
    input  wire        s_axil_wvalid,
    output wire        s_axil_wready,
    output wire [1:0] s_axil_bresp,
    output wire        s_axil_bvalid,
    input  wire        s_axil_bready,
    
    // 输入数据 (来自 BRAM 或 DMA)
    input  wire [31:0] input_data [31:0],  // 32 个 32-bit 激活值
    input  wire        input_valid,
    
    // 输出结果
    output wire [1:0]  output_levels [31:0], // 每个激活值的等级 (00=SAFE, 01=WARNING, 10=DEAD)
    output wire        output_valid
);
```

**算法**：
```verilog
// 伪代码
for (i = 0; i < 32; i = i + 1) begin
    if (input_data[i] < DZ_THRESH * WARNING_RATIO) begin
        output_levels[i] <= 2'b10;  // DEAD
    end
    else if (input_data[i] < DZ_THRESH) begin
        output_levels[i] <= 2'b01;  // WARNING
    end
    else begin
        output_levels[i] <= 2'b00;  // SAFE
    end
end
```

**时序**：
- 延迟: 1 个时钟周期 (组合逻辑 + 寄存器)
- 吞吐量: 每个周期处理 32 个激活值

### 4.2 MUS Similarity Engine (`mus_similarity_engine.v`)

**功能**：计算检测框之间的余弦相似度 (点积)。

**接口定义**：
```verilog
module mus_similarity_engine (
    input  wire        clk,
    input  wire        rst_n,
    
    // 控制接口
    input  wire        start,
    input  wire [7:0] num_boxes,  // 检测框数量 (N)
    
    // 输入: 检测框特征向量 (来自 DMA)
    input  wire [31:0] box_features [63:0][15:0],  // 64 个框, 每个 16 维
    
    // 输出: 相似度矩阵 (上三角)
    output wire [15:0] similarity_matrix [63:0][63:0],  // N x N 矩阵
    output wire        done
);
```

**算法** (向量化点积)：
```verilog
// 计算余弦相似度 = dot(a, b) / (||a|| * ||b||)
// 简化: 只计算 dot(a, b) (假设特征已归一化)

// 并行计算所有框对
for (i = 0; i < N; i = i + 1) begin
    for (j = i+1; j < N; j = j + 1) begin
        dot_product = 0;
        for (k = 0; k < 16; k = k + 1) begin
            dot_product += box_features[i][k] * box_features[j][k];
        end
        similarity_matrix[i][j] = dot_product[15:0];  // Q0.16 格式
    end
end
```

**优化**：
- 使用**流水线** (pipeline) 提高吞吐量
- 使用 **DSP48E1**  slice (FPGA 内置乘法器)

**时序**：
- 延迟: N² × 16 个周期 (无优化) → 可优化到 N² 个周期 (完全并行)
- 吞吐量: 每个周期完成 1 次点积 (优化后)

### 4.3 DMA Engine (`dma_engine.v`)

**功能**：在 PS 和 PL 之间高速传输数据。

**接口**：使用 Xilinx AXI DMA IP 核 (无需自己写 RTL，直接例化)

```verilog
// 例化 AXI DMA (官方 IP)
axi_dma_0 dma_inst (
    .s_axi_lite_aclk(clk),
    .s_axi_lite_aresetn(rst_n),
    
    // PS 端 (AXI4-Lite 配置)
    .s_axi_lite_awaddr(s_axil_awaddr),
    .s_axi_lite_awvalid(s_axil_awvalid),
    .s_axi_lite_awready(s_axil_awready),
    // ... (省略其他 AXI 信号)
    
    // PL 端 (AXI4-Stream 数据流)
    .m_axis_mm2s_tdata(m_axis_mm2s_tdata),  // PS → PL
    .m_axis_mm2s_tvalid(m_axis_mm2s_tvalid),
    .m_axis_mm2s_tready(m_axis_mm2s_tready),
    
    .s_axis_s2mm_tdata(s_axis_s2mm_tdata),  // PL → PS
    .s_axis_s2mm_tvalid(s_axis_s2mm_tvalid),
    .s_axis_s2mm_tready(s_axis_s2mm_tready)
);
```

---

## 5. 存储架构

### 5.1 PS 端存储 (DRAM)

**容量**: 512 MB - 1 GB (Zynq-7000 支持)

**存储内容**：
- **EML 图谱**: 完整知识图谱 (44.7 GB 数据库)
- **检测历史**: 最近 N 帧的检测框 (用于 κ-Snap 调度)
- **配置参数**: Dead-Zero 阈值、MUS 阈值等

**访问方式**：
- C 指针 (libtshield.so)
- Python `numpy.ndarray` (通过 C 扩展访问)

### 5.2 PL 端存储 (BRAM)

**容量**: 36 Kb - 18 Mb (取决于 FPGA 型号)

**存储内容**：
- **阈值表**: Dead-Zero 阈值 (32-bit × 32 个)
- **临时激活值**: 当前批次的激活值 (32-bit × 32 个)
- **输出标记**: Dead-Zero 等级、MUS 标记 (2-bit × 32 个)

**BRAM 分配**：
```
┌────────────────────────────────┐
│  BRAM (36 Kb)               │
├──────────────────────────────┤
│  0x00-0x7F: 阈值表         │  ← 32 个 32-bit 阈值
├──────────────────────────────┤
│  0x80-0xFF: 输入缓冲区     │  ← 32 个 32-bit 激活值
├──────────────────────────────┤
│  0x100-0x17F: 输出标记    │  ← 32 个 2-bit 等级
└──────────────────────────────┘
```

---

## 6. 时序要求

### 6.1 时钟频率

| 时钟域 | 频率 | 来源 |
|--------|------|------|
| PS 时钟 | 866 MHz | ARM Cortex-A9 内部 |
| PL 时钟 | 100 MHz | Zynq PS 提供 (FCLK_CLK0) |
| AXI 时钟 | 50 MHz | AXI 总线标准频率 |

### 6.2 延迟要求

**目标**: 单帧处理延迟 < 1 ms

**延迟分解**：
```
PS 端预处理:        ~50 μs  (Python → C 调用)
AXI DMA 传输:      ~100 μs (传输 32 个框 @ 50 MHz)
PL 计算:           ~10 μs  (100 MHz, 1000 周期)
AXI DMA 回传:      ~100 μs
PS 端后处理:       ~50 μs
─────────────────────────────
总计:               ~310 μs  <  1 ms  ✅
```

### 6.3 吞吐量要求

**目标**: 30 FPS (视频流实时处理)

**吞吐量计算**：
- 单帧延迟: 310 μs
- 最大 FPS: 1 / 310 μs ≈ 3225 FPS

**结论**: 完全可以满足 30 FPS 要求，甚至可以达到 100+ FPS。

---

## 7. 开发流程

### 7.1 RTL 仿真 (Icarus Verilog)

```bash
# 编译
iverilog -o sim.out tb_deadzone_comp_array.v deadzone_comp_array.v

# 运行仿真
vvp sim.out

# 查看波形 (GTKWave)
gtkwave dump.vcd
```

### 7.2 综合与实现 (Vivado)

```tcl
# 1. 创建项目
create_project tshield_zynq ./vivado_proj -part xc7z020clg484-1

# 2. 添加 RTL 源文件
add_files [glob ./rtl/*.v]

# 3. 综合
launch_runs synth_1
wait_on_run synth_1

# 4. 实现
launch_runs impl_1
wait_on_run impl_1

# 5. 生成比特流
launch_runs impl_1 -to_step write_bitstream
wait_on_run impl_1

# 6. 导出硬件描述 (for PetaLinux)
write_hw_def -dir ./hw_def
```

### 7.3 PS 端软件开发

**步骤**：
1. **PetaLinux 构建** (PS 端 Linux)
   ```bash
   petalinux-create -t project -n tshield_linux
   petalinux-config -c kernel  # 启用 AXI DMA 驱动
   petalinux-build
   ```

2. **编写 C 库** (`libtshield.so`)
   ```c
   // tshield.c
   #include <stdio.h>
   #include "xil_io.h"  // Xilinx 硬件抽象层
   
   #define AXI_BASE_ADDR 0x43C00000  // PL 端 AXI 基地址
   
   void tshield_init() {
       // 配置 AXI DMA
       Xil_Out32(AXI_BASE_ADDR + 0x30, 0x1);  // 启动 DMA
   }
   
   void tshield_run(float *input, int len) {
       // 1. 写输入数据到 PL
       for (int i = 0; i < len; i++) {
           Xil_Out32(AXI_BASE_ADDR + 0x20 + i*4, input[i]);
       }
       
       // 2. 启动计算
       Xil_Out32(AXI_BASE_ADDR + 0x00, 0x1);
       
       // 3. 等待完成
       while ((Xil_In32(AXI_BASE_ADDR + 0x04) & 0x1) == 0);
       
       // 4. 读结果
       // ...
   }
   ```

3. **Python 绑定** (通过 `ctypes`)
   ```python
   # tshield_wrapper.py
   import ctypes
   lib = ctypes.CDLL('./libtshield.so')
   
   def infer(detections):
       # 调用 C 库
       lib.tshield_run(detections, len(detections))
   ```

---

## 8. 验证计划

### 8.1 RTL 仿真测试

**测试平台** (`tb_deadzone_comp_array.v`)：
```verilog
module tb_deadzone_comp_array;
    reg clk;
    reg [31:0] input_data [31:0];
    wire [1:0] output_levels [31:0];
    
    // 例化 DUT
    deadzone_comp_array dut (.clk(clk), .input_data(input_data), .output_levels(output_levels));
    
    // 测试向量
    initial begin
        clk = 0;
        input_data[0] = 32'h00000005;  // < threshold (DEAD)
        input_data[1] = 32'h0000CCCC;  // between threshold and warning (WARNING)
        input_data[2] = 32'h00010000;  // > threshold (SAFE)
        
        #100;  // 等待 100 ns
        $display("Output levels: %b, %b, %b", output_levels[0], output_levels[1], output_levels[2]);
        $finish;
    end
    
    always #5 clk = ~clk;  // 100 MHz 时钟
endmodule
```

### 8.2 板级测试 (ZedBoard)

**硬件**：
- **开发板**: Digilent ZedBoard (Zynq-7000)
- **调试工具**: Xilinx Platform Cable USB II

**测试步骤**：
1. **JTAG 加载比特流**
   ```tcl
   connect -host localhost -port 3121
   target -set -filter {jtag_cable_type == "xilinx_tcf") -index 0
   fpcon -bitstream ./tshield.bit
   ```

2. **PS 端运行测试程序**
   ```bash
   # 在 ZedBoard 上
   root@zedboard:~# ./test_tshield
   ```

3. **抓取信号** (ILA - Integrated Logic Analyzer)
   ```tcl
   # 在 Vivado 中
   create_debug_core u_ila_0 ila
   set_property port_width 32 [get_debug_ports u_ila_0/probe0]
   connect_debug_port u_ila_0/probe0 [get_nets -hierarchical -filter {NAME =~ *input_data*}]
   ```

---

## 9. 性能预估

### 9.1 资源利用率 (Zynq-7020 CLG484-1)

| 资源 | 可用 | 使用 | 利用率 |
|------|------|------|--------|
| **LUT** | 53,200 | ~8,000 | ~15% |
| **FF** | 106,400 | ~4,000 | ~4% |
| **BRAM** | 140 (36 Kb) | ~10 | ~7% |
| **DSP** | 220 | ~32 | ~15% |

**结论**: T-Shield PL 加速器只占很少资源，还有大量空间用于其他加速器。

### 9.2 性能对比 (软件 vs 硬件加速)

| 指标 | 纯软件 (PS) | 硬件加速 (PL) | 加速比 |
|------|--------------|----------------|--------|
| **Dead-Zero 检查** (32 个框) | ~50 μs | ~10 μs | **5x** |
| **MUS 相似度计算** (32×32) | ~500 μs | ~50 μs | **10x** |
| **总延迟** | ~600 μs | ~100 μs | **6x** |
| **功耗** | ~2 W (ARM) | ~0.5 W (FPGA) | **4x 节省** |

---

## 10. 下一步工作

### 10.1 待完成任务

- [ ] **RTL 代码编写** (寇豆码)
  - `deadzone_comp_array.v`
  - `mus_similarity_engine.v`
  - `axi_lite_slave.v`
  
- [ ] **PS-PL 接口代码** (寇豆码)
  - C 库 (`libtshield.so`)
  - Python 绑定 (`tshield_wrapper.py`)
  
- [ ] **Vivado 项目创建** (寇豆码)
  - 创建 Vivado 项目
  - 综合、实现、生成比特流
  
- [ ] **板级测试** (严过关)
  - 在 ZedBoard 上验证
  - 编写测试报告

### 10.2 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| AXI DMA 传输不稳定 | 中 | 高 | 使用 Xilinx 官方 IP (经过验证) |
| 时序不满足 (100 MHz) | 低 | 中 | 降低 PL 时钟到 50 MHz |
| BRAM 容量不足 | 低 | 低 | 使用 DRAM (通过 AXI DMA) |

---

## 11. 附录

### 11.1 参考文献

1. Xilinx, "Zynq-7000 SoC Technical Reference Manual", UG585, 2022.
2. Xilinx, "AXI DMA v7.1 LogiCORE IP Product Guide", PG021, 2023.
3. Xilinx, "Vivado Design Suite User Guide: Design Flows Overview", UG892, 2023.

### 11.2 术语表

- **PS**: Processing System (ARM Cortex-A9)
- **PL**: Programmable Logic (Artix-7 FPGA)
- **AXI**: Advanced eXtensible Interface (ARM AMBA 总线)
- **BRAM**: Block RAM (FPGA 内置 RAM)
- **DMA**: Direct Memory Access (直接内存访问)
- **ILA**: Integrated Logic Analyzer (集成逻辑分析仪)

---

**文档结束**
