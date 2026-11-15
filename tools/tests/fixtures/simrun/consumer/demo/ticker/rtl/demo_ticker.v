// SPDX-License-Identifier: BSD-3-Clause
// SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
// Test fixture of simrun: a block of another repo around acme_counter (a dependency), counting
// every other clk.
module demo_ticker (
    input clk,
    input reset,
    output [7:0] q
);
    reg ce = 1'b0;
    always @(posedge clk)
        ce <= reset ? 1'b0 : ~ce;
    acme_counter #(.WIDTH(8)) counter (.clk(clk), .reset(reset), .ce(ce), .q(q));
endmodule
