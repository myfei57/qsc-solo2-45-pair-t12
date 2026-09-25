"""Survey line latch, track and geometry."""

import pytest

from dredgeops.errors import LatchClearError, LatchSetError


def test_line_latch_sets_when_a_line_opens(services):
    row = services.drag.next_line(services.pos, "L-1")
    assert row["line_id"] == "L-1"
    assert services.pos.latch() is True
    assert services.pos.active_line() == "L-1"
    assert services.drag.line_record()["count"] == 1


def test_second_line_is_refused_while_the_latch_is_set(services):
    services.drag.next_line(services.pos, "L-1")
    with pytest.raises(LatchSetError):
        services.drag.next_line(services.pos, "L-2")
    assert services.pos.active_line() == "L-1"


def test_line_needs_an_identifier(services):
    with pytest.raises(Exception) as failure:
        services.drag.next_line(services.pos, "")
    assert "identifier" in str(failure.value)


def test_latch_clears_after_the_result_is_committed(services):
    services.drag.next_line(services.pos, "L-1")
    row = services.pos.line_done(128.5)
    assert row == {"done": 1, "latched": False}
    assert services.pos.latch() is False
    assert services.pos.active_line() == ""
    assert services.pos.results()[0]["length"] == 128.5


def test_latch_stays_set_when_the_result_write_is_refused(services):
    services.drag.next_line(services.pos, "L-1")
    services.journal.set_read_only(True)
    with pytest.raises(LatchClearError):
        services.pos.line_done(128.5)
    services.journal.set_read_only(False)
    assert services.pos.latch() is True
    assert services.pos.done_lines() == 0
    assert services.pos.active_line() == "L-1"


def test_line_done_without_an_open_line_is_refused(services):
    with pytest.raises(LatchClearError):
        services.pos.line_done(10.0)


def test_track_counts_open_and_closed_lines(services):
    assert services.pos.track() == {"total": 0, "closed": 0, "open": 0}
    services.drag.next_line(services.pos, "L-1")
    assert services.pos.track() == {"total": 1, "closed": 0, "open": 1}
    services.pos.line_done(100.0)
    assert services.pos.track() == {"total": 1, "closed": 1, "open": 0}


def test_geometry_and_line_origin(services):
    assert services.pos.geometry(100.0, 25.0, 4) == [100.0, 125.0, 150.0, 175.0]
    assert services.pos.line_origin(3, 25.0) == 75.0
    assert services.pos.line_origin(-1, 25.0) == 0.0


def test_waypoint_distance(services):
    assert services.pos.distance_to(1.0, 1.0)["present"] is False
    services.pos.set_waypoint("W-1", 10.0, 20.0)
    result = services.pos.distance_to(13.0, 24.0)
    assert result["present"] is True
    assert result["distance"] == 5.0
