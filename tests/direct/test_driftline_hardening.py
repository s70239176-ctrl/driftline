"""Forged-leader tests: a well-formed but substantively false leader result must be rejected.

`direct_vm.run_validator` feeds the validator a leader result of our choosing while the validator
re-fetches the (mocked) page and re-judges it itself.
"""
import cloudpickle
import pytest

from conftest import (
    CLAUSES, PAGE_COSMETIC, PAGE_GONE, PAGE_MATERIAL, PAGE_V1, Q_NOTICE, Q_REFUND, Q_SELL,
    compare_json, extract_json,
)


def _obs(reach="OK", severity=0, kind="NONE", evidence="", missing=0):
    return {"reach": reach, "severity": severity, "evidence_kind": kind, "evidence": evidence, "missing": missing}


def _bobs(reach="OK", clauses=None):
    return {"reach": reach, "clauses": CLAUSES if clauses is None else clauses}


def _validate(env, leader_result):
    return env.vm.run_validator(leader_result=leader_result)


def _after_check(env, page=PAGE_V1, compare=None):
    """Run one real check so the check validator is the registered one, then re-arm mocks."""
    wid = env.ready()
    env.check(wid, page, compare if compare is not None else compare_json(0))
    return wid


# ----------------------------------------------------------- check validator


def test_honest_stable_accepted(env):
    _after_check(env)
    assert _validate(env, _obs()) is True


def test_forged_stable_rejected_when_validator_sees_material_drift(env):
    _after_check(env)
    env.reset(); env.page(PAGE_MATERIAL); env.llm(compare=compare_json(2, "ABSENT", Q_SELL))
    assert _validate(env, _obs(missing=0)) is False  # wrong deterministic fact (missing)
    assert _validate(env, _obs(missing=1)) is False  # right fact, but claims no drift while validator sees MATERIAL


def test_honest_drift_accepted(env):
    _after_check(env)
    env.reset(); env.page(PAGE_MATERIAL); env.llm(compare=compare_json(2, "ABSENT", Q_SELL))
    assert _validate(env, _obs(severity=2, kind="ABSENT", evidence=Q_SELL, missing=1)) is True


def test_forged_drift_rejected_when_validator_sees_cosmetic(env):
    _after_check(env)
    env.reset(); env.page(PAGE_COSMETIC); env.llm(compare=compare_json(1))
    forged = _obs(severity=3, kind="PRESENT", evidence="ACME TERMS OF SERVICE (updated Jan 2026)", missing=0)
    assert _validate(env, forged) is False


def test_forged_evidence_not_on_page_rejected(env):
    _after_check(env)
    env.reset(); env.page(PAGE_MATERIAL); env.llm(compare=compare_json(2, "ABSENT", Q_SELL))
    assert _validate(env, _obs(severity=2, kind="PRESENT", evidence="We now sell all your data to brokers", missing=1)) is False


def test_forged_absent_evidence_that_is_still_present_rejected(env):
    _after_check(env)
    env.reset(); env.page(PAGE_MATERIAL); env.llm(compare=compare_json(2, "ABSENT", Q_SELL))
    # Q_REFUND is still on the page, so it cannot be "absent"
    assert _validate(env, _obs(severity=2, kind="ABSENT", evidence=Q_REFUND, missing=1)) is False


def test_forged_unreachable_rejected_when_validator_can_read(env):
    _after_check(env)
    assert _validate(env, _obs(reach="UNREACHABLE")) is False


def test_forged_ok_rejected_when_validator_cannot_read(env):
    _after_check(env)
    env.reset()
    assert _validate(env, _obs()) is False
    assert _validate(env, _obs(reach="UNREACHABLE")) is True


def test_forged_unclassified_cannot_hide_wrong_missing_count(env):
    _after_check(env)
    assert _validate(env, _obs(reach="UNCLASSIFIED", missing=2)) is False
    assert _validate(env, _obs(reach="UNCLASSIFIED", missing=0)) is True  # fails closed, so acceptable


def test_cosmetic_vs_none_is_equivalent_below_threshold(env):
    _after_check(env)
    env.reset(); env.page(PAGE_COSMETIC); env.llm(compare=compare_json(1))
    assert _validate(env, _obs(severity=0)) is True  # same side of the threshold


def test_material_vs_critical_is_equivalent_for_threshold_two(env):
    _after_check(env)
    env.reset(); env.page(PAGE_MATERIAL); env.llm(compare=compare_json(2, "ABSENT", Q_SELL))
    assert _validate(env, _obs(severity=3, kind="ABSENT", evidence=Q_SELL, missing=1)) is True


def test_floor_cannot_be_dodged_by_leader(env):
    _after_check(env)
    env.reset(); env.page(PAGE_GONE); env.llm(compare=compare_json(0))
    assert _validate(env, _obs(severity=0, missing=3)) is False  # validator floors to MATERIAL
    assert _validate(env, _obs(severity=2, kind="ABSENT", evidence=Q_SELL, missing=3)) is True


