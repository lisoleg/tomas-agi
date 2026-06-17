//=============================================================================
// deadzone_comp_array.v — Dead-Zero Comparator Array
// T-Shield Cognitive Safety Layer — PL (Programmable Logic) Accelerator
// Target: Xilinx Zynq-7000 (Artix-7 FPGA)
//
// Compares 32 activation values against Dead-Zero threshold in parallel.
// Classifies each value as:
//   2'b00 = SAFE    (>= epsilon)
//   2'b01 = WARNING (epsilon * warning_ratio <= val < epsilon)
//   2'b10 = DEAD    (< epsilon * warning_ratio)
//
// Latency: 1 clock cycle (combinational + registered)
// Throughput: 32 comparisons per cycle @ 100 MHz
//=============================================================================

`timescale 1ns / 1ps

module deadzone_comp_array #(
    parameter NUM_ELEMENTS    = 32,
    parameter DATA_WIDTH      = 32,
    parameter LEVEL_WIDTH     = 2,
    parameter THRESH_WIDTH    = 32,
    // Fixed-point Q8.8: threshold values as parameters
    parameter [THRESH_WIDTH-1:0] DZ_THRESH_DEFAULT  = 32'h00000001,   // 1/256 in Q8.8
    parameter [THRESH_WIDTH-1:0] WARNING_RATIO       = 32'h00000019    // 25/256 = ~0.1 in Q8.8
) (
    input  wire                              clk,
    input  wire                              rst_n,

    // Control interface
    input  wire                              dz_start,       // Start comparison
    input  wire [THRESH_WIDTH-1:0]           dz_threshold,   // Dead-Zero threshold (Q8.8)
    input  wire [THRESH_WIDTH-1:0]           warn_threshold,  // Warning threshold = dz_thresh * ratio (pre-computed by PS)

    // Input data bus: 32 activation values
    input  wire [DATA_WIDTH-1:0]             input_data [0:NUM_ELEMENTS-1],
    input  wire                              input_valid,

    // Output result: 2-bit level per element
    output reg  [LEVEL_WIDTH-1:0]            output_levels [0:NUM_ELEMENTS-1],
    output reg                               output_valid,
    output reg  [$clog2(NUM_ELEMENTS)-1:0]   dead_count,     // Number of DEAD elements
    output reg  [$clog2(NUM_ELEMENTS)-1:0]   warning_count   // Number of WARNING elements
);

    // Internal registers for registered outputs
    reg  [LEVEL_WIDTH-1:0] level_reg [0:NUM_ELEMENTS-1];
    reg  [$clog2(NUM_ELEMENTS)-1:0] dead_cnt_reg;
    reg  [$clog2(NUM_ELEMENTS)-1:0] warn_cnt_reg;

    // Combinational parallel comparison
    integer i;

    always @* begin
        dead_cnt_reg   = 0;
        warn_cnt_reg   = 0;

        if (dz_start && input_valid) begin
            for (i = 0; i < NUM_ELEMENTS; i = i + 1) begin
                if (input_data[i] < warn_threshold) begin
                    // Below warning threshold → DEAD
                    level_reg[i] = 2'b10;
                    dead_cnt_reg = dead_cnt_reg + 1;
                end
                else if (input_data[i] < dz_threshold) begin
                    // Between warning and dead → WARNING
                    level_reg[i] = 2'b01;
                    warn_cnt_reg = warn_cnt_reg + 1;
                end
                else begin
                    // Above threshold → SAFE
                    level_reg[i] = 2'b00;
                end
            end
        end
        else begin
            for (i = 0; i < NUM_ELEMENTS; i = i + 1) begin
                level_reg[i] = 2'b00;
            end
        end
    end

    // Register output stage (1-cycle pipeline)
    integer j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            output_valid <= 1'b0;
            dead_count   <= 0;
            warning_count <= 0;
            for (j = 0; j < NUM_ELEMENTS; j = j + 1) begin
                output_levels[j] <= 2'b00;
            end
        end
        else begin
            output_valid <= dz_start && input_valid;
            dead_count   <= dead_cnt_reg;
            warning_count <= warn_cnt_reg;
            for (j = 0; j < NUM_ELEMENTS; j = j + 1) begin
                output_levels[j] <= level_reg[j];
            end
        end
    end

`ifdef FORMAL
    // Formal verification assertions
    always @(posedge clk) begin
        if (output_valid) begin
            // Assert: dead_count <= NUM_ELEMENTS
            assert(dead_count <= NUM_ELEMENTS);
            // Assert: dead_count + warning_count <= NUM_ELEMENTS
            assert(dead_count + warning_count <= NUM_ELEMENTS);
        end
    end
`endif

endmodule
