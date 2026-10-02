# Chipalooza Harness Cocotb Verification — Slot 16

Date: 2026-10-01. Repository: `/home/arjun/eda/projects/ADC_IHP/SAR_ADC`. Harness clone:
`sg13cmos5l_ocd_chipalooza/`. No harness test or RTL file was modified.

## Environment
| Item | Value |
|---|---|
| Harness commit | `190683013a65077076b8ca54b4023d1d0d5e3e49` (`main`, up to date with `origin/main`, working tree clean before the run) |
| Harness submodules | Initialised with `git submodule update --init --recursive`; all three were uninitialised before:<br>`sg13cmos5l_ocd_ip__analog_switches` `f441f2a3`<br>`sg13cmos5l_ocd_ip__biasgen` `c9e4d5e6`<br>`sg13cmos5l_ocd_ip__por` `109a4f0d` |
| Simulator (official result) | **Icarus Verilog 13.0 (stable)**, built from tag `v13_0` into `~/eda/tools/iverilog-13`. gperf 3.1 was built into `~/eda/tools/gperf-3.1` for the build. No system packages changed. |
| Simulator (first run) | Icarus Verilog 12.0 (Ubuntu `12.0-2build2`, `/usr/bin`). 6 failures, explained below. |
| cocotb | 2.1.0, pinned by `verilog/dv/requirements.txt`, in the venv `verilog/dv/venv` (per `verilog/dv/README`) |
| Python | 3.12.3 |
| make | GNU Make 4.3 |
| PDK | `PDK_ROOT=/home/arjun/eda/pdks/IHP-Open-PDK` (IHP-Open-PDK `719b8fd6`), `PDK=ihp-sg13cmos5l`. The Makefile default `$(HOME)/gits` does not exist here. |
| Official command | `make sim` from the harness top level. This runs `make -C verilog/dv` with the venv on PATH; `SIM=icarus`, compile args `-g2012 -gno-specify`. |

## Official tests
Results are at Icarus 13.0. The full per-test list (100 tests, both simulators) is in `per_test_results.md`.

| Test module | Result | What it verifies | Slot-16 relevance |
|---|---|---|---|
| `test_spi.py` (6) | 6 PASS | SPI protocol and register file: ID registers, mask_rev, write/readback, auto-increment, CSB abort, NOP | Generic (A). This is the path used to configure slot 16. |
| `test_sram.py` (6) | 6 PASS | Pattern SRAM over SPI: read/write, auto-increment across 256, address carry, walking ones, non-destructive read, return to the register map | Generic (A) |
| `test_clocking.py` (5) | 5 PASS | SRAM clock-source exclusivity, sram_clk source following, sequencer command latching on SCK, loop mode, async digital reset of the sequencer | Generic (A) |
| `test_no_clock.py` (9) | 9 PASS | Operation with no chip clock: SPI, SRAM, input constants and pads, output routing, project selection and enables, analog biases; sequencer and pattern generator frozen | Generic (A). Uses slot 7. |
| `test_pattern.py` (9) | 9 PASS | Pattern generator modes 00/01/10/11, address walk, data lag, loop and single shot, timed mode | Generic (A) |
| `test_sequencer.py` (12) | 12 PASS | Sequencer reset defaults, constant 0/1, binary and Gray up/down, LFSR, single shot vs loop, strobe, prescaler, stop/reset, undefined mode | Generic (A). The sequencer is a START source for slot 16. |
| `test_router.py` (12) | 12 PASS | Digital crossbar: every project input from every pad, per-bit routing, constants, sequencer/SRAM codes, every output to every pad, contention, unrouted pads stay inputs, monitors | Generic (A). Exercised at `dbus_in`/`dbus_out`, without any slot. |
| `test_project_control.py` (12) | 12 PASS (6 FAIL with Icarus 12) | One-hot selection of all 18 slots, address 0 and > 18 select nothing, enables only on the selected slot, dig_in latch, gated project clock with no glitches, synchronised per-slot reset, dig_out daisy-chain continuity | (A) and (C). `test_select_is_one_hot` selects **slot 16** explicitly. The others select slots 4, 7, 10, 11, 13 and 15, and check slot 16 only as "unselected, must stay off". |
| `test_analog.py` (21) | 21 PASS | Power gates (3.3 V / 1.2 V), bias switches, voltgen, analog-bus enables one-hot and per line, shared pads to the selected slot only, diagnostic switches, bandgap trim curve | (A). Selects slots 1, 5, 7, 9 and 18. Slot 16 is checked only as "unselected, must see nothing". |
| `test_bias.py` (8) | 8 PASS | Bias generator at the documented settings: currents, range checks (including a deliberate mis-setting), disable, iDAC scaling, polarity through the switches, register readback | Generic (A) |

