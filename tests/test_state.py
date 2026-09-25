"""Read model aggregation and the expiring control snapshot."""

import pytest

from dredgeops.errors import StaleArtifactError
from dredgeops.event import ALL_TOPICS

from support import issue_confirmation, ok


SUBSYSTEMS = ("pump", "jet", "drag", "hopper", "overflow", "valve", "pos", "dens")


def test_state_view_aggregates_every_subsystem(services):
    payload = services.state.view().to_dict()
    assert tuple(sorted(payload["subsystems"])) == tuple(sorted(SUBSYSTEMS))
    assert payload["subsystems"]["pump"]["running"] is False
    assert payload["committed_keys"] == 0


def test_state_view_advances_with_the_stream(services):
    services.pump.persist()
    payload = services.state.view().to_dict()
    assert payload["committed_keys"] == 1
    assert payload["watermark"] == 1
    assert payload["subsystems"]["pump"]["persisted"] is True


def test_counters_track_every_declared_topic(services):
    services.jet.open_jet()
    counters = services.state.counters()
    assert tuple(counters) == ALL_TOPICS
    assert counters["jet.opened"] == 1
    assert counters["pump.started"] == 0


def test_snapshot_freezes_the_committed_stream(services):
    services.pump.persist()
    payload = services.state.snapshot()
    assert payload["snapshot"]["watermark"] == 1
    assert payload["artifact"]["kind"] == "snapshot"
    assert payload["artifact"]["generation"] == 1
    assert services.state.require_snapshot(10).digest == payload["snapshot"]["digest"]


def test_snapshot_is_refused_after_a_parameter_generation_moves(services, console):
    services.state.snapshot()
    services.dens.replace_probe()
    with pytest.raises(StaleArtifactError):
        services.state.require_snapshot(100)


def test_snapshot_is_refused_once_it_ages_past_the_limit(services):
    services.state.snapshot()
    services.clock.advance(200)
    with pytest.raises(StaleArtifactError):
        services.state.require_snapshot(100)


def test_verdict_history_is_available_per_subject(services, console):
    confirmation_id = issue_confirmation(console, "dens.baseline", "dens")
    services.dens.calibrate(1000.0, confirmation_id)
    services.drag.head(services.dens, 1200.0)
    payload = services.state.verdict_history("drag.head")
    assert payload["current"] == "high"
    assert payload["points"][0]["detail"] == "reading=1200.0"
    assert services.state.verdict_history("unknown.subject")["current"] == "unknown"


def test_snapshot_endpoint_round_trip(services, console):
    created = ok(console, "POST", "/api/state/snapshot", {})
    checked = ok(console, "GET", "/api/state/snapshot?max_age=50")
    assert checked["digest"] == created["snapshot"]["digest"]


def test_counters_endpoint_lists_topics(services, console):
    ok(console, "POST", "/api/jet/open", {})
    counters = ok(console, "GET", "/api/state/counters")
    assert counters["jet.opened"] == 1
