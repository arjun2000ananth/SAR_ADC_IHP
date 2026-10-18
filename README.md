# 10-Bit SAR ADC — IHP SG13CMOS5L

A fully differential 10-bit successive-approximation-register (SAR) ADC designed in the **IHP SG13CMOS5L** process for the **Chipalooza Challenge**.

The repository contains the transistor-level analog design, SAR control logic, block-level and top-level layout, post-layout verification, and the integration into **Chipalooza slot 16**.

The ADC targets approximately **1 MS/s** operation and uses separate **3.3 V analog/high-voltage** and **1.2 V digital/low-voltage** supply domains.

ADC block and slot-level sign-off have passed. Result plots are available in [`docs/`](docs/).

---

## Team

| Name | Role |
|---|---|
| Arjun Ananth | Lead Designer - Design & Layout |
| Man Yu | Verification |

---

## Overview

The ADC uses a fully differential charge-redistribution SAR architecture.

Main blocks:

- Differential input sampling network
- Fully differential 10-bit capacitive DAC
- Strong-arm dynamic comparator with latch
- 1.2 V ↔ 3.3 V level shifters
- SAR finite-state machine
- Digital conversion outputs and status signals

Block diagram:

![Block Diagram](docs/Block_Diagram.png)

---

## Architecture

The ADC consists of the following main blocks:

### Sampling Network

The differential input is sampled onto the CDAC before the SAR conversion begins.

### Capacitive DAC

A fully differential 10-bit capacitive DAC performs the successive-approximation charge redistribution. The CDAC uses a common-mode based differential switching scheme and is implemented using SG13CMOS5L MOM capacitors.

### Comparator

A strong-arm dynamic comparator performs the bit decisions during conversion.

### Level Shifters

The analog circuitry operates primarily from the 3.3 V domain while the SAR controller operates at 1.2 V. Level shifters provide the required voltage-domain crossings between the digital controller and the analog switching circuitry.

### SAR Controller

The SAR controller is implemented as a synthesized FSM operating in the 1.2 V domain.

It controls:

- Sampling
- Comparator timing
- CDAC bit decisions
- Conversion sequencing
- `busy`
- `valid`
- Final 10-bit output code

---

## Conversion Sequence

A conversion proceeds as follows:

1. The differential input is sampled onto the CDAC.
2. The sampling switches open.
3. The SAR controller applies the MSB trial decision.
4. The comparator resolves the differential DAC residue.
5. The decision is stored.
6. Steps 3–5 repeat for the remaining bits.
7. The final 10-bit result is presented on `C[9:0]`.
8. `valid` is asserted when the result is available.

`busy` indicates that a conversion is currently in progress.

At a 60 MHz conversion clock, the controller completes one conversion every 60 cycles (1 MS/s) in the functional simulation.

---

## Supply Domains

| Domain | Nominal Voltage | Usage |
|---|---:|---|
| `vddh` | 3.3 V | Analog / hv circuitry |
| `vddl` | 1.2 V | SAR FSM and lv digital circuitry |
| `vss` | 0 V | Common ground |

The nominal CDAC reference (`vrefp`) is 3.3 V, with `vcm` at 1.65 V. Both references are routed through shared analog buses in the harness.

---

## SAR ADC Interface

The reusable `sar_10_bit` ADC macro has the following interface.

### Analog and Supply Pins

| Signal | Direction | Description |
|---|---|---|
| `ainp` | Input | Positive differential analog input |
| `ainn` | Input | Negative differential analog input |
| `vrefp` | Input | CDAC reference voltage |
| `vcm` | Input | Common-mode voltage |
| `Voutn` | Output | Comparator/debug analog output |
| `vddh` | Supply | 3.3 V supply |
| `vddl` | Supply | 1.2 V supply |
| `vss` | Supply | Ground |

### Digital Control Pins

| Signal | Direction | Description |
|---|---|---|
| `CLK` | Input | SAR conversion clock |
| `START` | Input | Starts a conversion |
| `RSTN` | Input | Active-low reset |

### Digital Outputs

| Signal | Direction | Description |
|---|---|---|
| `C0`–`C9` | Output | 10-bit conversion result |
| `busy` | Output | Conversion in progress |
| `valid` | Output | Conversion result valid |

---

# Chipalooza Integration

This project is assigned to **slot 16** of the IHP SG13CMOS5L Chipalooza test chip. The reusable ADC and the Chipalooza implementation are kept separate.

The harness integration expects its slot GDS at:

```text
final/gds/slot_16.gds
```

The `sar_10_bit` cell remains the reusable ADC macro and can be integrated independently into other designs.

---

## Slot-16 Signal Mapping

### Analog Inputs and References

