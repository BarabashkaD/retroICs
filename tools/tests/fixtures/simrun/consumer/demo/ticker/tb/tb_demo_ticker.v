// SPDX-License-Identifier: BSD-3-Clause
// SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
// Test fixture of simrun: 20 clk after the reset give a count of 10.
`timescale 1ns / 1ns
module tb_demo_ticker;
    reg clk = 1'b0;
    reg reset = 1'b1;
    wire [7:0] q;

    always #5 clk = ~clk;

    demo_ticker dut (.clk(clk), .reset(reset), .q(q));

    initial begin
        repeat (3) @(posedge clk);
        @(negedge clk) reset = 1'b0;
        repeat (20) @(posedge clk);
        @(negedge clk);
        if (q !== 8'd10)
            $display("ERROR: ticker: count %0d after 20 clocks, expected 10", q);
        else
            $display("PASS: ticker");
        $finish;
    end
endmodule
