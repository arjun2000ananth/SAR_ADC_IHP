v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N -830 -180 -830 -130 {
lab=GND}
N -830 -570 -830 -540 {
lab=vddl}
N -830 -180 -780 -180 {
lab=GND}
N -720 -180 -690 -180 {
lab=in}
N -720 -340 -690 -340 {
lab=vddh}
N -830 -340 -830 -180 {
lab=GND}
N -830 -380 -830 -340 {
lab=GND}
N -950 -500 -950 -470 {
lab=vss}
N -950 -410 -950 -380 {
lab=GND}
N -950 -380 -830 -380 {
lab=GND}
N -160 -410 -160 -370 {
lab=GND}
N -160 -490 -160 -470 {
lab=Vout}
N -220 -490 -160 -490 {
lab=Vout}
N -830 -340 -780 -340 {
lab=GND}
N -830 -480 -830 -380 {
lab=GND}
N -610 -520 -590 -520 {lab=in}
N -520 -610 -520 -590 {lab=vddl}
N -380 -610 -380 -590 {lab=vddh}
N -290 -520 -270 -520 {lab=Vout}
N -440 -450 -440 -420 {lab=vss}
N -440 -590 -380 -590 {lab=vddh}
C {vsource.sym} -750 -180 1 0 {name=V_VIN value="PULSE(0 \{VDDL\} 10n 100p 100p 20n 40n)" savecurrent=false}
C {vsource.sym} -830 -510 0 0 {name=VDD_L value="dc \{VDDL\}" savecurrent=false}
C {gnd.sym} -830 -130 0 0 {name=l3 lab=GND}
C {lab_pin.sym} -830 -570 0 0 {name=p24 sig_type=std_logic lab=vddl

}
C {lab_pin.sym} -690 -340 2 0 {name=p25 sig_type=std_logic lab=vddh}
C {vsource.sym} -750 -340 1 0 {name=VDD_H value="dc \{VDDH\}" savecurrent=false}
C {lab_pin.sym} -690 -180 2 0 {name=p26 sig_type=std_logic lab=in}
C {vsource.sym} -950 -440 0 0 {name=V_VSS value="dc 0" savecurrent=false}
C {lab_pin.sym} -950 -500 0 0 {name=p28 sig_type=std_logic lab=vss

}
C {capa.sym} -160 -440 0 0 {name=COUT
m=1
value=\{CLOAD\}
footprint=1206
device="ceramic capacitor"}
C {lab_pin.sym} -160 -370 3 0 {name=p17 sig_type=std_logic lab=GND}
C {lab_pin.sym} -220 -490 0 0 {name=p31 sig_type=std_logic lab=Vout}
C {code_shown.sym} -650 -235 0 0 {name=MODELS2 only_toplevel=true
format="tcleval( @value )"
value="
** .lib /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOSlv.lib mos_tt
** .lib /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
** .lib /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib res_typ

** .lib /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOSlv.lib mos_tt
** .lib /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt

.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOSlv.lib mos_tt
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib res_typ
.include /foss/designs/SAR_ADC_IHP/circuit_files/layout/Levelshifter_1.2-3.3/pex/level_shifter_1v2_to_3v3.pex.spice

** osdi /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/osdi/cap_cmomi.osdi
** .include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cap_cmomi.lib
** .lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib cap_typ
** .include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib
** .include "cap_cmomi.lib"
.include /foss/pdks/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/spice/sg13cmos5l_stdcell.spice

"}
C {lab_pin.sym} -440 -420 0 0 {name=p1 sig_type=std_logic lab=vss

}
C {lab_pin.sym} -270 -520 2 0 {name=p2 sig_type=std_logic lab=Vout}
C {lab_pin.sym} -610 -520 0 0 {name=p3 sig_type=std_logic lab=in}
C {lab_pin.sym} -380 -610 2 0 {name=p4 sig_type=std_logic lab=vddh}
C {lab_pin.sym} -520 -610 0 0 {name=p5 sig_type=std_logic lab=vddl

}
C {code_shown.sym} -40 -580 0 0 {name=s2 only_toplevel=false value="
.param VDDL=1.2
.param VDDH=3.3
.param CLOAD=50f

.options savecurrents
.options reltol=1e-4 abstol=1e-12 vntol=1e-6
.options method=gear maxord=2
.options plotwinsize=0

.save v(in)
.save v(x1.inb)
.save v(x1.a)
.save v(x1.b)
.save v(Vout)

.save i(VDD_L)
.save i(VDD_H)
"}
C {code.sym} 190 -360 0 0 {name=s3
only_toplevel=true
value="
.control

set noaskquit
set filetype=binary
set wr_singlescale
set wr_vecnames

shell rm -f level_shifter_pex_results.txt
shell rm -f level_shifter_pex.raw

echo ============================================================ > level_shifter_pex_results.txt
echo IHP SG13CMOS5L LEVEL SHIFTER PEX TRANSIENT TEST >> level_shifter_pex_results.txt
echo ============================================================ >> level_shifter_pex_results.txt
echo VDDL = 1.2 V >> level_shifter_pex_results.txt
echo VDDH = 3.3 V >> level_shifter_pex_results.txt
echo CLOAD = 50 fF >> level_shifter_pex_results.txt
echo Output limits: LOW < 0.33 V, HIGH > 2.97 V >> level_shifter_pex_results.txt

* Use the nominal values already defined in the testbench
alterparam VDDL=1.2
alterparam VDDH=3.3
alterparam CLOAD=50f

reset

* Input source is expected to be:
* PULSE(0 \{VDDL\} 10n 100p 100p 20n 40n)
*
* Input:
*   LOW  approximately 0–10 ns
*   HIGH approximately 10–30 ns
*   LOW  approximately 30–50 ns
*   HIGH approximately 50–70 ns
*
* Run long enough to capture two complete transitions.
tran 10p 90n

* Save the PEX transient waveform
write level_shifter_pex.raw v(in) v(Vout) v(vddl) v(vddh) v(vss) i(VDD_L) i(VDD_H)

* ============================================================
* STATIC LOGIC LEVELS
* ============================================================

* Input HIGH
meas tran in_high FIND v(in) AT=25n
meas tran out_high FIND v(Vout) AT=25n

* Input LOW
meas tran in_low FIND v(in) AT=45n
meas tran out_low FIND v(Vout) AT=45n

let high_limit = 0.9*VDDH
let low_limit  = 0.1*VDDH

let err_high = out_high - VDDH
let err_low  = out_low

* ============================================================
* PROPAGATION DELAY
* ============================================================

* Input threshold = VDDL/2 = 0.6 V
* Output threshold = VDDH/2 = 1.65 V
*
* Use the second complete transition.
meas tran tplh TRIG v(in) VAL=0.6 RISE=2 TARG v(Vout) VAL=1.65 RISE=2
meas tran tphl TRIG v(in) VAL=0.6 FALL=2 TARG v(Vout) VAL=1.65 FALL=2

* ============================================================
* OUTPUT RISE/FALL TIME
* ============================================================

meas tran tr_out TRIG v(Vout) VAL=0.33 RISE=2 TARG v(Vout) VAL=2.97 RISE=2
meas tran tf_out TRIG v(Vout) VAL=2.97 FALL=2 TARG v(Vout) VAL=0.33 FALL=2

* ============================================================
* SUPPLY CURRENT AND POWER
* ============================================================

meas tran iddl_avg AVG i(VDD_L) FROM=10n TO=90n
meas tran iddh_avg AVG i(VDD_H) FROM=10n TO=90n

let p_vddl = abs(VDDL*iddl_avg)
let p_vddh = abs(VDDH*iddh_avg)
let p_total = p_vddl + p_vddh

* ============================================================
* PASS CONDITIONS
*
* Output HIGH must be > 90% of VDDH
* Output LOW must be < 10% of VDDH
* ============================================================

let pass_high = 0
if out_high > high_limit
  let pass_high = 1
end

let pass_low = 0
if out_low < low_limit
  let pass_low = 1
end

let functional_pass = 0
if pass_high = 1
  if pass_low = 1
    let functional_pass = 1
  end
end

* ============================================================
* WRITE RESULTS
* ============================================================

echo ------------------------------------------------------------ >> level_shifter_pex_results.txt
echo STATIC LEVELS >> level_shifter_pex_results.txt
echo ------------------------------------------------------------ >> level_shifter_pex_results.txt
echo Input_HIGH = $&in_high V >> level_shifter_pex_results.txt
echo Output_HIGH = $&out_high V >> level_shifter_pex_results.txt
echo High_error = $&err_high V >> level_shifter_pex_results.txt
echo Input_LOW = $&in_low V >> level_shifter_pex_results.txt
echo Output_LOW = $&out_low V >> level_shifter_pex_results.txt
echo Low_error = $&err_low V >> level_shifter_pex_results.txt

echo ------------------------------------------------------------ >> level_shifter_pex_results.txt
echo TIMING >> level_shifter_pex_results.txt
echo ------------------------------------------------------------ >> level_shifter_pex_results.txt
echo TPLH = $&tplh s >> level_shifter_pex_results.txt
echo TPHL = $&tphl s >> level_shifter_pex_results.txt
echo Output_rise_10_to_90 = $&tr_out s >> level_shifter_pex_results.txt
echo Output_fall_90_to_10 = $&tf_out s >> level_shifter_pex_results.txt

echo ------------------------------------------------------------ >> level_shifter_pex_results.txt
echo POWER >> level_shifter_pex_results.txt
echo ------------------------------------------------------------ >> level_shifter_pex_results.txt
echo VDDL_power = $&p_vddl W >> level_shifter_pex_results.txt
echo VDDH_power = $&p_vddh W >> level_shifter_pex_results.txt
echo Total_average_power = $&p_total W >> level_shifter_pex_results.txt

echo ------------------------------------------------------------ >> level_shifter_pex_results.txt
echo PASS RESULT >> level_shifter_pex_results.txt
echo ------------------------------------------------------------ >> level_shifter_pex_results.txt
echo Pass_HIGH = $&pass_high >> level_shifter_pex_results.txt
echo Pass_LOW = $&pass_low >> level_shifter_pex_results.txt
echo FUNCTIONAL_PASS = $&functional_pass >> level_shifter_pex_results.txt

* Optional ASCII waveform file
wrdata level_shifter_pex_waveforms.txt v(in) v(Vout) v(vddl) v(vddh) v(vss)

* Display waveforms if running interactively
plot v(in) v(Vout)
plot v(vddl) v(vddh) v(Vout)

.endc

"}
C {/foss/designs/SAR_ADC_IHP_09302026/circuit_files/xschem/level_shifter_1v2_to_3v3_pex.sym} -440 -520 0 0 {name=x3}
