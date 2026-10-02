
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
import harness as H

SLOT = 16                         # 1-based; user index 15 -> left_slot[15]


def v(h):
    try:
        return str(h.value)
    except Exception as e:                                   # noqa: BLE001
        return f"<{e}>"


@cocotb.test()
async def diag_slot16_cells(dut):
    spi = await H.reset(dut)
    cocotb.start_soon(Clock(dut.clk_in, 20, unit="ns").start())
    await spi.write_reg(H.REG["proj_sel"], SLOT)
    await H.set_dbus_pattern(spi, 0xA5A5A5)
    await spi.write_reg(H.REG["proj_config"], H.proj_config(proj_ena=1, dig_ena=1))
    for _ in range(4):
        await RisingEdge(dut.clk_in)
    await Timer(5, unit="ns")
    ctrl = dut.left_slot[SLOT - 1].ctrl
    cg = ctrl.clockgate
    lat = ctrl.dig_in_gen[0].dig_in_latch
    dut._log.info("proj_sel readback = %d", await spi.read_reg(H.REG["proj_sel"]))
    for name, h in (("lgcp_1.CLK", cg.CLK), ("lgcp_1.GATE (select)", cg.GATE), ("lgcp_1.delayed_CLK", cg.delayed_CLK),
                    ("lgcp_1.delayed_GATE", cg.delayed_GATE), ("lgcp_1.GCLK", cg.GCLK),
                    ("dlhrq_1.D", lat.D), ("dlhrq_1.GATE (dig_ena)", lat.GATE), ("dlhrq_1.RESET_B (select)", lat.RESET_B),
                    ("dlhrq_1.delayed_D", lat.delayed_D), ("dlhrq_1.delayed_GATE", lat.delayed_GATE),
                    ("dlhrq_1.delayed_RESET_B", lat.delayed_RESET_B), ("dlhrq_1.Q", lat.Q),
                    ("user_ena (18 slots)", dut.user_ena), ("user_clk (18 slots)", dut.user_clk)):
        dut._log.info("DIAG %-28s = %s", name, v(h))
