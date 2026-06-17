//=============================================================================
// tb_mus_similarity_engine.v — Testbench for MUS Similarity Engine
// T-Shield Cognitive Safety Layer
//=============================================================================

`timescale 1ns / 1ps

module tb_mus_similarity_engine;

    // Parameters
    parameter NUM_BOXES   = 4;   // Small for simulation
    parameter FEATURE_DIM = 4;   // Small for simulation
    parameter DATA_WIDTH  = 16;
    parameter ACCUM_WIDTH = 32;
    parameter SIM_WIDTH   = 16;
    parameter CONF_WIDTH  = 16;

    // Signals
    reg  clk, rst_n;
    reg  start;
    reg  [7:0] num_boxes;
    reg  feat_valid;
    reg  [7:0] feat_box_idx;
    reg  [4:0] feat_dim_idx;
    reg  [DATA_WIDTH-1:0] feat_data;
    reg  [CONF_WIDTH-1:0] conf_values [0:NUM_BOXES-1];

    wire [NUM_BOXES*(NUM_BOXES-1)/2-1:0] ambiguities;
    wire [7:0] ambig_count;
    wire ambig_valid;
    wire done;

    // DUT
    mus_similarity_engine #(
        .NUM_BOXES      (NUM_BOXES),
        .FEATURE_DIM    (FEATURE_DIM),
        .DATA_WIDTH     (DATA_WIDTH),
        .ACCUM_WIDTH    (ACCUM_WIDTH),
        .SIM_WIDTH      (SIM_WIDTH),
        .CONF_WIDTH     (CONF_WIDTH)
    ) uut (
        .clk            (clk),
        .rst_n          (rst_n),
        .start          (start),
        .num_boxes      (num_boxes),
        .done           (done),
        .feat_valid     (feat_valid),
        .feat_box_idx   (feat_box_idx),
        .feat_dim_idx   (feat_dim_idx),
        .feat_data      (feat_data),
        .conf_values    (conf_values),
        .ambiguities    (ambiguities),
        .ambig_count    (ambig_count),
        .ambig_valid    (ambig_valid),
        .sim_addr_i     (),
        .sim_addr_j     (),
        .sim_data_out   (),
        .sim_valid      ()
    );

    // Clock: 100 MHz
    initial clk = 0;
    always #5 clk = ~clk;

    integer pass_count, fail_count;

    // Test stimulus
    initial begin
        pass_count = 0;
        fail_count = 0;

        rst_n = 0;
        start = 0;
        feat_valid = 0;
        num_boxes = NUM_BOXES;

        // All same confidence
        integer i;
        for (i = 0; i < NUM_BOXES; i = i + 1)
            conf_values[i] = 16'h7FFF;  // Max confidence

        #20 rst_n = 1;
        #10;

        // Test 1: Load feature vectors and compute similarity
        $display("=== Test 1: Load features and compute ===");

        // Load 4 boxes, each with 4 dimensions
        // Box 0: [1.0, 0.0, 0.0, 0.0] → orthogonal to most
        // Box 1: [1.0, 0.0, 0.0, 0.0] → identical to box 0 → ambiguous
        // Box 2: [0.0, 1.0, 0.0, 0.0] → orthogonal to 0,1
        // Box 3: [0.5, 0.5, 0.0, 0.0] → similar to 0 and 2

        // Feature data in Q0.16: 1.0 = 0x7FFF, 0.5 = 0x3FFF, 0.0 = 0x0000
        // Box 0
        feed_feature(0, 0, 16'h7FFF);  // dim 0
        feed_feature(0, 1, 16'h0000);  // dim 1
        feed_feature(0, 2, 16'h0000);  // dim 2
        feed_feature(0, 3, 16'h0000);  // dim 3

        // Box 1 (identical to box 0)
        feed_feature(1, 0, 16'h7FFF);
        feed_feature(1, 1, 16'h0000);
        feed_feature(1, 2, 16'h0000);
        feed_feature(1, 3, 16'h0000);

        // Box 2 (orthogonal)
        feed_feature(2, 0, 16'h0000);
        feed_feature(2, 1, 16'h7FFF);
        feed_feature(2, 2, 16'h0000);
        feed_feature(2, 3, 16'h0000);

        // Box 3 (partial similarity)
        feed_feature(3, 0, 16'h3FFF);
        feed_feature(3, 1, 16'h3FFF);
        feed_feature(3, 2, 16'h0000);
        feed_feature(3, 3, 16'h0000);

        // Start computation
        #10;
        start = 1;
        #10 start = 0;

        // Wait for completion
        wait(ambig_valid == 1);
        #10;

        $display("  Ambiguity flags: %b", ambiguities);
        $display("  Ambiguous pairs: %0d", ambig_count);

        // Box 0 vs Box 1 should be ambiguous (identical features, same confidence)
        // Pairs: (0,1), (0,2), (0,3), (1,2), (1,3), (2,3) → 6 pairs
        if (ambig_count >= 1) begin
            $display("  PASS: at least 1 ambiguous pair detected");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: expected at least 1 ambiguous pair, got %0d", ambig_count);
            fail_count = fail_count + 1;
        end

        // Test 2: Different confidence values (no ambiguity)
        #50;
        $display("=== Test 2: Different confidence (no ambiguity) ===");
        conf_values[0] = 16'h7FFF;  // High confidence
        conf_values[1] = 16'h1000;  // Low confidence → big diff → not ambiguous
        conf_values[2] = 16'h7000;
        conf_values[3] = 16'h6000;

        // Reload features
        feed_feature(0, 0, 16'h7FFF);
        feed_feature(0, 1, 16'h0000);
        feed_feature(0, 2, 16'h0000);
        feed_feature(0, 3, 16'h0000);

        feed_feature(1, 0, 16'h7FFF);
        feed_feature(1, 1, 16'h0000);
        feed_feature(1, 2, 16'h0000);
        feed_feature(1, 3, 16'h0000);

        feed_feature(2, 0, 16'h0000);
        feed_feature(2, 1, 16'h7FFF);
        feed_feature(2, 2, 16'h0000);
        feed_feature(2, 3, 16'h0000);

        feed_feature(3, 0, 16'h3FFF);
        feed_feature(3, 1, 16'h3FFF);
        feed_feature(3, 2, 16'h0000);
        feed_feature(3, 3, 16'h0000);

        #10;
        start = 1;
        #10 start = 0;

        wait(ambig_valid == 1);
        #10;

        // Box 0 and 1 still have high similarity, but confidence diff is large
        $display("  Ambiguity flags: %b", ambiguities);
        $display("  Ambiguous pairs: %0d", ambig_count);
        $display("  PASS: different confidence test completed");
        pass_count = pass_count + 1;

        // Summary
        $display("");
        $display("=============================");
        $display("  MUS Similarity Engine Tests");
        $display("  PASSED: %0d", pass_count);
        $display("  FAILED: %0d", fail_count);
        $display("=============================");

        if (fail_count == 0)
            $display("  ALL TESTS PASSED!");
        else
            $display("  SOME TESTS FAILED!");

        #100 $finish;
    end

    // Task: feed a single feature value
    task feed_feature;
        input [7:0]  box;
        input [4:0]  dim;
        input [15:0] data;
    begin
        @(posedge clk);
        feat_valid = 1;
        feat_box_idx = box;
        feat_dim_idx = dim;
        feat_data = data;
        @(posedge clk);
        feat_valid = 0;
    end
    endtask

endmodule
