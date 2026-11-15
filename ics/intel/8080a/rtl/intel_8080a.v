// SPDX-License-Identifier: BSD-3-Clause
// SPDX-FileCopyrightText: 2026 Dmitry Veremeev (BarabashkaD), https://github.com/BarabashkaD
// intel_8080a: the family-wide name of the 8080A model. It reproduces the die-derived КР580ВМ80А
// model (rtl/upstream/k580vm80a.v, kept byte-identical; component.toml: reproduces = "k580vm80a"),
// with the same ports and no VARIANT (docs/conventions.md, "The 8080"). Hierarchical paths into the
// CPU go through the instance core (a TB's dut.cpu.core.t3). No `default_nettype or `timescale here,
// so the upstream file compiles as it did before the wrapper.
module intel_8080a(
    input  wire        pin_clk,
    input  wire        pin_f1,
    input  wire        pin_f2,
    input  wire        pin_reset,
    output wire [15:0] pin_a,
    output wire  [7:0] pin_dout,
    input  wire  [7:0] pin_din,
    output wire        pin_aena,
    output wire        pin_dena,
    input  wire        pin_hold,
    output wire        pin_hlda,
    input  wire        pin_ready,
    output wire        pin_wait,
    input  wire        pin_int,
    output wire        pin_inte,
    output wire        pin_sync,
    output wire        pin_dbin,
    output wire        pin_wr_n
);

k580vm80a core(.pin_clk(pin_clk), .pin_f1(pin_f1), .pin_f2(pin_f2), .pin_reset(pin_reset),
    .pin_a(pin_a), .pin_dout(pin_dout), .pin_din(pin_din), .pin_aena(pin_aena), .pin_dena(pin_dena),
    .pin_hold(pin_hold), .pin_hlda(pin_hlda), .pin_ready(pin_ready), .pin_wait(pin_wait),
    .pin_int(pin_int), .pin_inte(pin_inte), .pin_sync(pin_sync), .pin_dbin(pin_dbin),
    .pin_wr_n(pin_wr_n));

endmodule
