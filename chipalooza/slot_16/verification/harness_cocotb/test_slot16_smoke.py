
import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from harness import (reset, REG, proj_config, IN_ROUTE_BASE, OUT_ROUTE_BASE, ROUTE_PIN_0, ROUTE_CONST_0,
                     ROUTE_CONST_1, ROUTE_SPECIAL, CMD_DIG_RESET, isnan, drive_pad)

SLOT = 16
IDX = SLOT - 1              # user index; bit IDX of the 18-bit per-slot vectors
SETTLE = 200
ADC_OUT = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "busy", "valid"]   # dig_out[0..11]


async def select16(spi, **cfg):
    await spi.write_reg(REG["proj_sel"], SLOT)
    await spi.write_reg(REG["proj_config"], proj_config(**cfg))
    await Timer(SETTLE, unit="ns")


def bit(vec_handle, i):
    return (int(vec_handle.value) >> i) & 1


def slot16_dig_in(dut):
    return (int(dut.user_dig_in.value) >> (IDX * 24)) & 0xFFFFFF


@cocotb.test()
async def test_slot16_select_enable_and_power(dut):
    """proj_sel = 16 enables slot 16 only; its 3.3 V / 1.2 V gates deliver power to slot 16 only."""
    spi = await reset(dut)
    await select16(spi, proj_ena=1, pwr_3v3=1, pwr_1v2=1)
    assert await spi.read_reg(REG["proj_sel"]) == SLOT
    for name in ("user_ena", "user_3v3_ena", "user_1v2_ena"):
        v = int(getattr(dut, name).value)
        assert v == 1 << IDX, f"{name} = {v:018b}, expected only slot 16 (bit {IDX})"
    for i in range(18):
        avdd, dvdd = float(dut.user_avdd[i].value), float(dut.user_dvdd[i].value)
        if i == IDX:
            assert abs(avdd - 3.3) < 1e-6 and abs(dvdd - 1.2) < 1e-6, (avdd, dvdd)
        else:
            assert isnan(avdd) and isnan(dvdd), f"slot {i + 1} powered: {avdd}, {dvdd}"
    dut._log.info("slot 16: enable, vdd_3v3 = %.2f V, vdd_1v2 = %.2f V", float(dut.user_avdd[IDX].value),
                  float(dut.user_dvdd[IDX].value))


@cocotb.test()
async def test_slot16_clock_is_gated_through(dut):
    """The slot-16 clock (-> ADC CLK) follows clk_in when selected; the other 17 stay low; it stops on deselect."""
    spi = await reset(dut)
    cocotb.start_soon(Clock(dut.clk_in, 20, unit="ns").start())
    await select16(spi, proj_ena=1)
    highs = 0; others = 0
    for _ in range(20):
        await RisingEdge(dut.clk_in); await Timer(2, unit="ns")
        highs += bit(dut.user_clk, IDX); others |= int(dut.user_clk.value) & ~(1 << IDX)
        await FallingEdge(dut.clk_in); await Timer(2, unit="ns")
        assert bit(dut.user_clk, IDX) == 0
    assert highs == 20 and others == 0, (highs, others)
    await spi.write_reg(REG["proj_sel"], 1)
    for _ in range(4):
        await RisingEdge(dut.clk_in)
    await Timer(2, unit="ns")
    assert bit(dut.user_clk, IDX) == 0, "slot-16 clock kept running after deselect"


@cocotb.test()
async def test_slot16_start_rstn_from_pads_and_constants(dut):
    """dig_in[0] (START) and dig_in[1] (RSTN) reach slot 16 from pads 0/1 and from the SPI constants."""
    spi = await reset(dut)
    await select16(spi, proj_ena=1, dig_ena=1)
    nib = [ROUTE_CONST_0] * 24
    nib[0], nib[1] = ROUTE_PIN_0 + 0, ROUTE_PIN_0 + 1          # START <- pad 0, RSTN <- pad 1
    await spi.write_regs(IN_ROUTE_BASE, nib)
    for pads in (0b00, 0b01, 0b10, 0b11):
        dut.gpio_in.value = pads
        await Timer(SETTLE, unit="ns")
        got = slot16_dig_in(dut) & 0b11
        assert got == pads, f"pads {pads:02b} -> slot16 dig_in[1:0] = {got:02b}"
    # constants (START held high, RSTN high = run): the bring-up protocol
    nib[0], nib[1] = ROUTE_CONST_1, ROUTE_CONST_1
    await spi.write_regs(IN_ROUTE_BASE, nib)
    await Timer(SETTLE, unit="ns")
    assert slot16_dig_in(dut) == 0b11, f"{slot16_dig_in(dut):024b}"
    nib[1] = ROUTE_CONST_0                                     # RSTN low = ADC in reset
    await spi.write_regs(IN_ROUTE_BASE, nib)
    await Timer(SETTLE, unit="ns")
    assert slot16_dig_in(dut) == 0b01