@pytest.mark.parametrize("forged", [
    {"reach": "OK", "severity": True, "evidence_kind": "NONE", "evidence": "", "missing": 0},
    {"reach": "OK", "severity": 0.0, "evidence_kind": "NONE", "evidence": "", "missing": 0},
    {"reach": "OK", "severity": "0", "evidence_kind": "NONE", "evidence": "", "missing": 0},
    {"reach": "OK", "severity": "0x2", "evidence_kind": "NONE", "evidence": "", "missing": 0},
    {"reach": "OK", "severity": -1, "evidence_kind": "NONE", "evidence": "", "missing": 0},
    {"reach": "OK", "severity": 4, "evidence_kind": "NONE", "evidence": "", "missing": 0},
    {"reach": "OK", "severity": 0, "evidence_kind": "NONE", "evidence": "", "missing": False},
    {"reach": "OK", "severity": 0, "evidence_kind": "NONE", "evidence": "", "missing": -1},
    {"reach": "MAYBE", "severity": 0, "evidence_kind": "NONE", "evidence": "", "missing": 0},
    {"reach": "OK", "severity": 0, "evidence_kind": "MAYBE", "evidence": "", "missing": 0},
    {"reach": "OK", "severity": 2, "evidence_kind": "NONE", "evidence": "", "missing": 0},  # MATERIAL w/o evidence
    {"reach": "OK", "severity": 0, "evidence_kind": "NONE", "evidence": "stray", "missing": 0},
    {"reach": "OK", "severity": 0, "evidence_kind": "NONE", "evidence": "", "missing": 0, "extra": 1},
    {"reach": "OK", "severity": 0, "evidence_kind": "NONE", "evidence": ""},  # missing field
    {"reach": "UNREACHABLE", "severity": 2, "evidence_kind": "NONE", "evidence": "", "missing": 0},
    {"reach": "OK", "severity": 0, "evidence_kind": "NONE", "evidence": "", "missing": 99},
    ["OK", 0],
    "OK",
    None,
])
def test_malformed_leader_results_rejected(env, forged):
    _after_check(env)
    assert _validate(env, forged) is False


def test_leader_error_is_not_accepted(env):
    _after_check(env)
    assert env.vm.run_validator(leader_error=Exception("boom")) is False


# -------------------------------------------------------- baseline validator


def _after_baseline(env):
    wid = env.register()
    env.baseline(wid)
    return wid


def test_baseline_honest_leader_accepted(env):
    _after_baseline(env)
    assert _validate(env, _bobs()) is True


def test_baseline_fabricated_clause_rejected(env):
    _after_baseline(env)
    forged = CLAUSES + [{"statement": "pony", "quote": "We will give every customer a pony"}]
    assert _validate(env, _bobs(clauses=forged)) is False


def test_baseline_quote_not_in_validator_copy_rejected(env):
    _after_baseline(env)
    env.reset(); env.page(PAGE_MATERIAL); env.llm(extract=extract_json())
    # Q_SELL is gone from the validator's own fetch, so a leader citing it is lying
    assert _validate(env, _bobs()) is False
    assert _validate(env, _bobs(clauses=CLAUSES[1:])) is True


def test_baseline_unreachable_claim_checked_against_validator(env):
    _after_baseline(env)
    assert _validate(env, _bobs(reach="UNREACHABLE", clauses=[])) is False
    env.reset()
    assert _validate(env, _bobs(reach="UNREACHABLE", clauses=[])) is True
    assert _validate(env, _bobs()) is False


@pytest.mark.parametrize("clauses", [
    [],
    CLAUSES * 4,  # duplicate quotes
    [{"statement": "", "quote": Q_SELL}],
    [{"statement": "x", "quote": "short"}],
    [{"statement": "x" * 161, "quote": Q_SELL}],
    [{"statement": "x", "quote": Q_SELL, "extra": 1}],
    [{"statement": 1, "quote": Q_SELL}],
    [{"statement": "x", "quote": True}],
    "not a list",
])
def test_baseline_malformed_clauses_rejected(env, clauses):
    _after_baseline(env)
    assert _validate(env, {"reach": "OK", "clauses": clauses}) is False


def test_baseline_ok_with_empty_clauses_rejected(env):
    _after_baseline(env)
    assert _validate(env, {"reach": "OK", "clauses": []}) is False
    assert _validate(env, {"reach": "UNCLASSIFIED", "clauses": [CLAUSES[0]]}) is False


# ------------------------------------------------------------------ pickling


def test_nondet_closures_are_picklable(env):
    """Direct Mode also runs with check_pickling=True; this guards against capturing storage."""
    wid = env.ready()
    env.check(wid, PAGE_V1, compare_json(0))
    assert cloudpickle.dumps(env.c.get_watch(wid)) is not None
