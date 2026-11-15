// SPDX-License-Identifier: BSD-3-Clause
// SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
// Test fixture of simrun: a counter with a clock enable and a synchronous reset.
module acme_counter #(parameter WIDTH = 8) (
    input clk,
    input reset,
    input ce,
    output reg [WIDTH-1:0] q
);
    always @(posedge clk)
        if (reset)
            q <= {WIDTH{1'b0}};
        else if (ce)
            q <= q + 1'b1;
endmodule
