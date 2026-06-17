# ============================================================
# TOMAS-AGI v2.0 FPGA RTL 编译框架
# 含 NASGA M5 谱计算 + T-Shield 认知安全层
# ============================================================

# 仿真器（Icarus Verilog 或 Verilator）
IVERILOG ?= iverilog
VVP     ?= vvp

# ---- NASGA M5 谱计算源文件 ----
M5_SRC := octonion_mul.v delta_compute.v spectral_engine.v

# ---- T-Shield 认知安全层源文件 ----
TSHIELD_SRC := deadzone_comp_array.v mus_similarity_engine.v \
               axi_lite_slave.v bram_threshold.v tshield_pl_top.v

# 全部源文件
RTL_SRC := $(M5_SRC) $(TSHIELD_SRC)

# 测试模块
TB_OCT     := tb_octonion_mul
TB_DELTA   := tb_delta_compute
TB_SPEC    := tb_spectral_engine
TB_DZ      := tb_deadzone_comp_array
TB_MUS     := tb_mus_similarity_engine

# 输出目录
BUILD := build

.PHONY: all sim-oct sim-delta sim-spec sim-dz sim-mus sim-tshield synth clean

all: $(BUILD)
	@echo "FPGA RTL 就绪。可用目标:"
	@echo "  make sim-oct      — 八元数乘法器仿真"
	@echo "  make sim-delta    — δ 计算单元仿真"
	@echo "  make sim-spec     — 谱计算引擎仿真"
	@echo "  make sim-dz       — Dead-Zone 比较器阵列仿真"
	@echo "  make sim-mus      — MUS 相似度引擎仿真"
	@echo "  make sim-tshield  — T-Shield 完整仿真"

$(BUILD):
	mkdir -p $(BUILD)

# ---- 八元数乘法器仿真 ----
sim-oct: $(BUILD)/$(TB_OCT).vvp
	$(VVP) $<

$(BUILD)/$(TB_OCT).vvp: octonion_mul.v | $(BUILD)
	$(IVERILOG) -o $@ $<

# ---- δ 计算单元仿真 ----
sim-delta: $(BUILD)/$(TB_DELTA).vvp
	$(VVP) $<

$(BUILD)/$(TB_DELTA).vvp: octonion_mul.v delta_compute.v | $(BUILD)
	$(IVERILOG) -o $@ $^

# ---- 谱计算引擎仿真 ----
sim-spec: $(BUILD)/$(TB_SPEC).vvp
	$(VVP) $<

$(BUILD)/$(TB_SPEC).vvp: octonion_mul.v delta_compute.v spectral_engine.v | $(BUILD)
	$(IVERILOG) -o $@ $^

# ---- Dead-Zone 比较器阵列仿真 ----
sim-dz: $(BUILD)/$(TB_DZ).vvp
	$(VVP) $<

$(BUILD)/$(TB_DZ).vvp: deadzone_comp_array.v tb_deadzone_comp_array.v | $(BUILD)
	$(IVERILOG) -o $@ $^

# ---- MUS 相似度引擎仿真 ----
sim-mus: $(BUILD)/$(TB_MUS).vvp
	$(VVP) $<

$(BUILD)/$(TB_MUS).vvp: mus_similarity_engine.v tb_mus_similarity_engine.v | $(BUILD)
	$(IVERILOG) -o $@ $^

# ---- T-Shield 完整仿真 (DZ + MUS) ----
sim-tshield: sim-dz sim-mus
	@echo "T-Shield 全部仿真完成。"

# ---- Vivado 项目创建 ----
vivado:
	vivado -mode batch -source create_vivado_project.tcl

# ---- 综合估算（需要 Vivado/Yosys）----
synth:
	@echo "请使用 Vivado 或 Yosys 进行综合"
	@echo "  Vivado: make vivado"
	@echo "  Yosys:  yosys > read_verilog $(TSHIELD_SRC); synth_xilinx -top tshield_pl_top"

# ---- 清理 ----
clean:
	rm -rf $(BUILD)
