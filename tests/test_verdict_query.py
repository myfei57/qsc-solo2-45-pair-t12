"""Judgement semantics: query filter conditions."""

from dredgeops.verdict import RecordFilter, parse_filter


ROWS = [
    {"topic": "pump.started", "seq": 1, "generation": 1, "batch_id": "b1", "kind": "event"},
    {"topic": "pump.stopped", "seq": 2, "generation": 1, "batch_id": "b2", "kind": "event"},
    {"topic": "pump.started", "seq": 3, "generation": 2, "batch_id": "b3", "kind": "event"},
]


def test_filter_matches_on_topic():
    kept = RecordFilter(topic="pump.started").apply(ROWS)
    assert [row["seq"] for row in kept] == [1, 3]


def test_filter_matches_on_key_prefix():
    rows = [{"key": "pump/curve"}, {"key": "dens/baseline"}]
    assert RecordFilter(key_prefix="pump/").apply(rows) == [{"key": "pump/curve"}]


def test_filter_matches_on_sequence_bounds():
    kept = RecordFilter(min_seq=2, max_seq=2).apply(ROWS)
    assert [row["seq"] for row in kept] == [2]


def test_filter_matches_on_generation_floor():
    kept = RecordFilter(min_generation=2).apply(ROWS)
    assert [row["seq"] for row in kept] == [3]


def test_filter_matches_on_batch_and_kind():
    assert RecordFilter(batch_id="b2").apply(ROWS) == [ROWS[1]]
    assert RecordFilter(kinds=("put",)).apply(ROWS) == []


def test_empty_filter_keeps_every_row():
    assert RecordFilter().apply(ROWS) == ROWS
    assert RecordFilter().describe()["topic"] is None


def test_parse_filter_reads_request_parameters():
    record_filter = parse_filter(
        {"topic": "pump.started", "min_seq": "3", "kind": "put,event", "batch_id": "b3"}
    )
    assert record_filter.topic == "pump.started"
    assert record_filter.min_seq == 3
    assert record_filter.kinds == ("put", "event")
    assert record_filter.matches(ROWS[2]) is True
    assert record_filter.matches(ROWS[0]) is False
