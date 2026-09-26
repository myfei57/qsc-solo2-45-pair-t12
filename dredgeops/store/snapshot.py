"""Snapshot records that pin a digest to a commit watermark."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


def canonical(value: Any) -> str:
    """Stable textual form of a value, independent of mapping order."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest_rows(rows: Mapping[str, Any], watermark: int | None = None) -> str:
    """Digest of a set of committed rows.

    When a watermark is given it is folded into the digest, so identical rows at
    different stream positions no longer look like the same snapshot.
    """
    payload = "".join(f"{key}\x00{canonical(rows[key])}\n" for key in sorted(rows))
    if watermark is not None:
        payload = f"watermark\x00{watermark}\n{payload}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Snapshot:
    """Frozen summary of the committed part of the stream."""

    watermark: int
    digest: str
    keys: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "watermark": self.watermark,
            "digest": self.digest,
            "keys": list(self.keys),
        }
