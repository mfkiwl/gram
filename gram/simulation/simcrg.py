# This file is Copyright (c) 2020 LambdaConcept <contact@lambdaconcept.com>

from nmigen import *
from nmigen.cli import main
from nmigen.lib.cdc import ResetSynchronizer

class PLL(Elaboratable):
    def __init__(self, clkin, clksel=Signal(shape=2, reset=2), clkout1=Signal(), clkout2=Signal(), clkout3=Signal(), clkout4=Signal(), lock=Signal(), CLKI_DIV=1, CLKFB_DIV=1, CLK1_DIV=3, CLK2_DIV=4, CLK3_DIV=5, CLK4_DIV=6):
        self.clkin = clkin
        self.clkout1 = clkout1
        self.clkout2 = clkout2
        self.clkout3 = clkout3
        self.clkout4 = clkout4
        self.clksel = clksel
        self.lock = lock
        self.CLKI_DIV = CLKI_DIV
        self.CLKFB_DIV = CLKFB_DIV
        self.CLKOP_DIV = CLK1_DIV
        self.CLKOS_DIV = CLK2_DIV
        self.CLKOS2_DIV = CLK3_DIV
        self.CLKOS3_DIV = CLK4_DIV
        self.ports = [
            self.clkin,
            self.clkout1,
            self.clkout2,
            self.clkout3,
            self.clkout4,
            self.clksel,
            self.lock,
        ]

    def elaborate(self, platform):
        clkfb = Signal()
        pll = Instance("EHXPLLL",
                       p_PLLRST_ENA='DISABLED',
                       p_INTFB_WAKE='DISABLED',
                       p_STDBY_ENABLE='DISABLED',
                       p_CLKOP_FPHASE=0,
                       p_CLKOP_CPHASE=1,
                       p_OUTDIVIDER_MUXA='DIVA',
                       p_CLKOP_ENABLE='ENABLED',
                       p_CLKOP_DIV=self.CLKOP_DIV,
                       p_CLKOS_DIV=self.CLKOS_DIV,
                       p_CLKOS2_DIV=self.CLKOS2_DIV,
                       p_CLKOS3_DIV=self.CLKOS3_DIV,
                       p_CLKFB_DIV=self.CLKFB_DIV,
                       p_CLKI_DIV=self.CLKI_DIV,
                       p_FEEDBK_PATH='CLKOP',
                       #p_FREQUENCY_PIN_CLKOP='200',
                       i_CLKI=self.clkin,
                       #i_CLKFB=clkfb,
                       i_RST=0,
                       i_STDBY=0,
                       i_PHASESEL0=0,
                       i_PHASESEL1=0,
                       i_PHASEDIR=0,
                       i_PHASESTEP=0,
                       i_PLLWAKESYNC=0,
                       i_ENCLKOP=0,
                       i_ENCLKOS=0,
                       i_ENCLKOS2=0,
                       i_ENCLKOS3=0,
                       o_CLKOP=self.clkout1,
                       o_CLKOS=self.clkout2,
                       o_CLKOS2=self.clkout3,
                       o_CLKOS3=self.clkout4,
                       o_LOCK=self.lock,
                       )
        m = Module()
        m.submodules += pll
        with m.If(self.clksel == 0):
            m.d.comb += clkfb.eq(self.clkout1)
        with m.Elif(self.clksel == 1):
            m.d.comb += clkfb.eq(self.clkout2)
        with m.Elif(self.clksel == 2):
            m.d.comb += clkfb.eq(self.clkout3)
        with m.Else():
            m.d.comb += clkfb.eq(self.clkout4)
        return m


class ECPIX5CRG(Elaboratable):
    def __init__(self):
        self.clkin = Signal()

    def elaborate(self, platform):
        m = Module()

        # Get 100Mhz from oscillator
        cd_rawclk = ClockDomain("rawclk", local=True, reset_less=True)
        m.d.comb += cd_rawclk.clk.eq(self.clkin)
        m.domains += cd_rawclk

        # Power-on delay (655us)
        podcnt = Signal(16, reset=2**16-1)
        pod_done = Signal()
        with m.If(podcnt != 0):
            m.d.rawclk += podcnt.eq(podcnt-1)
        m.d.comb += pod_done.eq(podcnt == 0)

        # Generating sync2x (200Mhz) and init (25Mhz) from clk100
        cd_sync2x = ClockDomain("sync2x", local=False)
        cd_sync2x_unbuf = ClockDomain("sync2x_unbuf", local=True, reset_less=True)
        cd_init = ClockDomain("init", local=False)
        cd_sync = ClockDomain("sync", local=False, reset_less=True)
        cd_dramsync = ClockDomain("dramsync", local=False)
        m.submodules.pll = pll = PLL(ClockSignal("rawclk"), CLKI_DIV=1, CLKFB_DIV=2, CLK1_DIV=2, CLK2_DIV=16, CLK3_DIV=4,
            clkout1=ClockSignal("sync2x_unbuf"), clkout2=ClockSignal("init"))
        m.submodules += Instance("ECLKSYNCB",
                i_ECLKI = ClockSignal("sync2x_unbuf"),
                i_STOP  = 0,
                o_ECLKO = ClockSignal("sync2x"))
        m.domains += cd_sync2x_unbuf
        m.domains += cd_sync2x
        m.domains += cd_init
        m.domains += cd_sync
        m.domains += cd_dramsync
        m.d.comb += ResetSignal("init").eq(~pll.lock|~pod_done)
        m.d.comb += ResetSignal("dramsync").eq(~pll.lock|~pod_done)

        # Generating sync (100Mhz) from sync2x
        
        m.submodules += Instance("CLKDIVF",
            p_DIV="2.0",
            i_ALIGNWD=0,
            i_CLKI=ClockSignal("sync2x"),
            i_RST=0,
            o_CDIVX=ClockSignal("sync"))
        m.d.comb += ClockSignal("dramsync").eq(ClockSignal("sync"))

        return m

class SimCRGTop(Elaboratable):
    def __init__(self):
        self.clkin = Signal()

        self.sync2x = Signal()
        self.sync = Signal()
        self.dramsync = Signal()
        self.init = Signal()

    def elaborate(self, platform):
        m = Module()

        m.submodules.crg = crg = ECPIX5CRG()
        m.d.comb += [
            crg.clkin.eq(self.clkin),
            self.sync2x.eq(ClockSignal("sync2x")),
            self.sync.eq(ClockSignal("sync")),
            self.dramsync.eq(ClockSignal("dramsync")),
            self.init.eq(ClockSignal("init")),
        ]

        return m


if __name__ == "__main__":
    top = SimCRGTop()
    main(top, name="simcrgtop", ports=[top.clkin, top.sync, top.sync2x, top.dramsync, top.init])
