//=============================================================================
// axi_lite_slave.v — AXI4-Lite Slave Interface for T-Shield PL
// T-Shield Cognitive Safety Layer — PS-PL Bridge
// Target: Xilinx Zynq-7000
//
// Register Map (32-bit aligned):
//   0x00: CTRL   — Control register [0]=dz_start, [1]=mus_start, [2]=reset
//   0x04: STATUS — Status register [0]=dz_done, [1]=mus_done, [2]=dz_busy, [3]=mus_busy
//   0x08: DZ_THRESH   — Dead-Zero threshold (Q8.8 fixed-point)
//   0x0C: WARN_THRESH — Warning threshold (Q8.8 fixed-point)
//   0x10: NUM_BOXES   — Number of detection boxes
//   0x14: NUM_ACTS    — Number of activation values
//   0x18: DZ_DEAD_CNT — Dead-Zero dead count (read-only)
//   0x1C: DZ_WARN_CNT — Dead-Zero warning count (read-only)
//   0x20: MUS_AMBIG_CNT — MUS ambiguity count (read-only)
//   0x24: IOTA_SCENE  — ℐ-scene value (Q8.8, read-only)
//   0x28: KSnap_CFG   — κ-Snap configuration [7:0]=max_config, [15:8]=strategy
//   0x2C: VERSION     — Hardware version (read-only, 0x00010000 = v1.0.0)
//=============================================================================

