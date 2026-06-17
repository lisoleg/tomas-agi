//=============================================================================
// tshield_pl_top.v — T-Shield PL Top-Level Module
// T-Shield Cognitive Safety Layer — Zynq-7000 PL Top
// Target: Xilinx Zynq-7000 (Artix-7 FPGA)
//
// Integrates all T-Shield PL accelerators:
//   1. Dead-Zone Comparator Array
//   2. MUS Similarity Engine
//   3. AXI4-Lite Slave (PS-PL register interface)
//   4. BRAM Threshold Storage
//
// PS (ARM Cortex-A9) handles:
//   - κ-Snap scheduling (software)
//   - Overall pipeline control
//   - Feature extraction and DMA setup
//
// PL (Artix-7 FPGA) handles:
//   - Dead-Zone parallel comparison (32 values/cycle)
//   - MUS pairwise similarity computation (pipelined DSP)
//   - Threshold storage (BRAM)
//=============================================================================

`timescale 1ns / 1ps

module tshield_pl_top #(
    // Dead-Zone parameters
    parameter NUM_ELEMENTS    = 32,
    parameter DATA_WIDTH      = 32,
    parameter LEVEL_WIDTH     = 2,
    parameter THRESH_WIDTH    = 32,

    // MUS parameters
    parameter NUM_BOXES       = 16,
    parameter FEATURE_DIM     = 16,
    parameter FEAT_WIDTH      = 16,
    parameter ACCUM_WIDTH     = 32,
    parameter SIM_WIDTH       = 16,
    parameter CONF_WIDTH      = 16,

    // AXI parameters
    parameter C_S_AXI_DATA_WIDTH = 32,
    parameter C_S_AXI_ADDR_WIDTH = 6
) (
    // Global signals
    input  wire                              clk,          // 100 MHz PL clock
    input  wire                              rst_n,        // Active-low reset

    //=========================================================================
    // AXI4-Lite Slave Interface (PS-PL register access)
    //=========================================================================
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]    s_axi_awaddr,
    input  wire [2:0]                        s_axi_awprot,
    input  wire                              s_axi_awvalid,
    output wire                              s_axi_awready,

    input  wire [C_S_AXI_DATA_WIDTH-1:0]    s_axi_wdata,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0] s_axi_wstrb,
    input  wire                              s_axi_wvalid,
    output wire                              s_axi_wready,

    output wire [1:0]                        s_axi_bresp,
    output wire                              s_axi_bvalid,
    input  wire                              s_axi_bready,

    input  wire [C_S_AXI_ADDR_WIDTH-1:0]    s_axi_araddr,
    input  wire [2:0]                        s_axi_arprot,
    input  wire                              s_axi_arvalid,
    output wire                              s_axi_arready,

    output wire [C_S_AXI_DATA_WIDTH-1:0]    s_axi_rdata,
    output wire [1:0]                        s_axi_rresp,
    output wire                              s_axi_rvalid,
    input  wire                              s_axi_rready,

    //=========================================================================
    // DMA Interface (AXI4-Stream for activation data from PS)
    //=========================================================================
    // Activation value stream (Dead-Zone input)
    input  wire [DATA_WIDTH-1:0]             s_axis_dz_tdata,
    input  wire                              s_axis_dz_tvalid,
    output wire                              s_axis_dz_tready,

    // Feature vector stream (MUS input)
    input  wire [FEAT_WIDTH-1:0]             s_axis_mus_tdata,
    input  wire [7:0]                        s_axis_mus_tuser_box,   // Box index
    input  wire [4:0]                        s_axis_mus_tuser_dim,   // Dimension index
    input  wire                              s_axis_mus_tvalid,
    output wire                              s_axis_mus_tready,

    //=========================================================================
    // DMA Interface (AXI4-Stream for results to PS)
    //=========================================================================
    // Dead-Zone results stream
    output wire [LEVEL_WIDTH*NUM_ELEMENTS-1:0] m_axis_dz_tdata,
    output wire [$clog2(NUM_ELEMENTS)-1:0]     m_axis_dz_dead_cnt,
    output wire [$clog2(NUM_ELEMENTS)-1:0]     m_axis_dz_warn_cnt,
    output wire                                m_axis_dz_tvalid,
    input  wire                                m_axis_dz_tready,

    // MUS ambiguity results stream
    output wire [NUM_BOXES*(NUM_BOXES-1)/2-1:0] m_axis_mus_ambig,
    output wire [7:0]                           m_axis_mus_ambig_cnt,
    output wire                                 m_axis_mus_tvalid,
    input  wire                                 m_axis_mus_tready,

    //=========================================================================
    // Interrupt to PS
    //=========================================================================
    output wire                              irq_dz_done,    // Dead-Zone complete
    output wire                              irq_mus_done    // MUS complete
);

    //=========================================================================
    // Internal wires
    //=========================================================================

    // AXI register outputs
    wire [C_S_AXI_DATA_WIDTH-1:0] reg_ctrl;
    wire [C_S_AXI_DATA_WIDTH-1:0] reg_dz_thresh;
    wire [C_S_AXI_DATA_WIDTH-1:0] reg_warn_thresh;
    wire [C_S_AXI_DATA_WIDTH-1:0] reg_num_boxes;
    wire [C_S_AXI_DATA_WIDTH-1:0] reg_num_acts;
    wire [C_S_AXI_DATA_WIDTH-1:0] reg_ksnap_cfg;

    // Status register inputs (from internal logic)
    reg  [C_S_AXI_DATA_WIDTH-1:0] reg_status;
    reg  [C_S_AXI_DATA_WIDTH-1:0] reg_dz_dead_cnt;
    reg  [C_S_AXI_DATA_WIDTH-1:0] reg_dz_warn_cnt;
    reg  [C_S_AXI_DATA_WIDTH-1:0] reg_mus_ambig_cnt;
    reg  [C_S_AXI_DATA_WIDTH-1:0] reg_iota_scene;

    // Dead-Zone comparator outputs
    wire [LEVEL_WIDTH-1:0] dz_output_levels [0:NUM_ELEMENTS-1];
    wire                   dz_output_valid;
    wire [$clog2(NUM_ELEMENTS)-1:0] dz_dead_count;
    wire [$clog2(NUM_ELEMENTS)-1:0] dz_warning_count;

    // MUS similarity engine outputs
    wire [NUM_BOXES*(NUM_BOXES-1)/2-1:0] mus_ambiguities;
    wire [7:0]                            mus_ambig_count;
    wire                                  mus_ambig_valid;
    wire                                  mus_done;

    // BRAM outputs
    wire [31:0] bram_dz_read_data;
    wire [31:0] bram_warn_read_data;

    // Control signals derived from register
    wire dz_start  = reg_ctrl[0];
    wire mus_start = reg_ctrl[1];
    wire soft_reset = reg_ctrl[2];

    // ℐ-scene computation (simplified: ratio of safe elements)
    // ℐ = (NUM_ELEMENTS - dead_count - warning_count) / NUM_ELEMENTS
    // In Q8.8: ℐ = (256 * (N - dead - warn)) / N
    always @* begin
        reg_iota_scene = (256 * (NUM_ELEMENTS - dz_dead_count - dz_warning_count)) / NUM_ELEMENTS;
    end

    // Status register assembly
    always @* begin
        reg_status     = 0;
        reg_status[0]  = dz_output_valid;    // dz_done
        reg_status[1]  = mus_done;           // mus_done
        reg_status[2]  = dz_start;           // dz_busy
        reg_status[3]  = mus_start;          // mus_busy
        reg_dz_dead_cnt = {24'd0, dz_dead_count};
        reg_dz_warn_cnt = {24'd0, dz_warning_count};
        reg_mus_ambig_cnt = {24'd0, mus_ambig_count};
    end

    //=========================================================================
    // Module instantiation: AXI4-Lite Slave
    //=========================================================================
    axi_lite_slave #(
        .C_S_AXI_DATA_WIDTH (C_S_AXI_DATA_WIDTH),
        .C_S_AXI_ADDR_WIDTH (C_S_AXI_ADDR_WIDTH)
    ) u_axi_lite (
        .clk              (clk),
        .rst_n            (rst_n && !soft_reset),

        // AXI4-Lite interface
        .s_axi_awaddr     (s_axi_awaddr),
        .s_axi_awprot     (s_axi_awprot),
        .s_axi_awvalid    (s_axi_awvalid),
        .s_axi_awready    (s_axi_awready),

        .s_axi_wdata      (s_axi_wdata),
        .s_axi_wstrb      (s_axi_wstrb),
        .s_axi_wvalid     (s_axi_wvalid),
        .s_axi_wready     (s_axi_wready),

        .s_axi_bresp      (s_axi_bresp),
        .s_axi_bvalid     (s_axi_bvalid),
        .s_axi_bready     (s_axi_bready),

        .s_axi_araddr     (s_axi_araddr),
        .s_axi_arprot     (s_axi_arprot),
        .s_axi_arvalid    (s_axi_arvalid),
        .s_axi_arready    (s_axi_arready),

        .s_axi_rdata      (s_axi_rdata),
        .s_axi_rresp      (s_axi_rresp),
        .s_axi_rvalid     (s_axi_rvalid),
        .s_axi_rready     (s_axi_rready),

        // Register interface
        .reg_ctrl         (reg_ctrl),
        .reg_dz_thresh    (reg_dz_thresh),
        .reg_warn_thresh  (reg_warn_thresh),
        .reg_num_boxes    (reg_num_boxes),
        .reg_num_acts     (reg_num_acts),
        .reg_ksnap_cfg    (reg_ksnap_cfg),

        .reg_status       (reg_status),
        .reg_dz_dead_cnt  (reg_dz_dead_cnt),
        .reg_dz_warn_cnt  (reg_dz_warn_cnt),
        .reg_mus_ambig_cnt(reg_mus_ambig_cnt),
        .reg_iota_scene   (reg_iota_scene)
    );

    //=========================================================================
    // Module instantiation: Dead-Zone Comparator Array
    //=========================================================================
    // Unpack DMA stream into array for comparator input
    reg [DATA_WIDTH-1:0] dz_input_data [0:NUM_ELEMENTS-1];
    reg                  dz_input_valid_reg;
    reg [7:0]            dz_element_idx;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dz_element_idx <= 0;
            dz_input_valid_reg <= 0;
        end else begin
            dz_input_valid_reg <= 0;
            if (s_axis_dz_tvalid && s_axis_dz_tready) begin
                dz_input_data[dz_element_idx] <= s_axis_dz_tdata;
                if (dz_element_idx == NUM_ELEMENTS - 1) begin
                    dz_input_valid_reg <= 1;
                    dz_element_idx <= 0;
                end else begin
                    dz_element_idx <= dz_element_idx + 1;
                end
            end
        end
    end

    assign s_axis_dz_tready = 1'b1;  // Always ready to accept data

    deadzone_comp_array #(
        .NUM_ELEMENTS   (NUM_ELEMENTS),
        .DATA_WIDTH     (DATA_WIDTH),
        .LEVEL_WIDTH    (LEVEL_WIDTH),
        .THRESH_WIDTH   (THRESH_WIDTH)
    ) u_deadzone_comp (
        .clk            (clk),
        .rst_n          (rst_n && !soft_reset),

        .dz_start       (dz_start),
        .dz_threshold   (reg_dz_thresh[THRESH_WIDTH-1:0]),
        .warn_threshold (reg_warn_thresh[THRESH_WIDTH-1:0]),

        .input_data     (dz_input_data),
        .input_valid    (dz_input_valid_reg),

        .output_levels  (dz_output_levels),
        .output_valid   (dz_output_valid),
        .dead_count     (dz_dead_count),
        .warning_count  (dz_warning_count)
    );

    //=========================================================================
    // Module instantiation: MUS Similarity Engine
    //=========================================================================
    // Confidence values (loaded via AXI register — simplified: all same)
    reg [CONF_WIDTH-1:0] mus_conf_values [0:NUM_BOXES-1];
    integer conf_init_i;
    initial begin
        for (conf_init_i = 0; conf_init_i < NUM_BOXES; conf_init_i = conf_init_i + 1)
            mus_conf_values[conf_init_i] = 16'h7FFF;  // Default: max confidence
    end

    mus_similarity_engine #(
        .NUM_BOXES      (NUM_BOXES),
        .FEATURE_DIM    (FEATURE_DIM),
        .DATA_WIDTH     (FEAT_WIDTH),
        .ACCUM_WIDTH    (ACCUM_WIDTH),
        .SIM_WIDTH      (SIM_WIDTH),
        .CONF_WIDTH     (CONF_WIDTH)
    ) u_mus_similarity (
        .clk            (clk),
        .rst_n          (rst_n && !soft_reset),

        .start          (mus_start),
        .num_boxes      (reg_num_boxes[7:0]),
        .done           (mus_done),

        .feat_valid     (s_axis_mus_tvalid),
        .feat_box_idx   (s_axis_mus_tuser_box),
        .feat_dim_idx   (s_axis_mus_tuser_dim),
        .feat_data      (s_axis_mus_tdata),

        .conf_values    (mus_conf_values),

        .ambiguities    (mus_ambiguities),
        .ambig_count    (mus_ambig_count),
        .ambig_valid    (mus_ambig_valid),

        // Debug similarity output (unused in top, tied off)
        .sim_addr_i     (),
        .sim_addr_j     (),
        .sim_data_out   (),
        .sim_valid      ()
    );

    assign s_axis_mus_tready = 1'b1;

    //=========================================================================
    // Module instantiation: BRAM Threshold Storage
    //=========================================================================
    bram_threshold #(
        .NUM_ELEMENTS   (NUM_ELEMENTS),
        .ADDR_WIDTH     (6),
        .DATA_WIDTH     (32)
    ) u_bram_threshold (
        .clk            (clk),

        .ps_write_en    (1'b0),       // PS write via AXI (not connected in this version)
        .ps_write_addr  (6'd0),
        .ps_write_data  (32'd0),

        .pl_read_addr   (6'd0),       // Read address (not connected in this version)
        .pl_read_data   (bram_dz_read_data),

        .bulk_load_en   (1'b0),       // Bulk load (not connected in this version)
        .bulk_load_addr (6'd0),
        .bulk_load_data (32'd0),
        .bulk_load_done ()
    );

    //=========================================================================
    // Output packing for DMA streams
    //=========================================================================
    // Pack Dead-Zone levels into a single bus
    genvar dz_i;
    generate
        for (dz_i = 0; dz_i < NUM_ELEMENTS; dz_i = dz_i + 1) begin : gen_dz_pack
            assign m_axis_dz_tdata[dz_i*LEVEL_WIDTH +: LEVEL_WIDTH] = dz_output_levels[dz_i];
        end
    endgenerate

    assign m_axis_dz_dead_cnt = dz_dead_count;
    assign m_axis_dz_warn_cnt = dz_warning_count;
    assign m_axis_dz_tvalid   = dz_output_valid;

    assign m_axis_mus_ambig     = mus_ambiguities;
    assign m_axis_mus_ambig_cnt = mus_ambig_count;
    assign m_axis_mus_tvalid    = mus_ambig_valid;

    //=========================================================================
    // Interrupt generation
    //=========================================================================
    assign irq_dz_done  = dz_output_valid;
    assign irq_mus_done = mus_ambig_valid;

endmodule
