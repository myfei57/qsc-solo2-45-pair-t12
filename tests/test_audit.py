"""Append-only event records and query filtering."""

from dredgeops.verdict import RecordFilter

from support import build, ok


def test_every_published_event_is_recorded(services):
    services.jet.open_jet()
    services.pump.start(services.jet)
    records = services.audit.records()
    assert [record.topic for record in records] == ["jet.opened", "pump.started"]
    assert records[0].record_id == "evt-000001"
    assert records[0].seq == 1


def test_query_returns_newest_first(services):
    services.jet.open_jet()
    services.jet.close()
    records = services.audit.query(RecordFilter())
    assert [record.topic for record in records] == ["jet.closed", "jet.opened"]


def test_query_filters_by_topic(services):
    services.jet.open_jet()
    services.jet.close()
    records = services.audit.by_topic("jet.opened")
    assert len(records) == 1
    assert records[0].seq == 1
    assert services.audit.count("jet.closed") == 1


def test_query_filters_by_sequence_and_generation(services, console):
    ok(console, "POST", "/api/jet/open", {})
    confirmation_id = ok(
        console,
        "POST",
        "/api/confirmation",
        {"name": "dens.baseline", "subject": "dens", "ttl_ticks": 5},
    )["confirmation_id"]
    ok(
        console,
        "POST",
        "/api/dens/calibrate",
        {"baseline": 1010.0, "confirmation_id": confirmation_id},
    )
    kept = services.audit.query(RecordFilter(min_seq=2))
    assert [record.seq for record in kept] == [2]
    assert services.audit.sequence == 2


def test_summary_counts_topics_and_generations(services):
    services.jet.open_jet()
    services.jet.close()
    services.jet.open_jet()
    summary = services.audit.summary()
    assert summary["watermark"] == 3
    assert summary["total"] == 3
    assert summary["topics"]["jet.opened"] == 2
    assert summary["generations"] == {"0": 3}


def test_summary_states_its_coverage_watermark(services):
    services.jet.open_jet()
    services.jet.close()
    summary = services.audit.summary()
    assert summary["watermark"] == services.audit.sequence == 2


def test_summary_can_be_frozen_at_an_earlier_watermark(services, console):
    services.jet.open_jet()
    services.jet.close()
    services.jet.open_jet()
    earlier = services.audit.summary(watermark=2)
    assert earlier["watermark"] == 2
    assert earlier["total"] == 2
    assert earlier["topics"] == {"jet.opened": 1, "jet.closed": 1}
    # 超过流尾的水位夹到流尾；零水位覆盖空区间
    assert services.audit.summary(watermark=99)["watermark"] == 3
    assert services.audit.summary(watermark=0)["total"] == 0


def test_summary_endpoint_reports_watermark_and_sequence(console):
    ok(console, "POST", "/api/jet/open", {})
    body = ok(console, "GET", "/api/audit/summary")
    assert body["watermark"] == 1
    assert body["sequence"] == 1
    frozen = ok(console, "GET", "/api/audit/summary?watermark=0")
    assert frozen["watermark"] == 0
    assert frozen["total"] == 0


def test_clear_empties_the_stream_but_keeps_the_sequence(services):
    services.jet.open_jet()
    services.jet.close()
    assert services.audit.clear() == 2
    assert services.audit.records() == ()
    assert services.audit.sequence == 2
    services.jet.open_jet()
    assert services.audit.records()[0].record_id == "evt-000003"


def test_records_are_replayed_after_a_restart(config):
    first = build(config)
    first.jet.open_jet()
    first.jet.close()
    second = build(config)
    records = second.audit.records()
    assert [record.topic for record in records] == ["jet.opened", "jet.closed"]
    assert records[1].record_id == "evt-000002"
    assert second.audit.sequence == 2


def test_newest_helper_can_be_limited(services):
    for _ in range(3):
        services.jet.open_jet()
    assert len(services.audit.news(2)) == 2
    assert services.audit.records()[0].seq == 1
