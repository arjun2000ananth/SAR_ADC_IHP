"""
configuration for the SAR ADC Python testbench.

Edit this file (or copy it and pass --config my_config.py).
Every value here can also be overridden from the command line with
    --set NAME=VALUE        e.g.  --set VDD=3.0 --set CORNER=ss
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))


# Tools / PDK

NGSPICE = os.environ.get("NGSPICE", "ngspice")
PDK_ROOT = os.environ.get("PDK_ROOT", "/foss/pdks")
PDK = os.environ.get("PDK", "ihp-sg13cmos5l")

# OSDI model libraries (PSP103 etc.).
#   "auto"  load them with pre_osdi unless a .spiceinit (cwd or $HOME) already does
#   []      never load (your .spiceinit does it)
#   [paths] always load exactly these
OSDI = "auto"
OSDI_DIR = "{PDK_ROOT}/{PDK}/libs.tech/ngspice/osdi"
OSDI_FILES = ["psp103.osdi", "psp103_nqs.osdi", "r3_cmc.osdi", "mosvar.osdi"]

# Model libraries: {corner} is replaced by CORNER (tt, ss, ff, sf, fs).
MODEL_LIBS = [
    ("{PDK_ROOT}/{PDK}/libs.tech/ngspice/models/cornerMOSlv.lib", "mos_{corner}"),
    ("{PDK_ROOT}/{PDK}/libs.tech/ngspice/models/cornerMOShv.lib", "mos_{corner}"),
    ("{PDK_ROOT}/{PDK}/libs.tech/ngspice/models/cornerRES.lib", "res_typ"),
]
STDCELL_SPICE = "{PDK_ROOT}/{PDK}/libs.ref/sg13cmos5l_stdcell/spice/sg13cmos5l_stdcell.spice"
STDCELL_LIB = "{PDK_ROOT}/{PDK}/libs.ref/sg13cmos5l_stdcell/lib/sg13cmos5l_stdcell_typ_1p20V_25C.lib"


# Design netlists

# Files searched for .subckt definitions, in priority order (first definition wins).
NETLISTS = [
    "{HERE}/netlists/sar_10_bit_tb.spice",       # has .subckt sar_10_bit + all its blocks
    "{HERE}/netlists/sar_10_bit.spice",
    "{HERE}/netlists/strong_arm_comp.spice",
    "{HERE}/netlists/simple_comparator.spice",
    "{HERE}/netlists/level_shifter_1v2_to_3v3.spice",
    "{HERE}/netlists/capDrivers.spice",
    "{HERE}/netlists/DFF_array2.spice",
]
# Gate-level SAR FSM (Yosys  spice).  REQUIRED for the fsm / adc_* benches.
FSM_NETLIST = "{HERE}/netlists/sar_fsm_wrapper_ihp.spice"
# `.include` lines inside the netlists are resolved by basename through this map
INCLUDE_MAP = {"sar_fsm_wrapper_ihp.spice": "{FSM_NETLIST}"}


# PVT

CORNER = "tt"
TEMP = 27.0


# Electrical operating point (matches sar_10_bit_tb.spice)

VDD = 3.3          # analog + FSM supply (hv devices)
VDD_LV = 1.2       # 1.2 V core supply (level shifter input side, capDrivers)
VREFP = 3.3        # CDAC reference (tied to VDD in the original tb)
VCM = 1.65         # CDAC common mode / input common mode
CU = 10e-15        # CDAC unit capacitor (.param Cu)
NBITS = 10
# Differential full-scale range (peak-to-peak).  None  2*(VREFP-VCM)
VFS_DIFF = None


# Clocks / ADC control (matches sar_10_bit_tb.spice)

FCLK = 50e6              # CLK frequency
T_EDGE = 20e-12          # rise/fall of ideal digital sources
T_RSTN = 60e-9           # RSTN released at this time
START_PHASE = 0.5        # START rises this fraction of a CLK period after a CLK rising edge
START_WIDTH_CLK = 1      # START pulse width in CLK periods
CONV_PERIOD_CLK = None   # CLK periods per conversion (fs = FCLK/this). None  from adc_timing probe
FS_TARGET = 1e6          # target sample rate (only used for pass/fail reporting)
READ_DELAY = 5e-9        # read C9..C0 this long after `valid` rises
T_SAMPLE = None          # sampling-window length for block benches; None  measured by adc_timing

# ADC top-level port order of the sar_10_bit subckt is taken from the netlist;
# these are the internal nodes of sar_10_bit used for debug/timing:
# voltage domains
# The FSM is made of sg13cmos5l std-cells (1.2 V devices); everything else is 3.3 V.
#   FSM_DOMAIN = "lv": FSM on VDD_LV; CLK/RSTN/START and C*/valid/busy swing 0..VDD_LV
#   FSM_DOMAIN = "hv": FSM on VDD exactly as sar_10_bit.spice is drawn (sim only)
FSM_DOMAIN = "lv"
#   ADC_TOP_MODE = "auto": if sar_10_bit has a 1.2 V supply port (see LV_PORT_NAMES) it is used
#                          as drawn; otherwise the testbench builds sar_10_bit_lv = sar_10_bit with
#                          the FSM on VDD_LV, LS_UP_SUBCKT on every FSManalog net and
#                          LS_DOWN_SUBCKT on the comparator output into the FSM
#   ADC_TOP_MODE = "as_drawn" / "generate": force one of the two
ADC_TOP_MODE = "auto"
LS_UP_SUBCKT = "level_shifter_1v2_to_3v3"
LS_DOWN_SUBCKT = None     # None  testbench-generated thick-oxide buffer on VDD_LV
# Level shifters in the long runs (adc_static / adc_dynamic, with FSM_MODEL="xspice"):
#   "xspice": done inside the FSM's XSPICE bridges (0..VDD outputs + fixed delay)  ~3x faster
#   "spice" : the transistor-level shifters (adc_timing and fsm always use these)
LS_MODEL = "xspice"
LS_UP_DELAY = None        # None  in-situ value measured by adc_timing (else 0.7 ns)
LS_DOWN_DELAY = None      # None  in-situ value measured by adc_timing (else 0.25 ns)
LV_PORT_NAMES = ["vdd_lv", "vddl", "vdd1v2", "vdd_1v2", "dvdd", "vdd_dig", "vccd", "vddd"]
# top-level control ports of sar_10_bit
ADC_PORTS = {"clk": "CLK", "rstn": "RSTN", "start": "START", "valid": "valid", "busy": "busy"}

ADC_SUBCKT = "sar_10_bit"
COMP_SUBCKT = "strong_arm_comp"   # comparator inside sar_10_bit (loads the CDAC in block benches)
FSM_SUBCKT = "sar_fsm_wrapper"
ADC_INTERNAL = {"sample": "sample", "comp_clk": "comp_clk", "vcp": "vcp", "vcn": "vcn",
                "voutp": "Voutp"}
# Output code bits: MSB first
CODE_BITS = ["C9", "C8", "C7", "C6", "C5", "C4", "C3", "C2", "C1", "C0"]


# Simulation settings

SPICE_OPTIONS = "reltol=1e-4 abstol=1e-12 vntol=1e-6 method=gear maxord=2"
ADC_TSTEP = 200e-12      # max internal timestep for full-ADC runs. Checked against 50 ps:
                         # top-plate voltage at comparator edges differs by < 0.01 LSB, 3x faster
ADC_SAVE_STEP = 0.5e-9   # tstep of the .tran card for full-ADC runs
# How the gate-level FSM is simulated in the long ADC runs (adc_static / adc_dynamic):
#   "xspice": logic-equivalent XSPICE digital model generated from your netlist + Liberty
#             (~10-50x faster; comparator/switches/CDAC stay transistor level)
#   "spice" : the std-cell transistors (slow: ~3000 PSP devices)
# adc_timing and fsm always run the transistor-level FSM as well.
FSM_MODEL = "xspice"
XSPICE_GATE_DELAY = 50e-12   # per-gate delay in the XSPICE model
XSPICE_CLK2Q = 100e-12
XSPICE_TRF = 100e-12         # rise/fall of FSM outputs (dac_bridge)
ADC_CHUNK = 16           # conversions per ngspice process
ADC_WARMUP = 1           # dummy conversions at the start of every chunk
JOBS = os.cpu_count() or 4
RESULTS_DIR = "{HERE}/results"
KEEP_RUNS = True         # keep decks/logs/raw data under results/<bench>/runs


# Specs used for hard PASS/FAIL. LSB-relative ones are in LSB.

SPEC = {
    # comparator
    "comp_offset_lsb": 0.5,          # |systematic offset| < 0.5 LSB
    "comp_delay_max": 5e-9,          # CLKdecision delay at 0.5 LSB input
    "comp_mc_sigma_lsb": 0.5,        # 1-sigma offset from mismatch MC
    # sampling switch
    "sh_settle_lsb": 0.5,            # tracking error at end of sampling window
    "sh_sndr_db": 68.0,              # S/H alone (>= 10-bit + ~6 dB margin)
    # DAC / CDAC
    "cdac_settle_lsb": 0.5,          # top-plate error at the end of the bit cycle
    "cdac_weight_err_lsb": 0.25,     # |bit weight error| (schematic  parasitics only)
    # ADC static
    "dnl_lsb": 0.5,
    "inl_lsb": 1.0,
    # ADC dynamic
    "sndr_db": 56.0,
    "enob": 9.0,
    "sfdr_db": 65.0,
    # level shifter
    "ls_delay_max": 2e-9,
}
