#=============================================================================
# create_vivado_project.tcl — Vivado Project Creation Script
# T-Shield Cognitive Safety Layer — Zynq-7000
#
# Usage:
#   vivado -mode batch -source create_vivado_project.tcl
#
# Creates a complete Vivado project with:
#   - Zynq-7000 Processing System (PS)
#   - T-Shield PL accelerators
#   - AXI interconnect
#   - Block design + synthesis + implementation
#=============================================================================

# Project settings
set project_name "tshield_zynq"
set project_dir "./vivado_project"
set part_name "xc7z020clg400-1"   ;# Zynq-7020 (common on ZedBoard/Pynq-Z1)

# Create project
create_project $project_name $project_dir -part $part_name -force

# Add RTL source files
add_files [list \
    "../tshield_pl_top.v" \
    "../deadzone_comp_array.v" \
    "../mus_similarity_engine.v" \
    "../axi_lite_slave.v" \
    "../bram_threshold.v" \
]

# Add testbench files (simulation only)
add_files -fileset sim_1 [list \
    "../tb_deadzone_comp_array.v" \
    "../tb_mus_similarity_engine.v" \
]

# Set top module
set_property top tshield_pl_top [current_fileset]

# Set testbench top for simulation
set_property top tb_deadzone_comp_array [get_filesets sim_1]

#=============================================================================
# Create Block Design with Zynq PS
#=============================================================================
create_block_design -name "tshield_system"

# Add Zynq Processing System
set ps_cell [create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 ps7]

# Apply board preset (ZedBoard)
apply_bd_automation [get_bd_cells ps7] -rules [list \
    ZYNQ [get_bd_cells ps7] \
]

# Configure PS:
# - Enable AXI GP0 master port (for PL register access)
# - Enable IRQ fabric interrupt
set_property -dict [list \
    CONFIG.PCW_USE_M_AXI_GP0 {1} \
    CONFIG.PCW_USE_S_AXI_GP0 {0} \
    CONFIG.PCW_IRQ_F2P_INTR {1} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} \
] [get_bd_cells ps7]

# Add AXI Interconnect (1 master from PS, 1 slave to T-Shield)
set axi_interconnect [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_interconnect_0]
set_property -dict [list \
    CONFIG.NUM_MI {1} \
] [get_bd_cells axi_interconnect_0]

# Connect PS AXI GP0 to interconnect
connect_bd_intf [get_bd_intf_pins ps7/M_AXI_GP0] [get_bd_intf_pins axi_interconnect_0/S00_AXI]

# Connect T-Shield PL top as AXI slave
# (In real design, the tshield_pl_top module's AXI interface would be wrapped
#  as an IP core and connected here. This script sets up the infrastructure.)
connect_bd_intf [get_bd_intf_pins axi_interconnect_0/M00_AXI] \
    [create_bd_intf_port -mode Slave -vlnv xilinx.com:interface:aximm_rtl:1.0 S00_AXI]

# Connect clocks and resets
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins axi_interconnect_0/ACLK]
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins axi_interconnect_0/S00_ACLK]
connect_bd_net [get_bd_pins ps7/FCLK_CLK0] [get_bd_pins axi_interconnect_0/M00_ACLK]
connect_bd_net [get_bd_pins ps7/FCLK_RESET0_N] [get_bd_pins axi_interconnect_0/ARESETN]
connect_bd_net [get_bd_pins ps7/FCLK_RESET0_N] [get_bd_pins axi_interconnect_0/S00_ARESETN]
connect_bd_net [get_bd_pins ps7/FCLK_RESET0_N] [get_bd_pins axi_interconnect_0/M00_ARESETN]

# Connect interrupts from PL to PS
create_bd_port -dir I -from 1 -to 0 irq_pl
connect_bd_net [get_bd_ports irq_pl] [get_bd_pins ps7/IRQ_F2P]

# Validate and save block design
validate_bd_design
save_bd_design

# Create HDL wrapper
make_wrapper -files [get_files $project_dir/$project_name.srcs/sources_1/bd/tshield_system/tshield_system.bd] -top
add_files -norecurse $project_dir/$project_name.gen/sources_1/bd/tshield_system/hdl/tshield_system_wrapper.v

# Set wrapper as top
set_property top tshield_system_wrapper [current_fileset]

# Run synthesis
launch_runs synth_1 -jobs 4
wait_on_run synth_1

# Check synthesis status
if {[get_property STATUS [get_runs synth_1]] != "synth_design Complete!"} {
    puts "ERROR: Synthesis failed!"
    exit 1
}

# Run implementation
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1

# Check implementation status
if {[get_property STATUS [get_runs impl_1]] != "write_bitstream Complete!"} {
    puts "ERROR: Implementation failed!"
    exit 1
}

# Export hardware (for Vitis/XSDK)
write_hw_platform -fixed -include_bit -force ./tshield_zynq.xsa

puts "=============================================="
puts "  T-Shield Zynq-7000 project created!"
puts "  Bitstream: [get_property DIRECTORY [get_runs impl_1]]/tshield_pl_top.bit"
puts "  HW export: ./tshield_zynq.xsa"
puts "=============================================="
