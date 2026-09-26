"""Snapshot records that pin a digest to a commit watermark."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .entry import Entry


def canonical(value: Any) -> str:
    """Stable textual form of a value, independent of mapping order."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest_rows(rows: Mapping[str, Any]) -> str:
    """Digest of the latest committed value per key."""
    payload = "".join(f"{key}\x00{canonical(rows[key])}\n" for key in sorted(rows))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def digest_entries(entries: Sequence[Entry]) -> str:
    """Digest of every committed row in stream order.

    Unlike :func:`digest_rows`, history counts: two snapshots whose covered record
    ranges differ never collapse to the same digest, even when a key ends with the
    same value it had before.
    """
    payload = "".join(
        f"{entry.seq}\x00{entry.kind.value}\x00{entry.key}\x00"
        f"{entry.batch_id}\x00{entry.generation}\x00{canonical(entry.value)}\x00"
        f"{canonical(entry.reason)}\n"
        for entry in entries
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Snapshot:
    """Frozen summary of the committed part of the stream.

    ``watermark`` states exactly how far into the record stream the snapshot
    reaches; the digest is computed over every committed row at or below it.
    """

    watermark: int
    digest: str
    keys: tuple[str, ...]
    count: int = 0

    def covers(self, seq: int) -> bool:
        """Whether a record at ``seq`` falls inside this snapshot's range."""
        return 1 <= seq <= self.watermark

    def to_dict(self) -> dict[str, Any]:
        return {
            "watermark": self.watermark,
            "count": self.count,
            "digest": self.digest,
            "keys": list(self.keys),
        }
