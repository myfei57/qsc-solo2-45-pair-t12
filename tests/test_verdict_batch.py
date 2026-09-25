"""Judgement semantics: batch uniqueness."""

import pytest

from dredgeops.errors import DuplicateBatchError, UnknownBatchError
from dredgeops.verdict import BatchRegistry


def test_first_reservation_is_accepted(journal):
    batches = BatchRegistry(journal)
    batches.reserve("B-1", {"volume": 12.5})
    assert batches.is_reserved("B-1") is True
    assert batches.payload("B-1")["volume"] == 12.5


def test_duplicate_batch_identifier_is_refused(journal):
    batches = BatchRegistry(journal)
    batches.reserve("B-1", {"volume": 12.5})
    with pytest.raises(DuplicateBatchError):
        batches.reserve("B-1", {"volume": 99.0})
    assert batches.payload("B-1")["volume"] == 12.5


def test_released_identifier_can_be_issued_again(journal):
    batches = BatchRegistry(journal)
    batches.reserve("B-1", {"volume": 12.5})
    batches.release("B-1")
    assert batches.is_reserved("B-1") is False
    batches.reserve("B-1", {"volume": 1.0})
    assert batches.payload("B-1")["volume"] == 1.0


def test_release_of_an_unknown_batch_is_refused(journal):
    batches = BatchRegistry(journal)
    with pytest.raises(UnknownBatchError):
        batches.release("B-9")


def test_reserved_ids_are_listed_in_key_order(journal):
    batches = BatchRegistry(journal)
    batches.reserve("B-2", {"volume": 2.0})
    batches.reserve("B-1", {"volume": 1.0})
    assert batches.reserved_ids() == ("B-1", "B-2")
