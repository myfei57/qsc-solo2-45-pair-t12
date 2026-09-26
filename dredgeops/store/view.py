"""Read-only projections of the record stream, current or frozen at a watermark."""

from typing import Any, Collection, Sequence

from .entry import Entry, EntryKind
from .snapshot import digest_entries, digest_rows


class CommittedView:
    """Latest committed value per key, optionally frozen at an earlier watermark."""

    def __init__(
        self,
        entries: Sequence[Entry],
        watermark: int,
        aborted: Collection[str] = (),
    ) -> None:
        self._watermark = watermark
        self._visible: list[Entry] = []
        self._rows: dict[str, Entry] = {}
        for entry in entries:
            if entry.seq > watermark or entry.batch_id in aborted:
                continue
            self._visible.append(entry)
            if entry.kind is EntryKind.TOMBSTONE:
                self._rows.pop(entry.key, None)
            else:
                self._rows[entry.key] = entry

    @property
    def watermark(self) -> int:
        return self._watermark

    def keys(self, prefix: str = "") -> tuple[str, ...]:
        return tuple(sorted(key for key in self._rows if key.startswith(prefix)))

    def rows(self) -> dict[str, Any]:
        return {key: entry.value for key, entry in self._rows.items()}

    def entries(self) -> tuple[Entry, ...]:
        """Every committed row this view covers, in stream order."""
        return tuple(self._visible)

    def digest(self) -> str:
        return digest_rows(self.rows())

    def snapshot_digest(self) -> str:
        """Digest of the whole covered range, not just the latest value per key."""
        return digest_entries(self._visible)
