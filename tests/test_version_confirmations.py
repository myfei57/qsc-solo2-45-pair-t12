"""Version semantics: short-lived confirmations."""

import pytest

from dredgeops.clock import IdSequence, LogicalClock
from dredgeops.errors import (
    ConfirmationMismatchError,
    StaleArtifactError,
    UnknownConfirmationError,
)
from dredgeops.store import Journal
from dredgeops.version import Confirmations, Generations


def make(tmp_path):
    journal = Journal(str(tmp_path / "stream"))
    clock = LogicalClock()
    generations = Generations(journal)
    return Confirmations(journal, clock, IdSequence("cfm"), generations), clock, generations


def test_issued_confirmation_carries_the_current_generation(tmp_path):
    confirmations, clock, generations = make(tmp_path)
    generations.advance("dens.baseline", "dens-gen")
    confirmation = confirmations.issue("dens.baseline", "dens", 5)
    assert confirmation.generation == 1
    assert confirmation.issued_tick == 0
    assert confirmation.expires_tick == 5
    assert confirmation.confirmation_id == "cfm-000001"


def test_redeem_accepts_a_confirmation_inside_its_ttl(tmp_path):
    confirmations, clock, generations = make(tmp_path)
    confirmation = confirmations.issue("dens.baseline", "dens", 5)
    clock.advance(3)
    redeemed = confirmations.redeem(confirmation.confirmation_id, "dens.baseline", "dens")
    assert redeemed.confirmation_id == confirmation.confirmation_id


def test_redeem_refuses_a_confirmation_after_its_ttl(tmp_path):
    confirmations, clock, generations = make(tmp_path)
    confirmation = confirmations.issue("dens.baseline", "dens", 5)
    clock.advance(6)
    with pytest.raises(StaleArtifactError):
        confirmations.redeem(confirmation.confirmation_id, "dens.baseline", "dens")


def test_redeem_refuses_a_confirmation_whose_generation_moved_on(tmp_path):
    confirmations, clock, generations = make(tmp_path)
    confirmation = confirmations.issue("dens.baseline", "dens", 50)
    generations.advance("dens.baseline", "dens-gen")
    with pytest.raises(StaleArtifactError):
        confirmations.redeem(confirmation.confirmation_id, "dens.baseline", "dens")


def test_redeem_refuses_a_confirmation_for_another_subject(tmp_path):
    confirmations, clock, generations = make(tmp_path)
    confirmation = confirmations.issue("dens.baseline", "dens", 5)
    with pytest.raises(ConfirmationMismatchError):
        confirmations.redeem(confirmation.confirmation_id, "dens.baseline", "pump")


def test_redeem_refuses_an_unknown_confirmation(tmp_path):
    confirmations, clock, generations = make(tmp_path)
    with pytest.raises(UnknownConfirmationError):
        confirmations.redeem("cfm-000099", "dens.baseline", "dens")


def test_issue_rejects_a_non_positive_ttl(tmp_path):
    confirmations, clock, generations = make(tmp_path)
    with pytest.raises(ValueError):
        confirmations.issue("dens.baseline", "dens", 0)


def test_outstanding_excludes_expired_confirmations(tmp_path):
    confirmations, clock, generations = make(tmp_path)
    confirmations.issue("dens.baseline", "dens", 5)
    assert len(confirmations.outstanding()) == 1
    clock.advance(9)
    assert confirmations.outstanding() == ()


def test_confirmations_survive_a_restart(tmp_path):
    directory = str(tmp_path / "stream")
    journal = Journal(directory)
    clock = LogicalClock()
    first = Confirmations(journal, clock, IdSequence("cfm"), Generations(journal))
    confirmation = first.issue("pump.curve", "pump", 9)

    second = Confirmations(Journal(directory), clock, IdSequence("cfm"), Generations(journal))
    restored = second.get(confirmation.confirmation_id)
    assert restored is not None
    assert restored.subject == "pump"
