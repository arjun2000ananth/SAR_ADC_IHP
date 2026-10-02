# 10-Bit SAR ADC — IHP SG13CMOS5L

Individual Testbench Results for parasitic extraction and five corner cases.

## Transmission Gate

A pulse changes every 30 ns from 0V to 3.3V. Transmission gate drives a 5.12pF load.

![Transmission Gate Waveform](tg.png)

---

## Comparator

The comparator's output waveform. Input voltages are 1.65V +/- 5mV. The output drives a 20fF load each side.

![Comparator Waveform](comparator.png)

---

## DAC Switch

A selector signal toggles determines if the load capacitance should be high or low. CLOAD is 25.6pF, which is 5,120 times the unit capacitance of 5 fF.

Top waveform drives the load capacitance to be high.

Bottom waveform drives the load capacitance to be low.

![DAC Switch Waveform](dac_SW.png)
