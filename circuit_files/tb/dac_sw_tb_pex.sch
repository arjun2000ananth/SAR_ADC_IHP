v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N -230 -530 -230 -500 {
lab=vdd}
N -120 -300 -90 -300 {
lab=sel}
N -230 -300 -230 -90 {
lab=GND}
N -230 -340 -230 -300 {
lab=GND}
N -350 -460 -350 -430 {
lab=vss}
N -350 -370 -350 -340 {
lab=GND}
N -350 -340 -230 -340 {
lab=GND}
N -230 -300 -180 -300 {
lab=GND}
N 690 -190 690 -150 {
lab=GND}
N 690 -270 690 -250 {
lab=Voutp}
N 630 -270 690 -270 {
lab=Voutp}
N 250 -370 250 -340 {
lab=vdd}
N 60 -270 100 -270 {
lab=sel}
N 250 -200 250 -170 {
lab=vss}
N 400 -310 440 -310 {
lab=Voutp}
N 400 -280 440 -280 {
lab=vref}
N 400 -250 440 -250 {
lab=vcm}
N -230 -440 -230 -340 {
lab=GND}
C {vsource.sym} -230 -470 0 0 {name=VDD_SRC value="dc \{VDD\}" savecurrent=false}
C {gnd.sym} -230 -90 0 0 {name=l3 lab=GND}
C {lab_pin.sym} -230 -530 0 0 {name=p24 sig_type=std_logic lab=vdd

}
C {vsource.sym} -150 -300 1 0 {name=V_VINP value="PULSE(0 \{VDD\} 5n 20p 20p 40n 100n)" savecurrent=false}
C {lab_pin.sym} -90 -300 2 0 {name=p26 sig_type=std_logic lab=sel}
C {vsource.sym} -350 -400 0 0 {name=V_VSS value="dc 0" savecurrent=false}
C {lab_pin.sym} -350 -460 0 0 {name=p28 sig_type=std_logic lab=vss

}
C {code_shown.sym} -160 -25 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOSlv.lib mos_fs
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_fs
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib res_typ