@cocotb.test()
async def test_slot16_start_from_the_sequencer_is_clock_synchronous(dut):
    """dig_in[0] (START) can come from the sequencer (route code 0xF), which runs on the same master clock."""
    spi = await reset(dut)
    cocotb.start_soon(Clock(dut.clk_in, 20, unit="ns").start())
    await select16(spi, proj_ena=1, dig_ena=1)
    nib = [ROUTE_CONST_0] * 24
    nib[0] = ROUTE_SPECIAL                                      # seq_out[0] -> START
    nib[1] = ROUTE_CONST_1                                      # RSTN high
    await spi.write_regs(IN_ROUTE_BASE, nib)
    await spi.write_reg(REG["seq_mode"], 6)                     # constant one
    await spi.write_reg(REG["seq_prescaler"], 0)
    await spi.command(0x01)                                     # CMD_SEQ_LOOP
    for _ in range(8):
        await RisingEdge(dut.clk_in)
    await Timer(SETTLE, unit="ns")
    assert slot16_dig_in(dut) & 0b11 == 0b11, f"{slot16_dig_in(dut):024b}"
    await spi.command(0x03)                                     # CMD_SEQ_STOP -> seq_out cleared
    await Timer(SETTLE, unit="ns")
    assert slot16_dig_in(dut) & 0b11 == 0b10


@cocotb.test()
async def test_slot16_harness_reset_reaches_slot16(dut):
    """The harness 'reset' (active high, synchronised) reaches slot 16 only.  (Unused by the ADC: RSTN is dig_in[1].)"""
    spi = await reset(dut)
    cocotb.start_soon(Clock(dut.clk_in, 20, unit="ns").start())
    await select16(spi, proj_ena=1)
    await spi.start(); await spi.write_byte(CMD_DIG_RESET)
    for _ in range(4):
        await RisingEdge(dut.clk_in)
    await Timer(2, unit="ns")
    assert int(dut.user_reset.value) == 1 << IDX, f"user_reset = {int(dut.user_reset.value):018b}"
    await spi.end()


@cocotb.test()
async def test_slot16_reference_buses(dut):
    """analog_bus0 (-> vrefp) and analog_bus1 (-> vcm) reach slot 16 from shared pads 0/1 only when enabled."""
    spi = await reset(dut)
    drive_pad(dut, 0, 3.3)          # vrefp source on shared analog pin 0
    drive_pad(dut, 1, 1.65)         # vcm source on shared analog pin 1
    await select16(spi, proj_ena=1, analog_bus=0b0011)
    got = [float(dut.user_analog[IDX * 4 + k].value) for k in range(4)]
    assert abs(got[0] - 3.3) < 1e-6 and abs(got[1] - 1.65) < 1e-6, got
    assert isnan(got[2]) and isnan(got[3]), got
    for other in range(18):
        if other != IDX:
            assert all(isnan(float(dut.user_analog[other * 4 + k].value)) for k in range(4)), f"slot {other + 1}"
    await select16(spi, proj_ena=1, analog_bus=0)
    assert all(isnan(float(dut.user_analog[IDX * 4 + k].value)) for k in range(4))
    dut._log.info("slot 16: analog_bus0 = %.2f V (vrefp), analog_bus1 = %.2f V (vcm)", *got[:2])


@cocotb.test()
async def test_slot16_outputs_reach_pads_and_spi(dut):
    """Behavioural stand-in for C0..C9/busy/valid on slot-16 dig_out[0..11] -> daisy chain -> router -> pads and
    the SPI readback registers 0x38/0x39.  Walking one: every output bit lands on its own pad, nowhere else."""
    spi = await reset(dut)
    await select16(spi, proj_ena=1, dig_ena=1)
    await spi.write_regs(OUT_ROUTE_BASE, list(range(12)))       # identity: dig_out[j] -> pad j
    ctrl_out = dut.left_slot[IDX].ctrl.proj_dig_out
    for j in range(12):
        ctrl_out.value = Force(1 << j)
        await Timer(SETTLE, unit="ns")
        io_out, io_oe = int(dut.hk_top.io_out.value), int(dut.hk_top.io_oe.value)
        gpio = int(dut.gpio_out.value)
        lo, hi = await spi.read_regs(0x38, 2)
        sampled = lo | ((hi & 0xF) << 8)
        assert io_oe == 0xFFF, f"io_oe = {io_oe:03x}"
        assert io_out == 1 << j and gpio == 1 << j, f"{ADC_OUT[j]} (dig_out[{j}]): io_out={io_out:03x} gpio={gpio:03x}"
        assert sampled == 1 << j, f"{ADC_OUT[j]}: SPI 0x38/0x39 = {sampled:03x}"
    ctrl_out.value = Release()
    # deselected (address 0 = diagnostic, matches no slot, so every slot relays the zero seed):
    # slot 16's outputs must no longer reach the bus.  (Selecting another real slot instead would put THAT slot's
    # undriven template outputs on the bus, which is X by design of the empty wrappers, not a harness fault.)
    ctrl_out.value = Force(0xFFF)
    await spi.write_reg(REG["proj_sel"], 0)
    await Timer(SETTLE, unit="ns")
    assert int(dut.hk_top.io_out.value) == 0, "slot 16 outputs leak onto the bus while deselected"
    ctrl_out.value = Release()
