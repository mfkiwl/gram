# This file is Copyright (c) 2020 LambdaConcept <contact@lambdaconcept.com>

import unittest

from nmigen import *
from nmigen import tracer
from nmigen.compat import Case
from nmigen.back.pysim import *

__ALL__ = ["delayed_enter", "RoundRobin", "Timeline", "CSRPrefixProxy"]


def delayed_enter(m, src, dst, delay):
    assert delay > 0

    for i in range(delay):
        if i == 0:
            statename = src
        else:
            statename = "{}-{}".format(src, i)

        if i == delay-1:
            deststate = dst
        else:
            deststate = "{}-{}".format(src, i+1)

        with m.State(statename):
            m.next = deststate

class RoundRobin(Elaboratable):
    """A round-robin scheduler. (HarryHo90sHK)
    Parameters
    ----------
    n : int
        Maximum number of requests to handle.
    Attributes
    ----------
    request : Signal(n)
        Signal where a '1' on the i-th bit represents an incoming request from the i-th device.
    grant : Signal(range(n))
        Signal that equals to the index of the device which is currently granted access.
    stb : Signal()
        Strobe signal to enable granting access to the next device requesting. Externally driven.
    """

    def __init__(self, n):
        self.n = n
        self.request = Signal(n)
        self.grant = Signal(range(n))
        self.stb = Signal()

    def elaborate(self, platform):
        m = Module()

        if self.n == 1:
            m.d.comb += self.grant.eq(0)
        else:
            with m.If(self.stb):
                with m.Switch(self.grant):
                    for i in range(self.n):
                        with m.Case(i):
                            for j in reversed(range(i+1, i+self.n)):
                                # If i+1 <= j < n, then t == j;     (after i)
                                # If n <= j < i+n, then t == j - n  (before i)
                                t = j % self.n
                                with m.If(self.request[t]):
                                    m.d.sync += self.grant.eq(t)

        return m


class Timeline(Elaboratable):
    def __init__(self, events):
        self.trigger = Signal()
        self._events = events

    def elaborate(self, platform):
        m = Module()

        lastevent = max([e[0] for e in self._events])
        counter = Signal(range(lastevent+1))

        # Counter incrementation
        # (with overflow handling)
        if (lastevent & (lastevent + 1)) != 0:
            with m.If(counter == lastevent):
                m.d.sync += counter.eq(0)
            with m.Else():
                with m.If(counter != 0):
                    m.d.sync += counter.eq(counter+1)
                with m.Elif(self.trigger):
                    m.d.sync += counter.eq(1)
        else:
            with m.If(counter != 0):
                m.d.sync += counter.eq(counter+1)
            with m.Elif(self.trigger):
                m.d.sync += counter.eq(1)

        for e in self._events:
            if e[0] == 0:
                with m.If(self.trigger & (counter == 0)):
                    m.d.sync += e[1]
            else:
                with m.If(counter == e[0]):
                    m.d.sync += e[1]

        return m


class CSRPrefixProxy:
    def __init__(self, bank, prefix):
        self._bank = bank
        self._prefix = prefix

    def csr(self, width, access, *, addr=None, alignment=None, name=None,
            src_loc_at=0):
        if name is not None and not isinstance(name, str):
            raise TypeError("Name must be a string, not {!r}".format(name))
        name = name or tracer.get_var_name(depth=2 + src_loc_at).lstrip("_")

        prefixed_name = "{}_{}".format(self._prefix, name)
        return self._bank.csr(width=width, access=access, addr=addr,
                              alignment=alignment, name=prefixed_name)
