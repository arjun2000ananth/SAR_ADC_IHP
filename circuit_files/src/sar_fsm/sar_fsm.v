`timescale 1ns/1ps

//-----------------------------------------------------------------------------
// Fully differential SAR controller.
//
// Evaluate-first monotonic switching:
//   - Decide MSB with all bottom plates at VCM.
//   - After each non-final decision, raise the lower side's capacitor.
//   - Final LSB decision does not trigger another DAC switch.
//
// Comparator polarity:
//   comp = 1 means vcp > vcn when INVERT_COMP = 0.
//
// Parameter limits for the counter widths used here:
//   1 <= N <= 16
//   1 <= SAMPLE_CYCLES <= 256
//   1 <= DAC_SETTLE_CYCLES <= 256
//
// Acquisition:
//   sample rises on the edge accepting START.
//   sample falls exactly SAMPLE_CYCLES clock periods later.
//-----------------------------------------------------------------------------
module sar_logic #(
    parameter integer N                 = 10,
    parameter integer SAMPLE_CYCLES     = 8,
    parameter integer DAC_SETTLE_CYCLES = 3,
    parameter         INVERT_COMP       = 1'b0
)(
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire         comp,

    output reg          sample,
    output reg          comp_clk,
    output reg          busy,
    output reg          valid,

    output reg  [N-1:0]  bp,
    output reg  [N-1:0]  bn,
    output reg  [N-1:0]  code
);

    wire cmp_p_gt_n = INVERT_COMP ? ~comp : comp;

    localparam [2:0]
        S_IDLE    = 3'd0,
        S_SAMPLE  = 3'd1,
        S_SETTLE  = 3'd2,
        S_COMPARE = 3'd3,
        S_DECIDE  = 3'd4,
        S_DONE    = 3'd5;

    localparam [3:0] LAST_BIT = N - 1;

    reg [2:0] state;
    reg [3:0] bit_idx;
    reg [7:0] count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= S_IDLE;
            sample   <= 1'b0;
            comp_clk <= 1'b0;
            busy     <= 1'b0;
            valid    <= 1'b0;

            bp       <= {N{1'b0}};
            bn       <= {N{1'b0}};
            code     <= {N{1'b0}};

            bit_idx  <= LAST_BIT;
            count    <= 8'd0;
        end else begin
            // Default: comparator reset and VALID deasserted.
            comp_clk <= 1'b0;
            valid    <= 1'b0;

            case (state)

                S_IDLE: begin
                    sample <= 1'b0;
                    busy   <= 1'b0;

                    if (start) begin
                        busy    <= 1'b1;

                        // Begin acquisition immediately.
                        sample  <= 1'b1;

                        bp      <= {N{1'b0}};
                        bn      <= {N{1'b0}};
                        code    <= {N{1'b0}};

                        bit_idx <= LAST_BIT;
                        count   <= 8'd0;
                        state   <= S_SAMPLE;
                    end
                end

                // Acquire input on top plates.
                // Keep all bottom plates at VCM.
                S_SAMPLE: begin
                    bp <= {N{1'b0}};
                    bn <= {N{1'b0}};

                    if (count == SAMPLE_CYCLES - 1) begin
                        sample <= 1'b0;
                        count  <= 8'd0;
                        state  <= S_SETTLE;
                    end else begin
                        sample <= 1'b1;
                        count  <= count + 1'b1;
                    end
                end

                // Allow sampling-edge or DAC-switch transients to settle.
                S_SETTLE: begin
                    if (count == DAC_SETTLE_CYCLES - 1) begin
                        count <= 8'd0;
                        state <= S_COMPARE;
                    end else begin
                        count <= count + 1'b1;
                    end
                end

                // Enable comparator for one clock period.
                S_COMPARE: begin
                    comp_clk <= 1'b1;
                    state    <= S_DECIDE;
                end

                // Capture comparator result on the following clock edge.
                S_DECIDE: begin
                    code[bit_idx] <= cmp_p_gt_n;

                    if (bit_idx != 4'd0) begin
                        // Raise the lower side's capacitor bottom plate.
                        if (cmp_p_gt_n)
                            bn[bit_idx] <= 1'b1;
                        else
                            bp[bit_idx] <= 1'b1;

                        bit_idx <= bit_idx - 1'b1;
                        count   <= 8'd0;
                        state   <= S_SETTLE;
                    end else begin
                        // Final LSB: decision only.
                        state <= S_DONE;
                    end
                end

                S_DONE: begin
                    valid <= 1'b1;
                    busy  <= 1'b0;
                    state <= S_IDLE;
                end

                default: begin
                    state    <= S_IDLE;
                    sample   <= 1'b0;
                    comp_clk <= 1'b0;
                    busy     <= 1'b0;
                    valid    <= 1'b0;
                    bp       <= {N{1'b0}};
                    bn       <= {N{1'b0}};
                    code     <= {N{1'b0}};
                    bit_idx  <= LAST_BIT;
                    count    <= 8'd0;
                end

            endcase
        end
    end

endmodule
