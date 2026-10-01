# 10-Bit SAR ADC — IHP SG13CMOS5L

A fully differential 10-bit successive-approximation-register (SAR) ADC designed in the **IHP SG13CMOS5L** process for the **Chipalooza Challenge**.

The repository contains the transistor-level analog design, SAR control logic, block-level and top-level layout, post-layout verification, and the final integration into **Chipalooza slot 16**.

The ADC targets approximately **1 MS/s** operation and uses separate **3.3 V analog/high-voltage** and **1.2 V digital/low-voltage** supply domains.

---

## Team

| Name | Role |
|---|---|
| Arjun Ananth | Lead Designer — Design & Layout |
| Man Yu | Verification |
| Kelvin Olonade | Verification Support |

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


block diagram:

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

---

## Supply Domains

| Domain | Nominal Voltage | Usage |
|---|---:|---|
| `vddh` | 3.3 V | Analog / high-voltage circuitry |
| `vddl` | 1.2 V | SAR FSM and low-voltage digital circuitry |
| `vss` | 0 V | Common ground |

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


The final harness-compatible GDS is:
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

---

# SAR FSM

The SAR controller RTL is located at:

```text
circuit_files/src/sar_fsm/sar_fsm.v
```

---

# Verification

Verification is performed at both block level and full-ADC level.

---

## Physical Verification Status

| Check | Status |
|---|---|
| Main DRC | PASS |
| Maximal-rule DRC | PASS |
| Antenna checks | PASS |
| DRC with official slot-wrapper geometry | PASS |
| LVS | PASS |
| Slot connectivity audit | PASS |

Verification logs are available under:

```text
chipalooza/slot_16/verification/
```

---

# Target Performance

| Parameter | Target |
|---|---:|
| Resolution | 10 bits |
| Architecture | Fully differential SAR |
| Sampling rate | 1 MS/s |
| Analog supply | 3.3 V |
| Digital supply | 1.2 V |
| DNL | within ±1 LSB target |
| INL | within ±1 LSB target |
| Missing codes | None |
| Input type | Differential |
| Digital result | 10-bit parallel code |
| Status outputs | `busy`, `valid` |

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

---


# Silicon Bring-Up Plan

Initial silicon testing is planned in the following order:

1. Verify continuity and supply connections.
2. Apply the 1.2 V and 3.3 V rails.
3. Hold the ADC in reset.
4. Measure static current.
5. Enable the project clock.
6. Apply the required `VCM` and `VREF`.
7. Apply a differential mid-scale input.
8. Trigger a conversion.
9. Check `busy`, `valid`, and `C[9:0]`.
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
