//=============================================================================
// tb_deadzone_comp_array.v — Testbench for Dead-Zone Comparator Array
// T-Shield Cognitive Safety Layer
//=============================================================================

`timescale 1ns / 1ps

module tb_deadzone_comp_array;

    // Parameters
    parameter NUM_ELEMENTS = 8;  // Small for simulation
    parameter DATA_WIDTH   = 32;
    parameter LEVEL_WIDTH  = 2;
    parameter THRESH_WIDTH = 32;

    // Signals
    reg                              clk;
    reg                              rst_n;
    reg                              dz_start;
    reg  [THRESH_WIDTH-1:0]          dz_threshold;
    reg  [THRESH_WIDTH-1:0]          warn_threshold;
    reg  [DATA_WIDTH-1:0]            input_data [0:NUM_ELEMENTS-1];
    reg                              input_valid;
    wire [LEVEL_WIDTH-1:0]           output_levels [0:NUM_ELEMENTS-1];
    wire                             output_valid;
    wire [$clog2(NUM_ELEMENTS)-1:0]  dead_count;
    wire [$clog2(NUM_ELEMENTS)-1:0]  warning_count;

    // DUT
    deadzone_comp_array #(
        .NUM_ELEMENTS   (NUM_ELEMENTS),
        .DATA_WIDTH     (DATA_WIDTH),
        .LEVEL_WIDTH    (LEVEL_WIDTH),
        .THRESH_WIDTH   (THRESH_WIDTH)
    ) uut (
        .clk            (clk),
        .rst_n          (rst_n),
        .dz_start       (dz_start),
        .dz_threshold   (dz_threshold),
        .warn_threshold (warn_threshold),
        .input_data     (input_data),
        .input_valid    (input_valid),
        .output_levels  (output_levels),
        .output_valid   (output_valid),
        .dead_count     (dead_count),
        .warning_count  (warning_count)
    );

    // Clock generation: 100 MHz (10ns period)
    initial clk = 0;
    always #5 clk = ~clk;

    // Test counters
    integer pass_count;
    integer fail_count;

    // Level names for display
    reg [15:0] level_name;
    always @(*) begin
        case (1'b1)
            default: level_name = "??";
        endcase
    end

    // Test stimulus
    initial begin
        pass_count = 0;
        fail_count = 0;

        // Initialize
        rst_n = 0;
        dz_start = 0;
        input_valid = 0;
        dz_threshold = 32'h0000_0100;   // Q8.8: 1.0
        warn_threshold = 32'h0000_0019; // Q8.8: ~0.1

        // Initialize input data
        integer i;
        for (i = 0; i < NUM_ELEMENTS; i = i + 1)
            input_data[i] = 0;

        // Reset
        #20 rst_n = 1;
        #10;

        $display("=== Test 1: All SAFE values ===");
        for (i = 0; i < NUM_ELEMENTS; i = i + 1)
            input_data[i] = 32'h0000_0200;  // Q8.8: 2.0 (above threshold)
        input_valid = 1;
        dz_start = 1;
        #10 dz_start = 0;
        #20;
        if (dead_count == 0 && warning_count == 0) begin
            $display("  PASS: all SAFE (dead=%0d, warn=%0d)", dead_count, warning_count);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: expected 0 dead, 0 warn; got dead=%0d, warn=%0d", dead_count, warning_count);
            fail_count = fail_count + 1;
        end

        #20;
        $display("=== Test 2: All DEAD values ===");
        for (i = 0; i < NUM_ELEMENTS; i = i + 1)
            input_data[i] = 32'h0000_0001;  // Q8.8: ~0.004 (below warning threshold)
        input_valid = 1;
        dz_start = 1;
        #10 dz_start = 0;
        #20;
        if (dead_count == NUM_ELEMENTS) begin
            $display("  PASS: all DEAD (dead=%0d)", dead_count);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: expected %0d dead; got dead=%0d", NUM_ELEMENTS, dead_count);
            fail_count = fail_count + 1;
        end

        #20;
        $display("=== Test 3: Mixed values ===");
        input_data[0] = 32'h0000_0200;  // 2.0 → SAFE
        input_data[1] = 32'h0000_0080;  // 0.5 → WARNING (0.1 < 0.5 < 1.0)
        input_data[2] = 32'h0000_0001;  // ~0.004 → DEAD
        input_data[3] = 32'h0000_0100;  // 1.0 → SAFE (boundary)
        input_data[4] = 32'h0000_000A;  // ~0.04 → DEAD (below warning)
        input_data[5] = 32'h0000_0060;  // 0.375 → WARNING
        input_data[6] = 32'h0000_0300;  // 3.0 → SAFE
        input_data[7] = 32'h0000_0002;  // ~0.008 → DEAD
        input_valid = 1;
        dz_start = 1;
        #10 dz_start = 0;
        #20;
        if (dead_count == 3 && warning_count == 2) begin
            $display("  PASS: mixed (dead=%0d, warn=%0d)", dead_count, warning_count);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: expected 3 dead, 2 warn; got dead=%0d, warn=%0d", dead_count, warning_count);
            fail_count = fail_count + 1;
        end

        #20;
        $display("=== Test 4: Output levels match ===");
        if (output_levels[0] == 2'b00 && output_levels[2] == 2'b10 && output_levels[1] == 2'b01) begin
            $display("  PASS: output levels correct");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: output_levels[0]=%b [1]=%b [2]=%b", output_levels[0], output_levels[1], output_levels[2]);
            fail_count = fail_count + 1;
        end

        #20;
        $display("=== Test 5: Reset clears outputs ===");
        rst_n = 0;
        #10;
        if (dead_count == 0 && warning_count == 0 && output_valid == 0) begin
            $display("  PASS: reset clears outputs");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: reset did not clear outputs");
            fail_count = fail_count + 1;
        end

        // Summary
        $display("");
        $display("=============================");
        $display("  Dead-Zone Comparator Tests");
        $display("  PASSED: %0d", pass_count);
        $display("  FAILED: %0d", fail_count);
        $display("=============================");

        if (fail_count == 0)
            $display("  ALL TESTS PASSED!");
        else
            $display("  SOME TESTS FAILED!");

        #100 $finish;
    end

endmodule
