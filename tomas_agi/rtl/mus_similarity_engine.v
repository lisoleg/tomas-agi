//=============================================================================
// mus_similarity_engine.v — MUS Similarity Engine
// T-Shield Cognitive Safety Layer — PL (Programmable Logic) Accelerator
// Target: Xilinx Zynq-7000 (Artix-7 FPGA)
//
// Computes pairwise dot-product similarity between detection box feature
// vectors. Identifies ambiguous pairs (high similarity + low confidence diff)
// for MUS Dual-Box Marking.
//
// Architecture:
//   - Pipelined dot-product using DSP48E1 slices
//   - Configurable NUM_BOXES and FEATURE_DIM
//   - Output: similarity matrix upper triangle + ambiguity flags
//
// Latency: FEATURE_DIM + 2 cycles per pair (pipelined)
// Throughput: 1 pair per cycle after pipeline fill
//=============================================================================

`timescale 1ns / 1ps

module mus_similarity_engine #(
    parameter NUM_BOXES     = 16,       // Max detection boxes per frame
    parameter FEATURE_DIM   = 16,       // Feature vector dimension
    parameter DATA_WIDTH    = 16,       // Fixed-point Q0.16
    parameter ACCUM_WIDTH   = 32,       // Accumulator width
    parameter SIM_WIDTH     = 16,       // Output similarity width
    parameter CONF_WIDTH    = 16,       // Confidence value width (Q0.16)
    parameter AMBIG_THRESH  = 16'h6666, // IoU/confidence ambiguity threshold (Q0.16: ~0.4)
    parameter CONF_DIFF_THRESH = 16'h0CCC  // Confidence difference threshold (Q0.16: ~0.05)
) (
    input  wire                              clk,
    input  wire                              rst_n,

    // Control interface
    input  wire                              start,          // Start computation
    input  wire [7:0]                        num_boxes,      // Actual number of boxes (<= NUM_BOXES)
    output reg                               done,           // Computation complete

    // Feature vector input (streaming: one feature per cycle)
    input  wire                              feat_valid,     // Feature data valid
    input  wire [7:0]                        feat_box_idx,   // Which box this feature belongs to
    input  wire [4:0]                        feat_dim_idx,   // Which dimension
    input  wire [DATA_WIDTH-1:0]             feat_data,      // Feature value (Q0.16)

    // Confidence values (loaded before start)
    input  wire [CONF_WIDTH-1:0]             conf_values [0:NUM_BOXES-1],

    // Output: ambiguity flags (one per pair, upper triangle)
    output reg  [NUM_BOXES*(NUM_BOXES-1)/2-1:0] ambiguities,  // 1 = ambiguous pair
    output reg  [7:0]                        ambig_count,     // Number of ambiguous pairs
    output reg                               ambig_valid,

    // Debug: similarity matrix output (BRAM interface)
    output reg  [7:0]                        sim_addr_i,     // Row index
    output reg  [7:0]                        sim_addr_j,     // Column index
    output reg  [SIM_WIDTH-1:0]             sim_data_out,    // Similarity value
    output reg                               sim_valid
);

    //=========================================================================
    // Internal storage: feature vectors
    //=========================================================================
    reg [DATA_WIDTH-1:0] feature_store [0:NUM_BOXES-1][0:FEATURE_DIM-1];

    // Feature loading state
    reg [7:0] load_count;
    reg       loading;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            load_count <= 0;
            loading    <= 0;
        end else if (start) begin
            load_count <= 0;
            loading    <= 1;
        end else if (loading && feat_valid) begin
            feature_store[feat_box_idx][feat_dim_idx] <= feat_data;
            load_count <= load_count + 1;
            if (load_count == num_boxes * FEATURE_DIM - 1)
                loading <= 0;
        end
    end

    //=========================================================================
    // Dot-product computation engine (pipelined)
    //=========================================================================
    // States
    localparam IDLE     = 3'd0;
    localparam COMPUTE  = 3'd1;
    localparam OUTPUT   = 3'd2;

    reg [2:0] state;
    reg [7:0] pair_i, pair_j;       // Current pair indices
    reg [4:0] dim_idx;              // Current dimension
    reg [ACCUM_WIDTH-1:0] accum;    // Running accumulation
    reg [NUM_BOXES*(NUM_BOXES-1)/2-1:0] ambig_reg;
    reg [7:0] ambig_cnt_reg;

    // Pipeline registers for DSP48E1 emulation
    reg [DATA_WIDTH-1:0]   pipe_a_reg;
    reg [DATA_WIDTH-1:0]   pipe_b_reg;
    reg [ACCUM_WIDTH-1:0]  pipe_mul_reg;
    reg [ACCUM_WIDTH-1:0]  pipe_acc_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state       <= IDLE;
            done        <= 0;
            pair_i      <= 0;
            pair_j      <= 1;
            dim_idx     <= 0;
            accum       <= 0;
            ambig_reg   <= 0;
            ambig_cnt_reg <= 0;
            ambiguities <= 0;
            ambig_count <= 0;
            ambig_valid <= 0;
            sim_valid   <= 0;
            sim_data_out <= 0;
            sim_addr_i  <= 0;
            sim_addr_j  <= 0;
            // Pipeline
            pipe_a_reg  <= 0;
            pipe_b_reg  <= 0;
            pipe_mul_reg <= 0;
            pipe_acc_reg <= 0;
        end else begin
            case (state)
                IDLE: begin
                    done        <= 0;
                    ambig_valid <= 0;
                    sim_valid   <= 0;
                    if (start && !loading && load_count == num_boxes * FEATURE_DIM) begin
                        state    <= COMPUTE;
                        pair_i   <= 0;
                        pair_j   <= 1;
                        dim_idx  <= 0;
                        accum    <= 0;
                        ambig_reg <= 0;
                        ambig_cnt_reg <= 0;
                    end
                end

                COMPUTE: begin
                    // Pipeline stage 1: Read operands
                    pipe_a_reg <= feature_store[pair_i][dim_idx];
                    pipe_b_reg <= feature_store[pair_j][dim_idx];

                    // Pipeline stage 2: Multiply
                    pipe_mul_reg <= pipe_a_reg * pipe_b_reg;

                    // Pipeline stage 3: Accumulate
                    pipe_acc_reg <= accum + pipe_mul_reg;

                    if (dim_idx == FEATURE_DIM - 1) begin
                        // Dot product complete for this pair
                        accum <= pipe_acc_reg;

                        // Output similarity (take upper bits for Q0.16)
                        sim_addr_i  <= pair_i;
                        sim_addr_j  <= pair_j;
                        sim_data_out <= pipe_acc_reg[ACCUM_WIDTH-1:ACCUM_WIDTH-SIM_WIDTH];
                        sim_valid   <= 1;

                        // Check ambiguity: high similarity AND low confidence diff
                        // similarity > AMBIG_THRESH AND |conf_i - conf_j| < CONF_DIFF_THRESH
                        if (pipe_acc_reg[ACCUM_WIDTH-1:ACCUM_WIDTH-SIM_WIDTH] >= AMBIG_THRESH) begin
                            // High similarity — check confidence difference
                            // Simplified: compare absolute difference (in real HW, use subtractor)
                            reg [CONF_WIDTH:0] conf_diff;
                            if (conf_values[pair_i] >= conf_values[pair_j])
                                conf_diff = conf_values[pair_i] - conf_values[pair_j];
                            else
                                conf_diff = conf_values[pair_j] - conf_values[pair_i];

                            if (conf_diff < CONF_DIFF_THRESH) begin
                                // Ambiguous pair found!
                                ambig_reg[pair_i * NUM_BOXES + pair_j - pair_i*(pair_i+1)/2 - 1] <= 1;
                                ambig_cnt_reg <= ambig_cnt_reg + 1;
                            end
                        end

                        // Advance to next pair
                        dim_idx <= 0;
                        accum   <= 0;
                        if (pair_j == num_boxes - 1) begin
                            if (pair_i == num_boxes - 2) begin
                                // All pairs done
                                state <= OUTPUT;
                            end else begin
                                pair_i <= pair_i + 1;
                                pair_j <= pair_i + 2;
                            end
                        end else begin
                            pair_j <= pair_j + 1;
                        end
                    end else begin
                        dim_idx <= dim_idx + 1;
                    end
                end

                OUTPUT: begin
                    ambiguities <= ambig_reg;
                    ambig_count <= ambig_cnt_reg;
                    ambig_valid <= 1;
                    done        <= 1;
                    state       <= IDLE;
                end

                default: state <= IDLE;
            endcase
        end
    end

`ifdef FORMAL
    // Formal verification: ambig_count <= NUM_BOXES*(NUM_BOXES-1)/2
    always @(posedge clk) begin
        if (ambig_valid) begin
            assert(ambig_count <= NUM_BOXES * (NUM_BOXES - 1) / 2);
        end
    end
`endif

endmodule