Classification:
- **A (generic harness infrastructure):** all 100 tests.
- **B (depends on a user project's behaviour):** none. Every slot wrapper is an empty template in the harness RTL, so no test can exercise a project.
- **C (anything specific to slot 16):** `test_project_control.test_select_is_one_hot` (slot 16 is one of the 18 addresses), plus the negative "unselected slots see nothing" checks, which read all 18 slot vectors.

## Summary
**Official regression, Icarus 13.0 (final):**
- Total: **100**
- Passed: **100**
- Failed: **0**
- Skipped: **0**
- Simulated time: 7.97 ms.
- Exit status 0.

The only WARNING line is the one the DV README says to expect: `bandgap bias out of range`, from
`test_bias_range_check_rejects_a_wrong_setting`, which mis-sets a trim on purpose.

**First run, Icarus 12.0 (`harness_cocotb_iverilog12.log`):** 100 total, **94 passed, 6 failed**, 0 skipped. The cause is the simulator
version (below).

**Local slot-16 smoke test, Icarus 13.0 (`test_slot16_smoke.py`, `slot16_smoke.log`):** **7/7 PASS**. This is not an official test.

## Slot-16 checks
- **SPI:** PASS (official `test_spi`; also every smoke test configures slot 16 over SPI). `proj_sel` reads back 16.
- **Project selection/control:** PASS.
  - Official `test_select_is_one_hot` covers address 16.
  - Smoke test: `user_ena`, `user_3v3_ena` and `user_1v2_ena` equal exactly bit 15 (slot 16).
  - Slot 16 receives `vdd_3v3` = 3.30 V and `vdd_1v2` = 1.20 V; the other 17 slots receive NaN (unpowered).
  - The harness `reset` (command 0x04) reaches only slot 16, synchronised. The ADC does not use it; RSTN comes from `dig_in[1]`.
- **Router:** PASS.
  - Official `test_router` covers the crossbar.
  - Smoke test, inputs: `dig_in[0]` (START) and `dig_in[1]` (RSTN) reach slot 16 from pads 0/1 in all four combinations, and from the
    SPI constants (START = 1, RSTN = 1 or 0).
  - Smoke test, outputs: a walking one on slot-16 `dig_out[0..11]` (C0..C9, busy, valid) appears on exactly pad j (`io_out`, `gpio_out`,
    with `io_oe` = 0xFFF), and in the SPI readback registers 0x38/0x39.
  - When the project is deselected, slot 16's outputs no longer reach the bus.
- **Sequencer:** PASS.
  - Official `test_sequencer`.
  - Smoke test: route code 0xF puts `seq_out[0]` on slot-16 `dig_in[0]` (START). The sequencer in constant-one mode drives START high;
    the stop command returns it to 0. This is the clock-synchronous START source that the ADC's FSM timing requires.
- **Clock:** PASS with Icarus 13.
  - Official `test_proj_clk_*`.
  - Smoke test: slot 16's gated clock (to the ADC CLK) follows `clk_in` on every edge, the other 17 stay low, and it stops after
    deselect.
- **Analog-bus switching infrastructure:** PASS.
  - Official `test_analog` covers the bus enables (one-hot and per line) and the pad-to-slot routing, on slots 1/5/9/18.
  - Smoke test: with pad 0 = 3.3 V and pad 1 = 1.65 V, and `analog_bus` = 0b0011, slot 16 receives `analog_bus0` = 3.30 V (vrefp) and
    `analog_bus1` = 1.65 V (vcm). `analog_bus2/3` read NaN, every other slot reads NaN, and disabling the bus disconnects it.
  - These are behavioural real-valued switch models: connectivity only, with no impedance.
- **Dedicated analog pads:** represented correctly in config and RTL, **NOT exercised** by any test.
  - `config.txt`: `s16_an[0]` and `s16_an[1]` are `sg13cmos5l_IOPadAnalog`, with core names `s16_an_0` and `s16_an_1`.
  - `verilog/gl/sg13cmos5l_padframe.v`: `pad_s16_an_0`/`_1` have `.pad(s16_an[n])` and `.padres(s16_an_n_esd)`.
  - `chipalooza_frame.v` passes `s16_an` and `s16_an_*_esd` straight to `slot16_wrapper`.
  - The DV README (model limitation 2) states that the dedicated per-slot analog pins are not modelled in the testbench.
- **Digital input/output paths:** PASS for the harness side (see Router). The slot-16 outputs were driven by a Python `Force` on the
  slot-16 control block's `proj_dig_out` input, because the official `slot16_wrapper.v` is an empty template. **This is a behavioural
  stub, not the ADC.**
- **Slot-16 configuration (`config.txt`):** PASS.
  - `s16_source: https://github.com/arjun2000ananth/SAR_ADC_IHP`
  - `slot_16: Yu, Ananth, & Olonande`
  - `s16_an[0..1]` analog pads
  - **`s16_version` is still `- -`** (no commit pinned yet).

No existing test conflicts with the slot-16 mapping:
- s16_an[0] → ainp, s16_an[1] → ainn
- analog_bus0 → vrefp, analog_bus1 → vcm
- clk → CLK
- dig_in[0] → START, dig_in[1] → RSTN
- C0..C9 → dig_out[0..9], busy → dig_out[10], valid → dig_out[11]

The official tests never drive slot 16's wrapper ports and assign no meaning to them.

## Failures / warnings
1. **Icarus 12.0: 6 FAIL in `test_project_control`.** Root cause: **simulator incompatibility** (environment), not a harness RTL failure
   and not specific to slot 16.
   - **Failing tests:** `test_dig_in_latch_is_transparent_then_holds`, `test_dig_in_latch_clears_when_deselected`,
     `test_only_the_selected_slot_sees_the_bus`, `test_proj_clk_runs_only_on_the_selected_slot`,
     `test_proj_clk_has_no_glitch_when_selection_changes`, `test_proj_clk_stops_cleanly_on_deselect`.
   - **Error, in every case:** `ValueError: Can't convert LogicArray to int: it contains non-0/1 values` on `user_dig_in` or `user_clk`.
   - **Mechanism:** the IHP PDK models for `sg13cmos5l_lgcp_1` (clock gate) and `sg13cmos5l_dlhrq_1` (input latch) drive their logic
     through `delayed_*` nets. Only the `$setuphold`/`$recrem` timing checks in their `specify` blocks drive those nets. Icarus 12.0 does
     not support that, and says so: 138 compile warnings `Timing checks are not supported and delayed signal "delayed_CLK" will not be
     driven`. The nets float to Z and the cell outputs become X.
   - **Not a PDK revision effect:** the earlier PDK stdcell revision `84040cf7` uses the same `delayed_*` structure.
   - **Diagnostic (`diag/diag_cells.py`, `diag/diag_cells.log`, read-only):** with slot 16 selected, the cells receive correct inputs
     (`CLK` = 1, `GATE` = select = 1, `D` = 1, `GATE` = dig_ena = 1, `RESET_B` = 1), while `delayed_*` = Z and `GCLK`/`Q` = X.
   - **Fix: environment only.** Icarus 13.0 makes delayed signals copies of the originals. An isolated two-cell test confirms
     `GCLK`/`Q` are correct with 13.0 and X with 12.0. The full regression then passes 100/100 with no source change.
   - **Note for Timothy:** the README's statement that `-gno-specify` loses nothing is only true with Icarus ≥ 13. The DV README and
     Makefile do not state a minimum Icarus version.
2. **Expected warning (both runs):** `WARNING: chipalooza_frame.bandgap ...: bandgap bias out of range`. This is documented in the DV
   README as deliberate.
3. **DV README partly out of date.** Its "NOT YET COVERED" section still lists the router and the sequencer/pattern modes as untested,
   but `test_router.py`, `test_sequencer.py` and `test_pattern.py` now cover them. Documentation only.
4. **Local smoke test, first attempt:** the final "deselect" check selected slot 1. Slot 1's empty template wrapper then put undriven
   (X) outputs on the bus, which is expected behaviour, not a harness fault. The check was corrected to select address 0 (no slot).

## What this DOES verify
At the RTL level (behavioural models for analog blocks, PDK cell models for the clock gate, latches and SRAM), the generic harness
infrastructure works:
- SPI register file, SRAM, router, sequencer, pattern generator;
- per-slot selection, gated clocks, input latch and output daisy chain;
- power gates, bias and analog-bus switch control, bandgap/voltgen/biasgen models.

For slot 16 specifically (local smoke test), the harness delivers:
- the slot clock;
- enable, power gates and reset;
- START/RSTN from pads, constants or the sequencer;
- vrefp/vcm through shared analog buses 0/1;

and it carries 12 output bits from slot 16 to the pads and SPI readback, all exactly on the agreed mapping.

## What this DOES NOT verify
- Nothing about the SAR ADC itself. The official `slot16_wrapper.v` is an empty template, and the smoke test uses a Python stand-in for
  the ADC outputs.
- Dedicated analog pads `s16_an[0]`/`[1]`: not modelled by the harness testbench.
- Analog accuracy of the shared buses. The switches are real-valued behavioural models with no on-resistance, bus capacitance or pad
  parasitics.
- Gate-level timing. All of this is RTL; per the DV README, there is no SDF/gate-level mode.
- The physical slot GDS: placement, pins, DRC and LVS.

These harness cocotb tests do **NOT** replace:
- transistor-level ADC simulation;
- PEX ADC verification;
- DRC;
- LVS;
- silicon characterisation.

## Reproduce
```
cd sg13cmos5l_ocd_chipalooza
git submodule update --init --recursive
(cd verilog/dv && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt)
export PDK_ROOT=$HOME/eda/pdks/IHP-Open-PDK PDK=ihp-sg13cmos5l
export PATH=$HOME/eda/tools/iverilog-13/bin:$PATH        # Icarus >= 13 required (see Failures 1)
make sim-clean && make sim                               # official regression

# local slot-16 smoke test:
cd verilog/dv && PATH=$HOME/eda/tools/iverilog-13/bin:$PWD/venv/bin:$PATH \
  PYTHONPATH=<repo>/chipalooza/slot_16/verification/harness_cocotb make COCOTB_TEST_MODULES=test_slot16_smoke
```

## Files (this directory)
- `harness_cocotb.log`: official regression, Icarus 13.0 (100/100)
- `harness_cocotb_iverilog12.log`: official regression, Icarus 12.0 (94/100)
- `per_test_results.md`: all 100 tests under both simulators
- `test_slot16_smoke.py` and `slot16_smoke.log`: local slot-16 connectivity smoke test (7/7)
- `diag/diag_cells.py` and `diag/diag_cells.log`: read-only cell diagnostic for the Icarus-12 failures
