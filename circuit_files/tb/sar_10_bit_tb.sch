v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N -310 -180 -310 -155 {
lab=GND}
N -310 -700 -310 -670 {
lab=vddh}
N -310 -310 -260 -310 {
lab=GND}
N -200 -310 -170 -310 {
lab=ainn}
N -200 -470 -170 -470 {
lab=ainp}
N -310 -470 -310 -310 {
lab=GND}
N -310 -510 -310 -470 {
lab=GND}
N -430 -630 -430 -600 {
lab=vss}
N -430 -540 -430 -510 {
lab=GND}
N -430 -510 -310 -510 {
lab=GND}
N -430 -400 -430 -370 {
lab=CLK}
N -430 -510 -430 -460 {
lab=GND}
N -310 -470 -260 -470 {
lab=GND}
N -220 -570 -190 -570 {
lab=vcm}
N -310 -570 -280 -570 {
lab=GND}
N -310 -130 -310 -40 {
lab=GND}
N -430 -130 -400 -130 {
lab=vrefp}
N -340 -130 -310 -130 {
lab=GND}
N -310 -155 -305 -155 {
lab=GND}
N -650 -510 -430 -510 {
lab=GND}
N -650 -420 -650 -390 {
lab=RSTN}
N -650 -510 -650 -480 {
lab=GND}
N -650 -620 -650 -590 {
lab=START}
N -650 -530 -650 -510 {
lab=GND}
N 180 -540 180 -510 {
lab=vddh}
N 60 -250 90 -250 {
lab=RSTN}
N 60 -230 90 -230 {
lab=START}
N 60 -410 90 -410 {
lab=vrefp}
N 60 -350 90 -350 {
lab=ainn}
N 60 -310 90 -310 {
lab=ainp}
N 60 -450 90 -450 {
lab=vcm}
N 60 -210 90 -210 {
lab=CLK}
N 240 -160 240 -140 {
lab=vss}
N 390 -230 420 -230 {
lab=busy}
N 390 -250 420 -250 {
lab=valid}
N 390 -470 420 -470 {
lab=C0}
N 390 -450 420 -450 {
lab=C1}
N 390 -430 420 -430 {
lab=C2}
N 390 -410 420 -410 {
lab=C3}
N 390 -390 420 -390 {
lab=C4}
N 390 -370 420 -370 {
lab=C5}
N 390 -350 420 -350 {
lab=C6}
N 390 -330 420 -330 {
lab=C7}
N 390 -310 420 -310 {
lab=C8}
N 390 -290 420 -290 {
lab=C9}
N 390 -200 420 -200 {
lab=Voutn}
N -310 -570 -310 -510 {
lab=GND}
N -310 -610 -310 -570 {
lab=GND}
N -310 -155 -310 -130 {
lab=GND}
N 280 -540 280 -510 {
lab=vddl}
N -200 -180 -170 -180 {
lab=vddl}
N -310 -180 -260 -180 {lab=GND}
N -310 -310 -310 -180 {
lab=GND}
C {sar_10_bit.sym} 240 -330 0 0 {name=x1}
C {vsource.sym} -230 -310 1 0 {name=V_VIN value="dc \{VCM - VDIFF/2\}" savecurrent=false}
C {vsource.sym} -310 -640 0 0 {name=VDD_SRC value="dc \{VDDH\}" savecurrent=false}
C {gnd.sym} -310 -40 0 0 {name=l3 lab=GND}
C {lab_pin.sym} -310 -700 0 0 {name=p24 sig_type=std_logic lab=vddh

}
C {lab_pin.sym} -170 -310 2 0 {name=p25 sig_type=std_logic lab=ainn}
C {vsource.sym} -230 -470 1 0 {name=V_VINP value="dc \{VCM + VDIFF/2\}" savecurrent=false}
C {lab_pin.sym} -170 -470 2 0 {name=p26 sig_type=std_logic lab=ainp}
C {vsource.sym} -430 -570 0 0 {name=V_VSS value="dc 0" savecurrent=false}
C {lab_pin.sym} -430 -630 0 0 {name=p28 sig_type=std_logic lab=vss

}
C {vsource.sym} -430 -430 2 0 {name=V_CLK value="PULSE(0 \{VDDL\} 30n 20p 20p 10n 20n)" savecurrent=false}
C {lab_pin.sym} -430 -370 3 0 {name=p29 sig_type=std_logic lab=CLK}
C {vsource.sym} -250 -570 1 0 {name=V_VCM1 value="dc \{VCM\}" savecurrent=false}
C {lab_pin.sym} -190 -570 1 0 {name=V_VCM sig_type=std_logic lab=vcm

}
C {vsource.sym} -370 -130 3 0 {name=VREFP_SRC value="dc \{VDDH\}" savecurrent=false}
C {lab_pin.sym} -430 -130 3 0 {name=V_VCM5 sig_type=std_logic lab=vrefp

}
C {vsource.sym} -650 -450 2 0 {name=V_RSTN value="PULSE(0 \{VDDL\} 60n 20p 20p 10u 20u)" savecurrent=false}
C {lab_pin.sym} -650 -390 3 0 {name=p8 sig_type=std_logic lab=RSTN}
C {vsource.sym} -650 -560 0 0 {name=V_START value="PULSE(0 \{VDDL\} 105n 20p 20p 50n 10u)" savecurrent=false}
C {lab_pin.sym} -650 -620 1 0 {name=p9 sig_type=std_logic lab=START}
C {code.sym} 1570 135 0 0 {name=s1
only_toplevel=true
value="
.control

set noaskquit
set num_threads=6

setplot const

let vin_vec = vector(3)
let code_vec = vector(3)
let valid_vec = vector(3)

let vin_vec[0] = -1.6
let vin_vec[1] = 0
let vin_vec[2] = 1.6

let index = 0


echo
echo BASIC_SAR_ADC_FUNCTIONAL_TEST

repeat 3

  let vdiff_now = vin_vec[index]
  let vinp_now = 1.65 + vdiff_now/2
  let vinn_now = 1.65 - vdiff_now/2

  echo
  echo TEST_POINT
  echo INDEX
  print index
  echo VDIFF
  print vdiff_now
  echo VINP
  print vinp_now
  echo VINN
  print vinn_now


  alter V_VINP $&vinp_now
  alter V_VIN $&vinn_now


  * One complete ADC conversion
  tran 100p 1.30u 0 100p


  * Check conversion completed
  meas tran valid_max MAX v(valid) FROM=100n TO=1.30u


  * Read result after VALID
  meas tran c9v FIND v(C9) AT=1.28u
  meas tran c8v FIND v(C8) AT=1.28u
  meas tran c7v FIND v(C7) AT=1.28u
  meas tran c6v FIND v(C6) AT=1.28u
  meas tran c5v FIND v(C5) AT=1.28u
  meas tran c4v FIND v(C4) AT=1.28u
  meas tran c3v FIND v(C3) AT=1.28u
  meas tran c2v FIND v(C2) AT=1.28u
  meas tran c1v FIND v(C1) AT=1.28u
  meas tran c0v FIND v(C0) AT=1.28u


  * Decode 10-bit output
  let adc_code = 512*(c9v gt 0.6) + 256*(c8v gt 0.6) + 128*(c7v gt 0.6) + 64*(c6v gt 0.6) + 32*(c5v gt 0.6) + 16*(c4v gt 0.6) + 8*(c3v gt 0.6) + 4*(c2v gt 0.6) + 2*(c1v gt 0.6) + (c0v gt 0.6)

  let valid_ok = valid_max gt 0.6


  * Store results
  let code_vec[index] = adc_code
  let valid_vec[index] = valid_ok


  echo
  echo ADC_CODE
  print adc_code

  echo VALID_OK
  print valid_ok


  * Delete transient waveform to save memory
  destroy $curplot

  setplot const

  let index = index + 1

end


echo

echo BASIC_ADC_TEST_RESULTS

echo INPUTS
print vin_vec

echo CODES
print code_vec

echo VALID_FLAGS
print valid_vec


plot code_vec vs vin_vec pointplot


.endc
"
spice_ignore=true}
C {lab_pin.sym} 60 -250 0 0 {name=p1 sig_type=std_logic lab=RSTN}
C {lab_pin.sym} 60 -230 0 0 {name=p2 sig_type=std_logic lab=START}
C {lab_pin.sym} 60 -410 0 0 {name=V_VCM2 sig_type=std_logic lab=vrefp

}
C {lab_pin.sym} 60 -350 0 0 {name=p3 sig_type=std_logic lab=ainn}
C {lab_pin.sym} 60 -310 0 0 {name=p4 sig_type=std_logic lab=ainp}
C {lab_pin.sym} 60 -450 0 0 {name=V_VCM3 sig_type=std_logic lab=vcm

}
C {lab_pin.sym} 60 -210 0 0 {name=p5 sig_type=std_logic lab=CLK}
C {lab_pin.sym} 180 -540 0 0 {name=p6 sig_type=std_logic lab=vddh

}
C {lab_pin.sym} 240 -140 0 0 {name=p7 sig_type=std_logic lab=vss

}
C {opin.sym} 570 -445 0 0 {name=p125 lab=C1}
C {opin.sym} 570 -410 0 0 {name=p126 lab=C2}
C {opin.sym} 570 -370 0 0 {name=p127 lab=C3}
C {opin.sym} 570 -330 0 0 {name=p128 lab=C4}
C {opin.sym} 640 -445 0 0 {name=p129 lab=C5}
C {opin.sym} 640 -410 0 0 {name=p130 lab=C6}
C {opin.sym} 640 -370 0 0 {name=p131 lab=C7}
C {opin.sym} 640 -330 0 0 {name=p132 lab=C8}
C {opin.sym} 570 -480 0 0 {name=p133 lab=C0}
C {opin.sym} 640 -480 0 0 {name=p134 lab=C9}
C {opin.sym} 715 -480 0 0 {name=p135 lab=busy}
C {opin.sym} 715 -440 0 0 {name=p136 lab=valid}
C {lab_pin.sym} 420 -290 2 0 {name=p89 sig_type=std_logic lab=C9


}
C {lab_pin.sym} 420 -310 2 0 {name=p101 sig_type=std_logic lab=C8


}
C {lab_pin.sym} 420 -330 2 0 {name=p102 sig_type=std_logic lab=C7


}
C {lab_pin.sym} 420 -350 2 0 {name=p103 sig_type=std_logic lab=C6


}
C {lab_pin.sym} 420 -370 2 0 {name=p104 sig_type=std_logic lab=C5


}
C {lab_pin.sym} 420 -390 2 0 {name=p105 sig_type=std_logic lab=C4


}
C {lab_pin.sym} 420 -410 2 0 {name=p106 sig_type=std_logic lab=C3


}
C {lab_pin.sym} 420 -430 2 0 {name=p107 sig_type=std_logic lab=C2


}
C {lab_pin.sym} 420 -450 2 0 {name=p108 sig_type=std_logic lab=C1


}
C {lab_pin.sym} 420 -470 2 0 {name=p109 sig_type=std_logic lab=C0


}
C {iopin.sym} 585 -270 0 0 {name=p167 lab=Voutn}
C {lab_pin.sym} 420 -200 2 0 {name=p10 sig_type=std_logic lab=Voutn}
C {lab_pin.sym} 420 -230 2 0 {name=p115 sig_type=std_logic lab=busy
}
C {lab_pin.sym} 420 -250 2 0 {name=p116 sig_type=std_logic lab=valid}
C {title.sym} 160 0 0 0 {name=l1 author="Arjun Ananth"}
C {code_shown.sym} -500 145 0 0 {name=MODELS2 only_toplevel=true
format="tcleval( @value )"
value="
.lib /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOSlv.lib mos_tt
.lib /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOShv.lib mos_tt
.lib /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerRES.lib res_typ

.lib /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerCAP.lib cap_typ
.include /home/arjun/eda/pdks/IHP-Open-PDK/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/spice/sg13cmos5l_stdcell.spice
.include /home/arjun/eda/projects/SAR_ADC/circuit_files/src/sar_fsm/build/sar_fsm_wrapper_ihp.spice
"}
C {lab_pin.sym} 280 -540 0 0 {name=p11 sig_type=std_logic lab=vddl

}
C {vsource.sym} -230 -180 1 0 {name=VDD_SRC1 value="dc \{VDDL\}" savecurrent=false}
C {lab_pin.sym} -170 -180 1 0 {name=p12 sig_type=std_logic lab=vddl

}
C {code_shown.sym} 730 140 0 0 {name=s2 only_toplevel=false value="

.param VDDH=3.3
.param VDDL=1.2

.param VREF=3.3
.param VCM=1.65

.param NBITS=10
.param Cu=10f

* LSB = 3.3 / 1024 = 3.22265625 mV
.param VDIFF=0.001611328125


.options savecurrents
.options reltol=1e-4
.options abstol=1e-12
.options vntol=1e-6

.options method=gear
.options maxord=2

.options plotwinsize=0
.options itl4=500

.save v(vddh)
.save v(vddl)
.save v(vss)

.save v(CLK)
.save v(RSTN)
.save v(START)

.save v(ainp)
.save v(ainn)

.save v(vrefp)
.save v(vcm)

.save v(busy)
.save v(valid)

.save v(C9)
.save v(C8)
.save v(C7)
.save v(C6)
.save v(C5)
.save v(C4)
.save v(C3)
.save v(C2)
.save v(C1)
.save v(C0)

.save v(Voutn)

.save v(x1.sample)
.save v(x1.comp_clk)
.save v(x1.comp_lv)

.save v(x1.dbp9)
.save v(x1.dbp8)
.save v(x1.dbp7)
.save v(x1.dbp6)
.save v(x1.dbp5)
.save v(x1.dbp4)
.save v(x1.dbp3)
.save v(x1.dbp2)
.save v(x1.dbp1)
.save v(x1.dbp0)

.save v(x1.dbn9)
.save v(x1.dbn8)
.save v(x1.dbn7)
.save v(x1.dbn6)
.save v(x1.dbn5)
.save v(x1.dbn4)
.save v(x1.dbn3)
.save v(x1.dbn2)
.save v(x1.dbn1)
.save v(x1.dbn0)

.save v(x1.sample_hv)
.save v(x1.sampleb_hv)

.save v(x1.comp_clk_hv)

.save v(x1.dbp9_hv)
.save v(x1.dbp8_hv)
.save v(x1.dbp7_hv)
.save v(x1.dbp6_hv)
.save v(x1.dbp5_hv)
.save v(x1.dbp4_hv)
.save v(x1.dbp3_hv)
.save v(x1.dbp2_hv)
.save v(x1.dbp1_hv)
.save v(x1.dbp0_hv)

.save v(x1.dbn9_hv)
.save v(x1.dbn8_hv)
.save v(x1.dbn7_hv)
.save v(x1.dbn6_hv)
.save v(x1.dbn5_hv)
.save v(x1.dbn4_hv)
.save v(x1.dbn3_hv)
.save v(x1.dbn2_hv)
.save v(x1.dbn1_hv)
.save v(x1.dbn0_hv)

.save v(x1.vcp)
.save v(x1.vcn)

.save v(x1.Voutp)

.save v(x1.bp9)
.save v(x1.bp8)
.save v(x1.bp7)
.save v(x1.bp6)
.save v(x1.bp5)
.save v(x1.bp4)
.save v(x1.bp3)
.save v(x1.bp2)
.save v(x1.bp1)
.save v(x1.bp0)

.save v(x1.bn9)
.save v(x1.bn8)
.save v(x1.bn7)
.save v(x1.bn6)
.save v(x1.bn5)
.save v(x1.bn4)
.save v(x1.bn3)
.save v(x1.bn2)
.save v(x1.bn1)
.save v(x1.bn0)


.save v(x1.x26.enb)

.save v(x1.x26.gatep)
.save v(x1.x26.gaten)

.save v(x1.x26.q)
.save v(x1.x26.qb)

.save v(x1.x26.hbuf)
.save v(x1.x26.hbuf2)
.save v(x1.x26.lvbuf)

.save i(VDD_SRC)
.save i(VDD_SRC1)


"
spice_ignore=true}
C {code_shown.sym} 1090 140 0 0 {name=s3 only_toplevel=false value="

.param VDDH=3.3
.param VDDL=1.2

.param VREF=3.3
.param VCM=1.65

.param NBITS=10
.param Cu=10f

* LSB = 3.3 / 1024 = 3.22265625 mV
.param VDIFF=1.6


*.options savecurrents
.options reltol=1e-4
.options abstol=1e-12
.options vntol=1e-6

.options method=gear
.options maxord=2

.options plotwinsize=0
.options itl4=500

.save v(valid)

.save v(C9)
.save v(C8)
.save v(C7)
.save v(C6)
.save v(C5)
.save v(C4)
.save v(C3)
.save v(C2)
.save v(C1)
.save v(C0)

.save v(ainp)
.save v(ainn)

.save v(x1.sample)
.save v(x1.sample_hv)
.save v(x1.sampleb_hv)
.save v(x1.comp_clk_hv)

.save v(x1.vcp)
.save v(x1.vcn)

"}
C {code.sym} 1770 145 0 0 {name=s4
only_toplevel=true
value="
.control

set noaskquit
set num_threads=6

setplot const

let npts = 1025

let vin_vec = -1.65 + (3.3/1024)*vector(npts)
let code_vec = 0*vector(npts)
let valid_vec = 0*vector(npts)

let index = 0

echo
echo FULL_10_BIT_SAR_ADC_TRANSFER
echo 1025_INPUT_POINTS


repeat 1025

  let vdiff_now = vin_vec[index]

  let vinp_now = 1.65 + vdiff_now/2
  let vinn_now = 1.65 - vdiff_now/2


  echo
  echo POINT
  print index
  echo VDIFF
  print vdiff_now


  alter V_VINP $&vinp_now
  alter V_VIN  $&vinn_now


  tran 500p 1.30u 0 500p


  meas tran valid_max MAX v(valid) FROM=100n TO=1.30u

  meas tran c9v FIND v(C9) AT=1.28u
  meas tran c8v FIND v(C8) AT=1.28u
  meas tran c7v FIND v(C7) AT=1.28u
  meas tran c6v FIND v(C6) AT=1.28u
  meas tran c5v FIND v(C5) AT=1.28u
  meas tran c4v FIND v(C4) AT=1.28u
  meas tran c3v FIND v(C3) AT=1.28u
  meas tran c2v FIND v(C2) AT=1.28u
  meas tran c1v FIND v(C1) AT=1.28u
  meas tran c0v FIND v(C0) AT=1.28u


  let adc_code = 512*(c9v gt 0.6) + 256*(c8v gt 0.6) + 128*(c7v gt 0.6) + 64*(c6v gt 0.6) + 32*(c5v gt 0.6) + 16*(c4v gt 0.6) + 8*(c3v gt 0.6) + 4*(c2v gt 0.6) + 2*(c1v gt 0.6) + (c0v gt 0.6)

  let valid_ok = valid_max gt 0.6


  let code_vec[index] = adc_code
  let valid_vec[index] = valid_ok


  echo CODE
  print adc_code

  echo VALID
  print valid_ok


  destroy $curplot

  setplot const

  let index = index + 1

end


setplot const


echo
echo FULL_TRANSFER_COMPLETE

setscale code_vec vin_vec
setscale valid_vec vin_vec

set wr_singlescale
set wr_vecnames

option numdgt=10

wrdata adc_full_transfer.dat code_vec valid_vec


plot code_vec vs vin_vec linplot xlimit -1.65 1.65 ylimit 0 1023 xlabel VDIFF_V ylabel ADC_CODE title FULL_10_BIT_SAR_ADC_TRANSFER


echo
echo Results_written_to_adc_full_transfer.dat
echo

rusage

.endc
"
spice_ignore=true}
C {code.sym} 1670 495 0 0 {name=s5
only_toplevel=true
value="
.control
set noaskquit
set num_threads=6
set numdgt=12
set wr_singlescale
set wr_vecnames

setplot const

* Nine ideal code centers, including both endpoints.
let target = vector(9)
let target[0] = 0
let target[1] = 128
let target[2] = 256
let target[3] = 384
let target[4] = 512
let target[5] = 640
let target[6] = 768
let target[7] = 896
let target[8] = 1023

let vin_vec = 0*vector(9)
let code_vec = -1 + 0*vector(9)
let err_vec = 0*vector(9)
let acq_ns_vec = -1 + 0*vector(9)
let valid_ns_vec = -1 + 0*vector(9)
let pass_vec = 0*vector(9)

let idx = 0
let passed = 0
let previous_code = -1

echo NINE_POINT_ADC_SMOKE_TEST
echo Acceptance: code_error_within_1_and_acquisition_158_to_162_ns
echo Endpoints_must_produce_0_and_1023

repeat 9

    setplot const

    let expected = target[idx]
    let vin_now = -1.65 + (expected + 0.5)*(3.3/1024)
    let vinp_now = 1.65 + vin_now/2
    let vinn_now = 1.65 - vin_now/2
    let vin_vec[idx] = vin_now

    let measured_code = -1
    let measured_valid = -1
    let measured_acq = -1

    alter V_VINP $&vinp_now
    alter V_VIN $&vinn_now

    * Current conversion completes near 1.290 us.
    * Stop at 1.40 us to avoid unnecessary idle simulation.
    tran 100p 1.40u 0 100p uic

    if length(time) > 1
        let last_time = time[length(time)-1]

        if last_time >= 1.399e-6

            let t_on = -1
            let t_off = -1
            let t_valid = -1

            meas tran t_on WHEN v(x1.sample_hv)=1.65 RISE=1 TD=100n
            meas tran t_off WHEN v(x1.sample_hv)=1.65 FALL=1 TD=100n
            meas tran t_valid WHEN v(valid)=0.6 RISE=1 TD=100n

            if t_on > 0
                if t_off > t_on
                    let const.measured_acq = (t_off - t_on)*1e9

                    if t_valid > t_off
                        let t_read = t_valid + 5n

                        if t_read < last_time
                            let code_wave = 512*(v(C9) gt 0.6) + 256*(v(C8) gt 0.6) + 128*(v(C7) gt 0.6) + 64*(v(C6) gt 0.6) + 32*(v(C5) gt 0.6) + 16*(v(C4) gt 0.6) + 8*(v(C3) gt 0.6) + 4*(v(C2) gt 0.6) + 2*(v(C1) gt 0.6) + (v(C0) gt 0.6)
                            let adc_code = -1
                            meas tran adc_code FIND code_wave AT=$&t_read
                            let const.measured_code = adc_code
                            let const.measured_valid = t_valid*1e9
                        end
                    end
                end
            end
        end
    end

    destroy $curplot
    setplot const

    let code_vec[idx] = measured_code
    let acq_ns_vec[idx] = measured_acq
    let valid_ns_vec[idx] = measured_valid
    let point_ok = 0

    if measured_code >= 0
        if measured_code <= 1023
            let actual = floor(measured_code + 0.5)
            let error = actual - expected
            let err_vec[idx] = error

            if abs(error) <= 1
                if measured_acq >= 158
                    if measured_acq <= 162
                        if measured_valid > 0
                            let point_ok = 1
                        end
                    end
                end
            end

            * Require strictly increasing outputs at these widely spaced inputs.
            if previous_code >= 0
                if actual <= previous_code
                    let point_ok = 0
                end
            end
            let previous_code = actual

            * Explicit endpoint reachability checks.
            if idx == 0
                if actual != 0
                    let point_ok = 0
                end
            end

            if idx == 8
                if actual != 1023
                    let point_ok = 0
                end
            end

            echo RESULT $&idx VIN $&vin_now EXPECTED $&expected ACTUAL $&actual ERROR $&error
        end
    else
        echo CONVERSION_FAILED_AT_POINT $&idx
    end

    let pass_vec[idx] = point_ok
    let passed = passed + point_ok

    echo ACQUISITION_NS $&measured_acq VALID_NS $&measured_valid POINT_PASS $&point_ok

    * Save progress after every conversion.
    * Rows with code=-1 have no valid result.
    setscale vin_vec
    wrdata adc_smoke_results.dat target code_vec err_vec acq_ns_vec valid_ns_vec pass_vec

    let idx = idx + 1

end

echo
echo SMOKE_TEST_SUMMARY
print passed

if passed == 9
    echo PASS_BASIC_OPERATION_AT_ALL_NINE_TEST_POINTS
else
    echo FAIL_ONE_OR_MORE_SMOKE_TEST_CHECKS
end

echo This_test_does_not_establish_DNL_INL_ENOB_or_no_missing_codes.

plot code_vec vs vin_vec
plot err_vec vs vin_vec

.endc

"
}