.include /foss/designs/SAR_ADC_IHP/circuit_files/layout/dac_switch/pex/dac_sw_2to1_tg.pex.spice
** osdi /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/osdi/cap_cmomi.osdi
** .include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cap_cmomi.lib
** .lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib cap_typ
** .include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib
** .include 
"}
C {code.sym} 910 70 0 0 {name=s1
only_toplevel=true
value="
* ============================================================
* Testbench parameters
* ============================================================

.param VDD   = 3.3
.param VCM   = 1.65
.param VREF  = 3.3
.param VDIFF = 0
.param CLOAD = 25.6p

* Local reference sources
VREF_SRC vref GND dc \{VREF\}
VVCM_SRC vcm  GND dc \{VCM\}

* Simulation options
.options savecurrents
.options reltol=1e-4
.options abstol=1e-12
.options vntol=1e-6
.options method=gear
.options maxord=2

* Save signals and currents
.save v(sel)
.save v(Voutp)
.save v(vref)
.save v(vcm)
.save v(vdd)
.save v(vss)
.save i(VDD_SRC)
.save i(VREF_SRC)
.save i(VVCM_SRC)

.control

shell rm -f dac_sw_results.txt

echo DAC switch PEX transient verification > dac_sw_results.txt
echo VDD = 3.3V >> dac_sw_results.txt
echo VCM = 1.65V >> dac_sw_results.txt
echo CLOAD = 25.6pF >> dac_sw_results.txt
echo Settling threshold = 5mV >> dac_sw_results.txt
echo columns: case out_low err_low out_high err_high out_return err_return pass >> dac_sw_results.txt

* ============================================================
* CASE A: VREF = 3.3 V
* ============================================================

alterparam VREF = 3.3
reset
tran 2p 100n

write dac_sw_case_A.raw v(sel) v(Voutp) v(vref) v(vcm) v(vdd) v(vss) i(VDD_SRC) i(VREF_SRC) i(VVCM_SRC)

meas tran out_low_A FIND v(Voutp) AT=4n
meas tran vcm_low_A FIND v(vcm) AT=4n
let err_low_A = out_low_A - vcm_low_A

meas tran out_high_A FIND v(Voutp) AT=20n
meas tran vref_high_A FIND v(vref) AT=20n
let err_high_A = out_high_A - vref_high_A

meas tran out_ret_A FIND v(Voutp) AT=80n
meas tran vcm_ret_A FIND v(vcm) AT=80n
let err_ret_A = out_ret_A - vcm_ret_A

let pass_low_A = 0
if abs(err_low_A) < 5m
  let pass_low_A = 1
end

let pass_high_A = 0
if abs(err_high_A) < 5m
  let pass_high_A = 1
end

let pass_return_A = 0
if abs(err_ret_A) < 5m
  let pass_return_A = 1
end

let pass_case_A = 0
if pass_low_A = 1
  if pass_high_A = 1
    if pass_return_A = 1
      let pass_case_A = 1
    end
  end
end

echo CASE_A $&out_low_A $&err_low_A $&out_high_A $&err_high_A $&out_ret_A $&err_ret_A $&pass_case_A >> dac_sw_results.txt

* ============================================================
* CASE B: VREF = 0 V
* ============================================================

alterparam VREF = 0
reset
tran 2p 100n

write dac_sw_case_B.raw v(sel) v(Voutp) v(vref) v(vcm) v(vdd) v(vss) i(VDD_SRC) i(VREF_SRC) i(VVCM_SRC)

meas tran out_low_B FIND v(Voutp) AT=4n
meas tran vcm_low_B FIND v(vcm) AT=4n
let err_low_B = out_low_B - vcm_low_B

meas tran out_high_B FIND v(Voutp) AT=20n
meas tran vref_high_B FIND v(vref) AT=20n
let err_high_B = out_high_B - vref_high_B

meas tran out_ret_B FIND v(Voutp) AT=80n
meas tran vcm_ret_B FIND v(vcm) AT=80n
let err_ret_B = out_ret_B - vcm_ret_B

let pass_low_B = 0
if abs(err_low_B) < 5m
  let pass_low_B = 1
end

let pass_high_B = 0
if abs(err_high_B) < 5m
  let pass_high_B = 1
end

let pass_return_B = 0
if abs(err_ret_B) < 5m
  let pass_return_B = 1
end

let pass_case_B = 0
if pass_low_B = 1
  if pass_high_B = 1
    if pass_return_B = 1
      let pass_case_B = 1
    end
  end
end

echo CASE_B $&out_low_B $&err_low_B $&out_high_B $&err_high_B $&out_ret_B $&err_ret_B $&pass_case_B >> dac_sw_results.txt

* ============================================================
* Overall pass
* ============================================================

let pass_overall = 0
if pass_case_A = 1
  if pass_case_B = 1
    let pass_overall = 1
  end
end

echo pass_case_A = $&pass_case_A >> dac_sw_results.txt
echo pass_case_B = $&pass_case_B >> dac_sw_results.txt
echo pass_overall = $&pass_overall >> dac_sw_results.txt

.endc


"}
C {capa.sym} 690 -220 0 0 {name=COUT
m=1
value=\{CLOAD\}
footprint=1206
device="ceramic capacitor"}
C {lab_pin.sym} 690 -150 3 0 {name=p17 sig_type=std_logic lab=GND}
C {lab_pin.sym} 630 -270 0 0 {name=p31 sig_type=std_logic lab=Voutp}
C {lab_pin.sym} 250 -370 0 0 {name=p1 sig_type=std_logic lab=vdd

}
C {lab_pin.sym} 250 -170 0 0 {name=p2 sig_type=std_logic lab=vss

}
C {lab_pin.sym} 60 -270 0 0 {name=p3 sig_type=std_logic lab=sel}
C {lab_pin.sym} 440 -310 2 0 {name=p4 sig_type=std_logic lab=Voutp}
C {lab_pin.sym} 440 -280 2 0 {name=p5 sig_type=std_logic lab=vref}
C {lab_pin.sym} 440 -250 2 0 {name=p6 sig_type=std_logic lab=vcm}
C {iopin.sym} 750 -340 0 0 {name=p18 lab=vref}
C {iopin.sym} 750 -300 0 0 {name=p7 lab=vcm}
C {/foss/designs/SAR_ADC_IHP_09302026/circuit_files/xschem/dac_sw_2to1_tg_pex.sym} 250 -270 0 0 {name=x1}
