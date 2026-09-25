"""State machine: durability gates in front of downstream actions."""

import pytest

from dredgeops.errors import PreGateError
from dredgeops.interlock import PreGate


def test_gate_refuses_until_the_upstream_key_is_committed(journal):
    gate = PreGate("drag.lower", journal, "pump/state")
    assert gate.satisfied() is False
    with pytest.raises(PreGateError):
        gate.require()


def test_gate_refuses_while_the_upstream_write_is_still_open(journal):
    gate = PreGate("drag.lower", journal, "pump/state")
    journal.open("draft")
    journal.append("pump/state", {"depth": 9}, "draft")
    assert gate.satisfied() is False
    with pytest.raises(PreGateError):
        gate.require()


def test_gate_passes_once_the_upstream_value_is_committed(journal):
    gate = PreGate("drag.lower", journal, "pump/state")
    journal.open("write")
    journal.append("pump/state", {"depth": 9}, "write")
    journal.commit("write")
    assert gate.require() == {"depth": 9}


def test_gate_is_unsatisfied_again_after_a_rollback(journal):
    gate = PreGate("drag.lower", journal, "pump/state")
    journal.open("write")
    journal.append("pump/state", {"depth": 9}, "write")
    journal.commit("write")
    journal.rollback("write")
    assert gate.satisfied() is False


def test_gate_reports_its_name_and_key(journal):
    gate = PreGate("valve.sea", journal, "hopper/gate")
    assert gate.name == "valve.sea"
    assert gate.key == "hopper/gate"
