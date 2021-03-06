#nmigen: UnusedElaboratable=no

from nmigen import *
from lambdasoc.periph import Peripheral

from gram.test.utils import *

from gram.common import gramNativePort
from gram.frontend.wishbone import gramWishbone

class FakeGramCrossbar:
    def __init__(self):
        self.port = gramNativePort("both", 3, 128)

    def get_native_port(self):
        return self.port

class FakeGramCore:
    def __init__(self):
        self.crossbar = FakeGramCrossbar()
        self.size = 2**3*128//8

class GramWishboneTestCase(FHDLTestCase):
    def read_request(self, *, bus, native_port, adr, sel, reference_value, timeout=128, ackCallback=None):
        # Send a read request
        yield bus.adr.eq(adr)
        yield bus.stb.eq(1)
        yield bus.cyc.eq(1)
        yield bus.sel.eq(sel)
        yield bus.we.eq(0)
        yield

        # Answer cmd
        yield native_port.cmd.ready.eq(1)
        yield

        # Answer rdata
        yield native_port.rdata.data.eq(reference_value)
        yield native_port.rdata.valid.eq(1)
        yield

        while not (yield bus.ack):
            timeout -= 1
            yield
            self.assertTrue(timeout > 0)

        if ackCallback is not None:
            yield from ackCallback(bus, native_port)
        res = yield bus.dat_r

        yield bus.stb.eq(0)
        yield bus.cyc.eq(0)
        yield native_port.rdata.valid.eq(0)
        yield

        return res

    def write_request(self, *, bus, native_port, adr, sel, value, timeout=128, ackCallback=None):
        # Send a write request
        yield bus.adr.eq(adr)
        yield bus.stb.eq(1)
        yield bus.cyc.eq(1)
        yield bus.sel.eq(sel)
        yield bus.we.eq(1)
        yield bus.dat_w.eq(value)
        yield

        # Answer cmd
        yield native_port.cmd.ready.eq(1)
        yield

        # Answer wdata
        yield native_port.wdata.ready.eq(1)

        while not (yield bus.ack):
            timeout -= 1
            yield
            self.assertTrue(timeout > 0)

        if ackCallback is not None:
            yield from ackCallback(bus, native_port)
        res = yield native_port.wdata.data

        yield bus.stb.eq(0)
        yield bus.cyc.eq(0)
        yield native_port.wdata.ready.eq(0)
        yield

        return res

    def read_test(self, *, data_width, granularity):
        core = FakeGramCore()
        native_port = core.crossbar.get_native_port()
        dut = gramWishbone(core, data_width=data_width, granularity=granularity)

        def process():
            # Initialize native port
            yield native_port.cmd.ready.eq(0)
            yield native_port.wdata.ready.eq(0)
            yield native_port.rdata.valid.eq(0)

            reference_value = 0xBADDCAFE_FEEDFACE_BEEFCAFE_BAD0DAB0

            data_granularity_radio = data_width//granularity

            for i in range(native_port.data_width//data_width):
                res = yield from self.read_request(bus=dut.bus,
                    native_port=native_port,
                    adr=i,
                    sel=2**data_granularity_radio-1,
                    reference_value=reference_value)
                self.assertEqual(res, (reference_value >> (i*data_width)) & 2**data_width-1)

        runSimulation(dut, process, "test_frontend_wishbone.vcd")


    def write_test(self, *, data_width, granularity):
        core = FakeGramCore()
        native_port = core.crossbar.get_native_port()
        dut = gramWishbone(core, data_width=data_width, granularity=granularity)

        def process():
            # Initialize native port
            yield native_port.cmd.ready.eq(0)
            yield native_port.wdata.ready.eq(0)
            yield native_port.rdata.valid.eq(0)

            reference_value = 0xBADDCAFE_FEEDFACE_BEEFCAFE_BAD0DAB0

            data_granularity_radio = data_width//granularity

            for i in range(native_port.data_width//data_width):
                res = yield from self.write_request(bus=dut.bus,
                    native_port=native_port,
                    adr=i,
                    sel=2**data_granularity_radio-1,
                    value=(reference_value >> (i*data_width)) & 2**data_width-1)
                self.assertEqual((reference_value >> (i*data_width)) & 2**data_width-1, (res >> (i*data_width)) & 2**data_width-1)

        runSimulation(dut, process, "test_frontend_wishbone.vcd")

    def test_init(self):
        core = FakeGramCore()
        dut = gramWishbone(core, data_width=32, granularity=8)
        self.assertEqual(dut.bus.data_width, 32)
        self.assertEqual(dut.bus.granularity, 8)

    def test_read8_8(self):
        self.read_test(data_width=8, granularity=8)

    def test_read16_8(self):
        self.read_test(data_width=16, granularity=8)

    def test_read16_16(self):
        self.read_test(data_width=16, granularity=16)

    def test_read32_8(self):
        self.read_test(data_width=32, granularity=8)

    def test_read32_16(self):
        self.read_test(data_width=32, granularity=16)

    def test_read32_32(self):
        self.read_test(data_width=32, granularity=32)

    def test_read64_8(self):
        self.read_test(data_width=64, granularity=8)

    def test_read64_16(self):
        self.read_test(data_width=64, granularity=16)

    def test_read64_32(self):
        self.read_test(data_width=64, granularity=32)

    def test_read64_64(self):
        self.read_test(data_width=64, granularity=64)

    def test_write8_8(self):
        self.write_test(data_width=8, granularity=8)

    def test_write16_8(self):
        self.write_test(data_width=16, granularity=8)

    def test_write16_16(self):
        self.write_test(data_width=16, granularity=16)

    def test_write32_8(self):
        self.write_test(data_width=32, granularity=8)

    def test_write32_16(self):
        self.write_test(data_width=32, granularity=16)

    def test_write32_32(self):
        self.write_test(data_width=32, granularity=32)

    def test_write64_8(self):
        self.write_test(data_width=64, granularity=8)

    def test_write64_16(self):
        self.write_test(data_width=64, granularity=16)

    def test_write64_32(self):
        self.write_test(data_width=64, granularity=32)

    def test_write64_64(self):
        self.write_test(data_width=64, granularity=64)

    def test_sel_write(self):
        core = FakeGramCore()
        native_port = core.crossbar.get_native_port()
        dut = gramWishbone(core, data_width=32, granularity=8)

        def process():
            # Initialize native port
            yield native_port.cmd.ready.eq(0)
            yield native_port.wdata.ready.eq(0)
            yield native_port.rdata.valid.eq(0)

            def sel1(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0b1)
            def sel2(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0b10)
            def sel3(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0b100)
            def sel4(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0b1000)
            def sel5(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0b10000)
            def sel9(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0b100000000)
            def sel13(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0b1000000000000)
            def selfirstdword(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0xF)
            def sellastdword(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0xF000)

            yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=0,
                sel=1,
                value=0xCA,
                timeout=128,
                ackCallback=sel1)

            yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=0,
                sel=0b10,
                value=0xCA,
                timeout=128,
                ackCallback=sel2)

            yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=0,
                sel=0b100,
                value=0xCA,
                timeout=128,
                ackCallback=sel3)

            yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=0,
                sel=0b1000,
                value=0xCA,
                timeout=128,
                ackCallback=sel4)

            yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=1,
                sel=1,
                value=0xCA,
                timeout=128,
                ackCallback=sel5)

        yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=2,
                sel=1,
                value=0xCA,
                timeout=128,
                ackCallback=sel9)

        yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=3,
                sel=1,
                value=0xCA,
                timeout=128,
                ackCallback=sel13)

        yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=3,
                sel=0xF,
                value=0xCA,
                timeout=128,
                ackCallback=sellastdword)

        yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=4,
                sel=0xF,
                value=0xCA,
                timeout=128,
                ackCallback=selfirstdword)

        runSimulation(dut, process, "test_frontend_wishbone.vcd")

    def test_sel_empty(self):
        core = FakeGramCore()
        native_port = core.crossbar.get_native_port()
        dut = gramWishbone(core, data_width=32, granularity=8)

        def process():
            # Initialize native port
            yield native_port.cmd.ready.eq(0)
            yield native_port.wdata.ready.eq(0)
            yield native_port.rdata.valid.eq(0)

            def selfirstdword(bus, native_port):
                self.assertEqual((yield native_port.wdata.we), 0xF)

            yield from self.write_request(bus=dut.bus,
                native_port=native_port,
                adr=0,
                sel=0,
                value=0xAAAAAAAA,
                timeout=128,
                ackCallback=selfirstdword)

        runSimulation(dut, process, "test_frontend_wishbone.vcd")
