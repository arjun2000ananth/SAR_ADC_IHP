crashbackups stop
drc off
gds read /home/arjun/eda/projects/SAR_ADC/circuit_files/src/sar_fsm/build/physical/gds/sar_fsm_wrapper.gds
if {[lsearch [cellname list topcells] {sar_fsm_wrapper}] < 0} {
    set _fp [open {/home/arjun/eda/projects/SAR_ADC/circuit_files/src/sar_fsm/build/physical/pex/pex_sar_fsm_wrapper.cellmismatch} w]
    puts $_fp [cellname list topcells]
    close $_fp
    quit -noprompt
}
load sar_fsm_wrapper
select top cell
flatten sar_fsm_wrapper_flat
load sar_fsm_wrapper_flat
cellname delete sar_fsm_wrapper
cellname rename sar_fsm_wrapper_flat sar_fsm_wrapper
select top cell
extract path /home/arjun/eda/projects/SAR_ADC/circuit_files/src/sar_fsm/build/physical/pex
ext2spice lvs
extresist threshold 10000
extresist mindelay 1
extresist minres 1000
extract do resistance
extract do unique
extract all
ext2spice extresist on
ext2spice cthresh 0.01
ext2spice -p /home/arjun/eda/projects/SAR_ADC/circuit_files/src/sar_fsm/build/physical/pex -o /home/arjun/eda/projects/SAR_ADC/circuit_files/src/sar_fsm/build/physical/pex/sar_fsm_wrapper.pex.spice.tmp
quit -noprompt
