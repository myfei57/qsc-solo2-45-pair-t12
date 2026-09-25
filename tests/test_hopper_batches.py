"""Judgement semantics: discharge batch uniqueness."""

import pytest

from dredgeops.errors import DuplicateBatchError


def test_discharge_batch_is_recorded_once(services):
    row = services.hopper.record_batch("D-1", "bow", 12.5)
    assert row["batch_id"] == "D-1"
    assert row["total"] == 12.5
    assert services.batches.is_reserved("D-1") is True


def test_duplicate_discharge_batch_is_refused(services):
    services.hopper.record_batch("D-1", "bow", 12.5)
    with pytest.raises(DuplicateBatchError):
        services.hopper.record_batch("D-1", "mid", 99.0)
    assert services.hopper.batch_total() == 12.5


def test_batch_total_sums_accepted_volumes(services):
    services.hopper.record_batch("D-1", "bow", 10.0)
    services.hopper.record_batch("D-2", "mid", 5.5)
    assert services.hopper.batch_total() == 15.5
    assert len(services.hopper.batch_entries()) == 2
    assert services.bus.count("hopper.batch.recorded") == 2


def test_batch_total_survives_a_restart(config):
    from support import build

    first = build(config)
    first.hopper.record_batch("D-1", "bow", 7.5)
    second = build(config)
    assert second.hopper.batch_total() == 7.5
    assert second.batches.is_reserved("D-1") is True