`timescale 1ns / 1ps

module axi_lite_slave #(
    parameter C_S_AXI_DATA_WIDTH = 32,
    parameter C_S_AXI_ADDR_WIDTH = 6      // 64 bytes = 16 registers
) (
    // Global signals
    input  wire                              clk,
    input  wire                              rst_n,

    // AXI4-Lite Slave Interface
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

    // Register outputs to internal logic
    output reg  [C_S_AXI_DATA_WIDTH-1:0]    reg_ctrl,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]    reg_dz_thresh,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]    reg_warn_thresh,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]    reg_num_boxes,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]    reg_num_acts,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]    reg_ksnap_cfg,

    // Register inputs from internal logic (read-only)
    input  wire [C_S_AXI_DATA_WIDTH-1:0]    reg_status,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]    reg_dz_dead_cnt,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]    reg_dz_warn_cnt,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]    reg_mus_ambig_cnt,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]    reg_iota_scene
);

    //=========================================================================
    // Register definitions
    //=========================================================================
    localparam ADDR_CTRL         = 6'h00;
    localparam ADDR_STATUS       = 6'h04;
    localparam ADDR_DZ_THRESH    = 6'h08;
    localparam ADDR_WARN_THRESH  = 6'h0C;
    localparam ADDR_NUM_BOXES    = 6'h10;
    localparam ADDR_NUM_ACTS     = 6'h14;
    localparam ADDR_DZ_DEAD_CNT  = 6'h18;
    localparam ADDR_DZ_WARN_CNT  = 6'h1C;
    localparam ADDR_MUS_AMBIG_CNT= 6'h20;
    localparam ADDR_IOTA_SCENE   = 6'h24;
    localparam ADDR_KSNAP_CFG    = 6'h28;
    localparam ADDR_VERSION      = 6'h2C;

    localparam HW_VERSION = 32'h0001_0000;  // v1.0.0

    //=========================================================================
    // AXI4-Lite Write Channel
    //=========================================================================
    reg [1:0] aw_state;
    reg [1:0] w_state;
    reg [1:0] b_state;

    // Write address channel
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            aw_state     <= 2'd0;
            s_axi_awready <= 1'b0;
        end else begin
            case (aw_state)
                2'd0: begin
                    s_axi_awready <= 1'b1;
                    if (s_axi_awvalid && s_axi_awready)
                        aw_state <= 2'd1;
                end
                2'd1: begin
                    s_axi_awready <= 1'b0;
                    aw_state <= 2'd0;
                end
                default: aw_state <= 2'd0;
            endcase
        end
    end

    // Write data channel
    reg [C_S_AXI_ADDR_WIDTH-1:0] write_addr;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            w_state       <= 2'd0;
            s_axi_wready <= 1'b0;
            write_addr   <= 0;
        end else begin
            case (w_state)
                2'd0: begin
                    s_axi_wready <= 1'b1;
                    if (s_axi_wvalid && s_axi_wready) begin
                        write_addr <= s_axi_awaddr;
                        s_axi_wready <= 1'b0;
                        w_state <= 2'd1;
                    end
                end
                2'd1: begin
                    w_state <= 2'd0;
                end
                default: w_state <= 2'd0;
            endcase
        end
    end

    // Register write logic
    wire write_enable = s_axi_wvalid && s_axi_awvalid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_ctrl        <= 0;
            reg_dz_thresh   <= 32'h0000_0001;  // Default: 1/256
            reg_warn_thresh <= 32'h0000_0019;  // Default: 25/256
            reg_num_boxes   <= 32'h0000_0010;  // Default: 16
            reg_num_acts    <= 32'h0000_0020;  // Default: 32
            reg_ksnap_cfg   <= 32'h0000_0401;  // Default: 4 configs, strategy=1
        end else if (write_enable) begin
            case (write_addr[5:2])
                4'h0: reg_ctrl        <= s_axi_wdata;  // CTRL
                4'h2: reg_dz_thresh   <= s_axi_wdata;  // DZ_THRESH
                4'h3: reg_warn_thresh <= s_axi_wdata;  // WARN_THRESH
                4'h4: reg_num_boxes   <= s_axi_wdata;  // NUM_BOXES
                4'h5: reg_num_acts    <= s_axi_wdata;  // NUM_ACTS
                4'hA: reg_ksnap_cfg   <= s_axi_wdata;  // KSNAP_CFG
                default: ;  // Read-only registers: ignore writes
            endcase
        end
    end

    // Write response
    assign s_axi_bresp = 2'b00;  // OKAY
    assign s_axi_bvalid = (w_state == 2'd1);

    //=========================================================================
    // AXI4-Lite Read Channel
    //=========================================================================
    reg [1:0] ar_state;
    reg [1:0] r_state;
    reg [C_S_AXI_DATA_WIDTH-1:0] read_data;

    // Read address channel
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ar_state     <= 2'd0;
            s_axi_arready <= 1'b0;
        end else begin
            case (ar_state)
                2'd0: begin
                    s_axi_arready <= 1'b1;
                    if (s_axi_arvalid && s_axi_arready)
                        ar_state <= 2'd1;
                end
                2'd1: begin
                    s_axi_arready <= 1'b0;
                    ar_state <= 2'd0;
                end
                default: ar_state <= 2'd0;
            endcase
        end
    end

    reg [C_S_AXI_ADDR_WIDTH-1:0] read_addr;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_state       <= 2'd0;
            s_axi_rvalid <= 1'b0;
            read_addr     <= 0;
            read_data     <= 0;
        end else begin
            case (r_state)
                2'd0: begin
                    s_axi_rvalid <= 1'b0;
                    if (s_axi_arvalid && s_axi_arready) begin
                        read_addr <= s_axi_araddr;
                        r_state   <= 2'd1;
                    end
                end
                2'd1: begin
                    // Mux read data based on address
                    case (read_addr[5:2])
                        4'h0: read_data <= reg_ctrl;
                        4'h1: read_data <= reg_status;
                        4'h2: read_data <= reg_dz_thresh;
                        4'h3: read_data <= reg_warn_thresh;
                        4'h4: read_data <= reg_num_boxes;
                        4'h5: read_data <= reg_num_acts;
                        4'h6: read_data <= reg_dz_dead_cnt;
                        4'h7: read_data <= reg_dz_warn_cnt;
                        4'h8: read_data <= reg_mus_ambig_cnt;
                        4'h9: read_data <= reg_iota_scene;
                        4'hA: read_data <= reg_ksnap_cfg;
                        4'hB: read_data <= HW_VERSION;
                        default: read_data <= 32'hDEAD_BEEF;
                    endcase
                    s_axi_rvalid <= 1'b1;
                    r_state <= 2'd2;
                end
                2'd2: begin
                    if (s_axi_rready) begin
                        s_axi_rvalid <= 1'b0;
                        r_state <= 2'd0;
                    end
                end
                default: r_state <= 2'd0;
            endcase
        end
    end

    assign s_axi_rdata = read_data;
    assign s_axi_rresp = 2'b00;  // OKAY

endmodule