| Chipalooza Signal | ADC Signal | Function |
|---|---|---|
| `s16_an[0]` | `ainp` | Positive differential input |
| `s16_an[1]` | `ainn` | Negative differential input |
| `analog_bus0` | `vrefp` | ADC reference voltage |
| `analog_bus1` | `vcm` | ADC common-mode voltage |

### Supplies

| Chipalooza Signal | ADC Signal |
|---|---|
| `vdd_3v3` | `vddh` |
| `vdd_1v2` | `vddl` |
| Ground network | `vss` |

### Control

| Chipalooza Signal | ADC Signal |
|---|---|
| `clk` | `CLK` |
| `dig_in[0]` | `START` |
| `dig_in[1]` | `RSTN` |

### Digital Outputs

| ADC Signal | Chipalooza Signal |
|---|---|
| `C0` | `dig_out[0]` |
| `C1` | `dig_out[1]` |
| `C2` | `dig_out[2]` |
| `C3` | `dig_out[3]` |
| `C4` | `dig_out[4]` |
| `C5` | `dig_out[5]` |
| `C6` | `dig_out[6]` |
| `C7` | `dig_out[7]` |
| `C8` | `dig_out[8]` |
| `C9` | `dig_out[9]` |
| `busy` | `dig_out[10]` |
| `valid` | `dig_out[11]` |

The harness routes START and RSTN through a digital input latch. A sustained START level produces repeated conversions; a short single-shot START pulse can be supplied through an external GPIO route or an appropriately configured sequencer.

---

# Layout

The reusable top-level ADC GDS is located at:

```text
circuit_files/layout/top/sar_10_bit_top.gds
```

The pre-fill version is retained at:

```text
circuit_files/layout/top_prefill/sar_10_bit_top_prefill.gds
```

Individual block layouts are available under:

```text
circuit_files/layout/
```

Layout views and characterization result plots are available in [`docs/`](docs/).

---

# SAR FSM

The SAR controller RTL is located at:

```text
circuit_files/src/sar_fsm/sar_fsm.v
```

---

# Target Performance

| Parameter | Target | Status |
|---|---:|---|
| Resolution | 10 bits | 10 bits |
| Architecture | Fully differential SAR | Fully differential SAR |
| Sampling rate | 1 MS/s | 1 MS/s in harness functional simulation at 60 MHz |
| Analog supply | 3.3 V | 3.3 V nominal |
| Digital supply | 1.2 V | 1.2 V nominal |
| DNL | Within ±1 LSB | Peak absolute DNL 0.199 LSB |
| INL | Within ±1 LSB | Peak absolute INL 0.139 LSB |
| Missing codes | None | None |
| Input type | Differential | Differential |
| Digital result | 10-bit parallel code | `C[9:0]` |
| Status outputs | `busy`, `valid` | Verified in sim |

The latest characterization plots are in [`docs/`](docs/).

The analysis also reported a 57.2 mV peak VSS IR drop, a 1.75 Ω VCM switch-tap resistance, and a 4.23 fF differential top-plate parasitic-capacitance difference.

---

# Results and Figures

The plots, schematics, and layout views below are stored in [`docs/`](docs/) and displayed directly from those files. 

## ADC Layout

![Complete SAR ADC GDS layout](docs/layouts/sar_top_gds.png)

*Top-level `sar_10_bit` layout.*

## Static Linearity and Transfer Characteristic

| | |
|:---:|:---:|
| <img src="docs/transfer_characteristic.png" alt="ADC transfer characteristic" width="470"><br><sub>ADC transfer characteristic</sub> | <img src="docs/transfer_midscale_zoom.png" alt="Transfer characteristic near midscale" width="470"><br><sub>Transfer characteristic near midscale</sub> |
| <img src="docs/dnl_vs_code.png" alt="DNL versus output code" width="470"><br><sub>DNL versus output code</sub> | <img src="docs/inl_vs_code.png" alt="INL versus output code" width="470"><br><sub>INL versus output code</sub> |
| <img src="docs/dnl_inl_pex_comparison.png" alt="PEX linearity comparison" width="470"><br><sub>PEX linearity comparison</sub> | <img src="docs/code_width_histogram.png" alt="Code width histogram" width="470"><br><sub>Code width histogram</sub> |

## Conversion Timing, Dynamic Performance and Power

