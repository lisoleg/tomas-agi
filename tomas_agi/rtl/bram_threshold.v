//=============================================================================
// bram_threshold.v — BRAM-based Threshold Storage for T-Shield PL
// T-Shield Cognitive Safety Layer — PL (Programmable Logic)
// Target: Xilinx Zynq-7000 (Artix-7 FPGA)
//
// Dual-port BRAM storing per-element Dead-Zero thresholds and warning ratios.
// Port A: PS write (via AXI) — for runtime threshold updates
// Port B: PL read (combinational) — for Dead-Zero comparator array
//
// Storage layout:
//   Address 0..NUM_ELEMENTS-1:  Dead-Zero thresholds (Q8.8)
//   Address NUM_ELEMENTS..2*N-1: Warning thresholds (Q8.8)
//
// Total: 2 * NUM_ELEMENTS * 32 bits = 256 bytes (for N=32)
//=============================================================================

`timescale 1ns / 1ps

module bram_threshold #(
    parameter NUM_ELEMENTS  = 32,
    parameter ADDR_WIDTH    = 6,       // ceil(log2(2 * NUM_ELEMENTS))
    parameter DATA_WIDTH    = 32       // Q8.8 fixed-point
) (
    input  wire                              clk,

    // Port A: PS write interface (synchronous write)
    input  wire                              ps_write_en,
    input  wire [ADDR_WIDTH-1:0]             ps_write_addr,
    input  wire [DATA_WIDTH-1:0]             ps_write_data,

    // Port B: PL read interface (asynchronous read for comparator)
    input  wire [ADDR_WIDTH-1:0]             pl_read_addr,
    output wire [DATA_WIDTH-1:0]             pl_read_data,

    // Bulk load interface (for initialization)
    input  wire                              bulk_load_en,
    input  wire [ADDR_WIDTH-1:0]             bulk_load_addr,
    input  wire [DATA_WIDTH-1:0]             bulk_load_data,
    output wire                              bulk_load_done
);

    //=========================================================================
    // BRAM storage (2 * NUM_ELEMENTS entries)
    //=========================================================================
    (* RAM_STYLE = "BLOCK" *)
    reg [DATA_WIDTH-1:0] bram_mem [0:2*NUM_ELEMENTS-1];

    // Port A: Synchronous write
    always @(posedge clk) begin
        if (ps_write_en) begin
            bram_mem[ps_write_addr] <= ps_write_data;
        end
        if (bulk_load_en) begin
            bram_mem[bulk_load_addr] <= bulk_load_data;
        end
    end

    // Port B: Asynchronous read (combinational — for parallel comparator)
    assign pl_read_data = bram_mem[pl_read_addr];

    // Bulk load done signal
    assign bulk_load_done = bulk_load_en && (bulk_load_addr == 2 * NUM_ELEMENTS - 1);

    //=========================================================================
    // Initialization (simulation only — replaced by bulk_load in synthesis)
    //=========================================================================
    integer init_i;
    initial begin
        for (init_i = 0; init_i < 2 * NUM_ELEMENTS; init_i = init_i + 1) begin
            if (init_i < NUM_ELEMENTS)
                bram_mem[init_i] = 32'h0000_0001;   // Default DZ threshold: 1/256
            else
                bram_mem[init_i] = 32'h0000_0019;   // Default warning threshold: 25/256
        end
    end

endmodule
