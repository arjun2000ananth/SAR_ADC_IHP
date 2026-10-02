# 10-Bit SAR ADC — IHP SG13CMOS5L

Block-level and ADC characterisation results, including parasitic extraction, process-corner sweeps, and statistical analysis. Test conditions are shown in the individual plots.

## Block Diagram

![10-bit SAR ADC block diagram](Block_Diagram.png)

## Individual Block Testbenches

### Transmission Gate

The input pulse switches between 0 V and 3.3 V every 30 ns. The transmission gate drives a 5.12 pF load.

![Transmission gate waveform](tg.png)

### Comparator

The comparator inputs are 1.65 V ± 5 mV. Each output drives a 20 fF load.

![Comparator waveform](comparator.png)

### DAC Switch

A selector signal determines whether the load capacitance is driven high or low. The load is 25.6 pF, equivalent to 5,120 unit capacitors of 5 fF each.

The upper waveform shows charging the load; the lower waveform shows discharging it.

![DAC switch waveform](dac_SW.png)

## ADC Transfer Characteristic

### Full Input Range

![ADC transfer characteristic](transfer_characteristic.png)

### Midscale Detail

![ADC transfer characteristic near midscale](transfer_midscale_zoom.png)

## Static Linearity

### Differential Nonlinearity

![DNL versus output code](dnl_vs_code.png)

### Integral Nonlinearity

![INL versus output code](inl_vs_code.png)

### PEX Comparison

![DNL and INL comparison](dnl_inl_pex_comparison.png)

### Code-Width Distribution

![Code-width histogram](code_width_histogram.png)

## Dynamic Performance

![SNDR and ENOB versus input frequency](sndr_enob_vs_fin.png)

## ADC Waveforms

### SAR Switching

![SAR switching waveforms](sar_switching_waveforms.png)

### Common-Mode Test at VCM = 1.45 V

![ADC smoke-test waveforms at VCM 1.45 V](smoke_vcm1.45_waveforms.png)

## CDAC Switching and Settling

### Switching Waveforms

![CDAC switching during SAR conversion](cdac_settling/sar_switching_waveforms.png)

### MSB Settling Across PVT

![MSB settling across process, voltage, and temperature](cdac_settling/msb_settling_pvt.png)

## Comparator Characterisation

### Decision Time Versus Input Overdrive

![Comparator decision time versus input overdrive](comparator/decision_time_vs_overdrive.png)

### Decision Waveforms — SS, 125 °C, VDDH = 3.0 V

![Comparator decision waveforms at SS, 125 degrees Celsius, and 3.0 V](comparator/decision_waveforms_ss_125_3.png)

### Input-Referred Noise

![Comparator noise S-curve](comparator/noise_scurve.png)

### Offset and Decision-History Dependence

![Comparator offset and decision-history dependence versus common-mode voltage](comparator/offset_history_vs_cm.png)

## Corner Analysis

![PVT corner summary](corner/pvt_summary.png)

## Monte Carlo Analysis

### Comparator Offset Distribution

![Monte Carlo comparator offset histogram](montecarlo/offset_histogram.png)

### Statistical Linearity

![Monte Carlo static-linearity results](montecarlo/statistical_linearity.png)

### ENOB Distribution

![Monte Carlo ENOB distribution](montecarlo/enob_distribution.png)

## Power Consumption

![Power consumption at 50 MHz and 65 MHz](power_50_vs_65MHz.png)