| | |
|:---:|:---:|
| <img src="docs/sndr_enob_vs_fin.png" alt="SNDR and ENOB versus input frequency" width="470"><br><sub>SNDR and ENOB versus input frequency</sub> | <img src="docs/power_50_vs_65MHz.png" alt="Power at 50 and 65 MHz" width="470"><br><sub>Power at 50 and 65 MHz</sub> |
| <img src="docs/conversion_timing_50MHz.png" alt="Conversion timing at 50 MHz" width="470"><br><sub>Conversion timing at 50 MHz</sub> | <img src="docs/conversion_timing_65MHz.png" alt="Conversion timing at 65 MHz" width="470"><br><sub>Conversion timing at 65 MHz</sub> |
| <img src="docs/sar_switching_waveforms.png" alt="SAR switching waveforms" width="470"><br><sub>SAR switching waveforms</sub> | <img src="docs/smoke_vcm1.45_waveforms.png" alt="Transient smoke test with VCM at 1.45 V" width="470"><br><sub>Transient smoke test with VCM at 1.45 V</sub> |

## CDAC Settling

| | |
|:---:|:---:|
| <img src="docs/cdac_settling/msb_settling_pvt.png" alt="MSB settling across PVT conditions" width="470"><br><sub>MSB settling across PVT conditions</sub> | <img src="docs/cdac_settling/sar_switching_waveforms.png" alt="CDAC switching waveforms" width="470"><br><sub>CDAC switching waveforms</sub> |

## Comparator Characterization

| | |
|:---:|:---:|
| <img src="docs/comparator/decision_time_vs_overdrive.png" alt="Comparator decision time versus overdrive" width="470"><br><sub>Comparator decision time versus overdrive</sub> | <img src="docs/comparator/decision_waveforms_ss_125_3.png" alt="Comparator waveforms, SS at 125 C" width="470"><br><sub>Comparator waveforms, SS at 125 C</sub> |
| <img src="docs/comparator/noise_scurve.png" alt="Comparator noise S-curve" width="470"><br><sub>Comparator noise S-curve</sub> | <img src="docs/comparator/offset_history_vs_cm.png" alt="Comparator offset history versus common-mode" width="470"><br><sub>Comparator offset history versus common-mode</sub> |

## PVT and Monte Carlo Analysis

| | |
|:---:|:---:|
| <img src="docs/corner/pvt_summary.png" alt="PVT corner summary" width="470"><br><sub>PVT corner summary</sub> | <img src="docs/montecarlo/enob_distribution.png" alt="Monte Carlo ENOB distribution" width="470"><br><sub>Monte Carlo ENOB distribution</sub> |
| <img src="docs/montecarlo/offset_histogram.png" alt="Monte Carlo comparator offset histogram" width="470"><br><sub>Monte Carlo comparator offset histogram</sub> | <img src="docs/montecarlo/statistical_linearity.png" alt="Statistical linearity" width="470"><br><sub>Statistical linearity</sub> |

## Block Layouts

| | |
|:---:|:---:|
| <img src="docs/layouts/cdac_array_10b_diff.png" alt="Differential CDAC array" width="470"><br><sub>Differential CDAC array</sub> | <img src="docs/layouts/cdac_unit.png" alt="CDAC unit capacitor" width="470"><br><sub>CDAC unit capacitor</sub> |
| <img src="docs/layouts/strong_arm_comp.png" alt="Strong-arm comparator" width="470"><br><sub>Strong-arm comparator</sub> | <img src="docs/layouts/dac_sw_2to1_tg.png" alt="DAC switch" width="470"><br><sub>DAC switch</sub> |
| <img src="docs/layouts/tg.png" alt="Transmission gate" width="470"><br><sub>Transmission gate</sub> | <img src="docs/layouts/inverter.png" alt="Inverter" width="470"><br><sub>Inverter</sub> |
| <img src="docs/layouts/level_shifter_1v2_to_3v3.png" alt="1.2 V to 3.3 V level shifter" width="470"><br><sub>1.2 V to 3.3 V level shifter</sub> | <img src="docs/layouts/level_shifter_3v3_to_1v2.png" alt="3.3 V to 1.2 V level shifter" width="470"><br><sub>3.3 V to 1.2 V level shifter</sub> |
| <img src="docs/layouts/sar_fsm_wrapper.png" alt="SAR FSM layout" width="470"><br><sub>SAR FSM layout</sub> |   |

## Circuit Views

| | |
|:---:|:---:|
| <img src="docs/comparator.png" alt="Comparator circuit view" width="470"><br><sub>Comparator circuit view</sub> | <img src="docs/dac_SW.png" alt="DAC switch circuit view" width="470"><br><sub>DAC switch circuit view</sub> |
| <img src="docs/tg.png" alt="Transmission gate circuit view" width="470"><br><sub>Transmission gate circuit view</sub> |   |

## Schematics

![Top-level SAR ADC schematic](docs/schematics/01_TOP_sar_10_bit_adc.png)

*Top-level ADC schematic.*

