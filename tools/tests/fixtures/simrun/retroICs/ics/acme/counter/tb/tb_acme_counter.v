// SPDX-License-Identifier: BSD-3-Clause
// SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
// Test fixture of simrun: N clock enables of acme_ce_gen reach the counter; then the count holds
// while ce is low; the count goes to count.txt (for a golden compare). +inject_error prints an
// ERROR line and still PASS (the pass rule must fail it).
`timescale 1ns / 1ns
module tb_acme_counter;
    parameter N = 10;
    reg clk = 1'b0;
    reg reset = 1'b1;
    reg en = 1'b0;
    wire ce;
    wire [7:0] q;
    integer seen = 0;
    integer errors = 0;
    integer fd;
    reg [7:0] held;

    always #5 clk = ~clk;

    acme_ce_gen gen (.clk(clk), .en(en), .ce(ce));
    acme_counter #(.WIDTH(8)) dut (.clk(clk), .reset(reset), .ce(ce), .q(q));

    always @(posedge clk)
        if (!reset && ce)
            seen <= seen + 1;

    initial begin
        #100000;
        $display("FATAL: counter: timeout, %0d of %0d ce", seen, N);
        $finish;
    end

    initial begin
        $display("INFO: counter: N = %0d", N);
        if ($test$plusargs("inject_error"))
            $display("ERROR: counter: injected by +inject_error");
        repeat (3) @(posedge clk);
        @(negedge clk) reset = 1'b0;
        en = 1'b1;
        wait (seen == N);
        @(negedge clk) en = 1'b0;
        repeat (3) @(posedge clk);
        @(negedge clk);
        if (q !== N) begin
            $display("ERROR: counter: count %0d after %0d ce, expected %0d", q, seen, N);
            errors = errors + 1;
        end
        held = q;
        repeat (4) @(posedge clk);
        @(negedge clk);
        if (q !== held) begin
            $display("ERROR: counter: changed without ce: %0d, then %0d", held, q);
            errors = errors + 1;
        end
        fd = $fopen("count.txt", "wb");  // "wb": LF on every host
        $fwrite(fd, "%0d\n", q);
        $fclose(fd);
        if (errors == 0)
            $display("PASS: counter");
        $finish;
    end
endmodule
