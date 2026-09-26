"""Aggregate view over the event record stream."""

from typing import Any, Sequence

from .record import AuditRecord


def summarize(records: Sequence[AuditRecord], watermark: int | None = None) -> dict[str, Any]:
    """Topic and generation counts for records at or below a watermark.

    The watermark is the highest record sequence covered by the summary, so a
    summary always states which slice of the stream its counts were computed
    over. It defaults to the tail of the stream.
    """
    tail = records[-1].seq if records else 0
    limit = tail if watermark is None else min(int(watermark), tail)
    topics: dict[str, int] = {}
    generations: dict[int, int] = {}
    total = 0
    for record in records:
        if record.seq > limit:
            continue
        total += 1
        topics[record.topic] = topics.get(record.topic, 0) + 1
        generations[record.generation] = generations.get(record.generation, 0) + 1
    return {
        "watermark": limit,
        "total": total,
        "topics": topics,
        "generations": {str(key): value for key, value in sorted(generations.items())},
    }