| | |
|:---:|:---:|
| <img src="docs/schematics/02_strong_arm_comp.png" alt="Strong-arm comparator schematic" width="470"><br><sub>Strong-arm comparator schematic</sub> | <img src="docs/schematics/03_tg.png" alt="Transmission gate schematic" width="470"><br><sub>Transmission gate schematic</sub> |
| <img src="docs/schematics/04_inverter.png" alt="Inverter schematic" width="470"><br><sub>Inverter schematic</sub> | <img src="docs/schematics/05_dac_sw_2to1_tg.png" alt="DAC switch schematic" width="470"><br><sub>DAC switch schematic</sub> |
| <img src="docs/schematics/06_level_shifter_1v2_to_3v3.png" alt="1.2 V to 3.3 V level shifter schematic" width="470"><br><sub>1.2 V to 3.3 V level shifter schematic</sub> | <img src="docs/schematics/07_level_shifter_3v3_to_1v2.png" alt="3.3 V to 1.2 V level shifter schematic" width="470"><br><sub>3.3 V to 1.2 V level shifter schematic</sub> |
| <img src="docs/schematics/08_cdac_caps_10b_diff.png" alt="Differential CDAC schematic" width="470"><br><sub>Differential CDAC schematic</sub> | <img src="docs/schematics/09_sar_fsm_wrapper_symbol.png" alt="SAR FSM wrapper symbol" width="470"><br><sub>SAR FSM wrapper symbol</sub> |

---

# Repository Structure

```text
.
├── AUTHORS.md
│
├── circuit_files/
│   ├── layout/
│   │   ├── cdac/
│   │   ├── comparator/
│   │   ├── dac_switch/
│   │   ├── inverter/
│   │   ├── Levelshifter_1.2-3.3/
│   │   ├── Levelshifter_3.3-1.2/
│   │   ├── tg/
│   │   ├── top/
│   │   └── top_prefill/
│   │
│   ├── src/
│   │   └── sar_fsm/
│   │
│   ├── tb/
│   │
│   └── xschem/
│       ├── *.sch
│       ├── *.sym
│       ├── spice/
│       └── spice_pex/
│
├── chipalooza/
│   └── slot_16/
│       ├── layout/
│       ├── netlist/
│       └── verification/
│
├── final/
│   └── gds/
│       └── slot_16.gds
│
├── src/
│   ├── chip_core.sv
│   └── chip_top.sv
│
├── cocotb/
│   └── chip_top_tb.py
│
├── docs/
│   ├── Block_Diagram.png
│   ├── layouts/
│   ├── schematics/
│   ├── comparator/
│   ├── cdac_settling/
│   ├── corner/
│   ├── montecarlo/
│   ├── dnl_vs_code.png
│   ├── inl_vs_code.png
│   ├── sndr_enob_vs_fin.png
│   └── README.md
│
├── ip/
│   └── bondpad_70x70/
│
├── librelane/
│   ├── chip_top.sdc
│   └── config.yaml
│
├── Makefile
├── flake.nix
├── flake.lock
└── LICENSE
```

---

# Tools

The project uses the following open-source tools:

- Xschem
- ngspice
- KLayout
- Magic
- Yosys
- OpenROAD
- LibreLane
- Icarus Verilog
- cocotb

---

# Analog Simulation

Transistor-level testbenches are located under:

```text
circuit_files/tb/
```

Available testbenches include:

```text
cdac_caps_10b_diff_tb.sch
cdac_comp_msb_step_tb.sch
cdac_comp_sar_fsm_tb.sch
dac_sw_tb.sch
inv_tb.sch
LS_h2l_tb.sch
LS_l2h_tb.sch
sar_10_bit_tb.sch
sar_10_bit_tb_1.sch
strong_arm_comp_tb.sch
tg_tb.sch
```

Schematics and SPICE views are located under:

```text
circuit_files/xschem/
```

The directory also contains extracted/post-layout SPICE views under:

```text
circuit_files/xschem/spice_pex/
```

# Silicon Bring-Up Plan

Initial silicon testing is planned in the following order:

1. Verify continuity and supply connections.
2. Apply the 1.2 V and 3.3 V rails through the appropriate harness controls.
3. Hold the ADC in reset (`RSTN = 0`).
4. Measure static current.
5. Enable the project clock.
6. Apply the required `VCM` and `VREFP` through shared analog buses 1 and 0, respectively, with suitable external decoupling.
7. Apply a differential mid-scale input.
8. Release reset with START low, then trigger a conversion using the appropriate GPIO route or sequencer.
9. Check `busy`, `valid`, and `C[9:0]` through the harness readout.
10. Test several DC input levels.
11. Perform a complete DC transfer sweep.
12. Measure DNL, INL, offset, and gain.
13. Apply a sinusoidal differential input.
14. Measure SNR, SNDR, SFDR, and ENOB.
15. Repeat key measurements over voltage and temperature where practical.

---

## License

This project is licensed under the **Apache License 2.0**.

See [LICENSE](LICENSE) for details.
