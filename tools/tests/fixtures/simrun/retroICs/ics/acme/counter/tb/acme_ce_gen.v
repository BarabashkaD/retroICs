// SPDX-License-Identifier: BSD-3-Clause
// SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
// Test fixture of simrun: a clock enable on every other clk while en is high.
module acme_ce_gen (
    input clk,
    input en,
    output reg ce
);
    initial ce = 1'b0;
    always @(posedge clk)
        ce <= en ? ~ce : 1'b0;
endmodule
