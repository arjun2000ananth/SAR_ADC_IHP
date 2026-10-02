v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {name=MODELS1 only_toplevel=true
format="tcleval( @value )"
value="
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOSlv.lib mos_tt
.include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/sg13g2_moshv_mod.lib
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib res_typ
.include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cap_cmomi.lib

** osdi /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/osdi/cap_cmomi.osdi
** .lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib cap_typ
** .include $\{::180MCU_MODELS\}/design.ngspice

** .lib $\{::180MCU_MODELS\}/sm141064.ngspice typical
** .include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib
** .include 

"} 300 320 0 0 0.4 0.4 {}
T {
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOSlv.lib mos_tt
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib res_typ
.include /foss/pdks/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/spice/sg13cmos5l_stdcell.spice
.include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cap_cmomi.lib

.include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/sg13g2_moshv_mod.lib
** osdi /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/osdi/cap_cmomi.osdi
** .lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib cap_typ
** .include $\{::180MCU_MODELS\}/design.ngspice

** .lib $\{::180MCU_MODELS\}/sm141064.ngspice typical
** .include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib
** .include } 1220 260 0 0 0.4 0.4 {}
N 30 70 30 120 {
lab=GND}
N 30 -320 30 -290 {
lab=vdd}
N 30 70 80 70 {
lab=GND}
N 140 70 170 70 {
lab=ng}
N 140 -20 170 -20 {
lab=pg}
N 30 -20 80 -20 {
lab=GND}
N 30 -20 30 70 {
lab=GND}
N 30 -180 30 -20 {
lab=GND}
N 210 -170 240 -170 {
lab=ng}
N 210 -150 240 -150 {
lab=pg}
N 210 -120 240 -120 {
lab=Va}
N 390 -220 390 -200 {
lab=vdd}
N 390 -80 390 -50 {
lab=vss}
N 540 -140 570 -140 {
lab=Voutp}
N -110 -180 -80 -180 {
lab=Va}
N -20 -180 30 -180 {
lab=GND}
N -80 20 -80 50 {
lab=vss}
N -80 110 -80 120 {
lab=GND}
N -80 120 30 120 {
lab=GND}
N 720 -110 720 -70 {
lab=GND}
N 720 -190 720 -170 {
lab=Voutp}
N 660 -190 720 -190 {
lab=Voutp}
N 30 -230 30 -180 {
lab=GND}
C {vsource.sym} 110 70 1 0 {name=VGN_SRC value=\{VGN\} savecurrent=false}
C {vsource.sym} 30 -260 0 0 {name=VDD_SRC value=\{VDD\} savecurrent=false}
C {gnd.sym} 30 120 0 0 {name=l3 lab=GND}
C {lab_pin.sym} 30 -320 0 0 {name=p10 sig_type=std_logic lab=vdd

}
C {lab_pin.sym} 170 70 2 0 {name=p9 sig_type=std_logic lab=ng}
C {vsource.sym} 110 -20 1 0 {name=VGP_SRC value=\{VGP\} savecurrent=false}
C {lab_pin.sym} 170 -20 2 0 {name=p18 sig_type=std_logic lab=pg}
C {code.sym} 250 50 0 0 {name=s2 only_toplevel=false value="
.include /foss/designs/SAR_ADC_IHP/circuit_files/layout/tg/pex/tg.pex.spice

.param VDD=3.3
.param VGN=3.3
.param VGP=0
.param CLOAD=5.12p

.save v(Va) v(Voutp) v(ng) v(pg) i(VDD_SRC)

.control
tran 2p 120n
write tg_pex_transient.raw v(Va) v(Voutp) v(ng) v(pg) i(VDD_SRC)

meas tran Va_9ns FIND v(Va) AT=9n
meas tran Vout_9ns FIND v(Voutp) AT=9n
meas tran Va_16ns FIND v(Va) AT=16n
meas tran Vout_16ns FIND v(Voutp) AT=16n

plot v(Va) v(Voutp) v(ng) v(pg)
.endc

"}
C {lab_pin.sym} 210 -150 0 0 {name=p1 sig_type=std_logic lab=pg}
C {lab_pin.sym} 210 -170 0 0 {name=p2 sig_type=std_logic lab=ng}
C {vsource.sym} -50 -180 3 0 {name=V_a value="PULSE(0 \{VDD\} 1n 20p 20p 29n 60n)" savecurrent=false}
C {lab_pin.sym} -110 -180 0 0 {name=p19 sig_type=std_logic lab=Va}
C {lab_pin.sym} 210 -120 0 0 {name=p3 sig_type=std_logic lab=Va}
C {lab_pin.sym} 390 -220 0 0 {name=p4 sig_type=std_logic lab=vdd

}
C {vsource.sym} -80 80 0 0 {name=V_VSS value="dc 0" savecurrent=false}
C {lab_pin.sym} -80 20 0 0 {name=p28 sig_type=std_logic lab=vss

}
C {lab_pin.sym} 390 -50 0 0 {name=p5 sig_type=std_logic lab=vss

}
C {capa.sym} 720 -140 0 0 {name=COUT
m=1
value=\{CLOAD\}
footprint=1206
device="ceramic capacitor"}
C {lab_pin.sym} 720 -70 3 0 {name=p17 sig_type=std_logic lab=GND}
C {lab_pin.sym} 660 -190 0 0 {name=p31 sig_type=std_logic lab=Voutp}
C {lab_pin.sym} 570 -140 2 0 {name=p6 sig_type=std_logic lab=Voutp}
C {code_shown.sym} 420 -5 0 0 {name=MODELS1 only_toplevel=true
format="tcleval( @value )"
value="
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOSlv.lib mos_tt
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib res_typ

** osdi /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/osdi/cap_cmomi.osdi
** .include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cap_cmomi.lib
** .lib /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib cap_typ
** .include /foss/pdks/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib
** .include "cap_cmomi.lib"
.include /foss/pdks/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/spice/sg13cmos5l_stdcell.spice
"}
C {/foss/designs/SAR_ADC_IHP/circuit_files/xschem/tg_pex.sym} 390 -140 0 0 {name=x2}
