# This file is Copyright (c) 2015 Sebastien Bourdeauducq <sb@m-labs.hk>
# This file is Copyright (c) 2020 LambdaConcept <contact@lambdaconcept.com>

from nmigen import *
from nmigen.hdl.rec import *

__ALL__ = ["Interface"]


def phase_description(addressbits, bankbits, nranks, databits):
    return [
        # cmd description
        ("address", addressbits, DIR_FANOUT),
        ("bank", bankbits, DIR_FANOUT),
        ("cas", 1, DIR_FANOUT),
        ("cs", nranks, DIR_FANOUT),
        ("ras", 1, DIR_FANOUT),
        ("we", 1, DIR_FANOUT),
        ("clk_en", nranks, DIR_FANOUT),
        ("odt", nranks, DIR_FANOUT),
        ("reset", 1, DIR_FANOUT),
        ("act", 1, DIR_FANOUT),
        # wrdata description
        ("wrdata", databits, DIR_FANOUT),
        ("wrdata_en", 1, DIR_FANOUT),
        ("wrdata_mask", databits//8, DIR_FANOUT),
        # rddata description
        ("rddata_en", 1, DIR_FANOUT),
        ("rddata", databits, DIR_FANIN),
        ("rddata_valid", 1, DIR_FANIN),
    ]


class Interface:
    def __init__(self, addressbits, bankbits, nranks, databits, nphases=1):
        self.phases = []
        for p in range(nphases):
            p = Record(phase_description(
                addressbits, bankbits, nranks, databits))
            self.phases += [p]
            p.reset.reset = 1

    def connect(self, target):
        if not isinstance(target, Interface):
            raise TypeError("Target must be an instance of Interface, not {!r}"
                            .format(target))

        ret = []
        for i in range(min(len(self.phases), len(target.phases))):
            ret += [self.phases[i].connect(target.phases[i])]

        return ret
