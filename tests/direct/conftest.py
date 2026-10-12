"""Shared Direct Mode helpers for Driftline."""
import datetime
import json
import sys

import pytest

BASE = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
URL = "https://terms.example.com/tos"
URL_RE = r"^https://terms\.example\.com/tos$"
FOCUS = "Data privacy and refund commitments to customers"

Q_SELL = "never sell your personal data to third parties"
Q_REFUND = "Refunds are available within 30 days of purchase"
Q_NOTICE = "60 days notice before changing prices"

PAGE_V1 = (
    "Acme Terms of Service. We will " + Q_SELL + ". "
    + Q_REFUND + ". We give " + Q_NOTICE + "."
)
PAGE_COSMETIC = PAGE_V1.replace("Acme Terms of Service.", "ACME TERMS OF SERVICE (updated Jan 2026).")
PAGE_MATERIAL = (
    "Acme Terms of Service. We may share your data with advertising partners. "
    + Q_REFUND + ". We give " + Q_NOTICE + "."
)
PAGE_GONE = "Acme has moved. Visit our new site for current information."

CLAUSES = [
    {"statement": "No sale of personal data", "quote": Q_SELL},
    {"statement": "30 day refunds", "quote": Q_REFUND},
    {"statement": "Price change notice", "quote": Q_NOTICE},
]


def iso(offset_s: int) -> str:
    return (BASE + datetime.timedelta(seconds=offset_s)).isoformat().replace("+00:00", "Z")


def extract_json(clauses=None):
    return json.dumps({"clauses": CLAUSES if clauses is None else clauses})


def compare_json(severity=0, kind="NONE", evidence=""):
    return json.dumps({"severity": severity, "evidence_kind": kind, "evidence": evidence})


class Env:
    def __init__(self, vm, contract, alice, bob):
        self.vm, self.c = vm, contract
        self.owner, self.other = alice, bob
        self.t = 0

    def warp(self, offset_s):
        # genlayer-test 0.29.2: vm.warp() does not refresh the already-loaded
        # gl.message_raw['datetime'] that the contract reads, so sync it here.
        self.vm.warp(iso(offset_s))
        sys.modules["genlayer.gl"].message_raw["datetime"] = iso(offset_s)

    def now(self):
        return int(BASE.timestamp()) + self.t

    def as_(self, who):
        self.vm.sender = who

    def page(self, body, status=200):
        self.vm.mock_web(URL_RE, {"method": "GET", "status": status, "body": body})

    def llm(self, extract=None, compare=None):
        if extract is not None:
            self.vm.mock_llm(r"DRIFTLINE_EXTRACT", extract)
        if compare is not None:
            self.vm.mock_llm(r"DRIFTLINE_COMPARE", compare)

    def reset(self):
        self.vm.clear_mocks()

    def register(self, min_severity=2, who=None, focus=FOCUS, url=URL):
        self.as_(who or self.owner)
        return self.c.register_watch(url, focus, min_severity)

    def baseline(self, wid, page=PAGE_V1, extract=None, dt=10):
        self.reset()
        self.page(page)
        self.llm(extract=extract if extract is not None else extract_json())
        self.t += dt
        self.warp(self.t)
        self.as_(self.owner)
        return self.c.set_baseline(wid)

    def ready(self, min_severity=2):
        wid = self.register(min_severity)
        self.baseline(wid)
        return wid

    def check(self, wid, page, compare, dt=61, who=None):
        self.reset()
        self.page(page)
        self.llm(compare=compare)
        self.t += dt
        self.warp(self.t)
        self.as_(who or self.other)
        return self.c.check(wid)

    def check_down(self, wid, dt=61):
        self.reset()  # unmocked URL -> the web call raises -> unreachable
        self.t += dt
        self.warp(self.t)
        self.as_(self.other)
        return self.c.check(wid)


@pytest.fixture
def env(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.check_pickling = True
    direct_vm.warp(iso(0))
    contract = direct_deploy("contracts/driftline.py")
    # A real network delivers calldata addresses as genlayer Address, not raw bytes.
    from genlayer.py.types import Address  # importable once the loader has staged the SDK

    a, b = (Address(x) if isinstance(x, bytes) else x for x in (direct_alice, direct_bob))
    e = Env(direct_vm, contract, a, b)
    e.warp(0)
    return e
