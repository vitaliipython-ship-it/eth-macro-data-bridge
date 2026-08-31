"""Qualified DATA_ROOT immutable filesystem adapter for the bounded F5 slice."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from server.storage.ports import ImmutableObjectConflict, ImmutableObjectEvidence


class QualifiedDataRootImmutableFilesystem:
    """Bounded immutable-object adapter rooted under the declared F5 DATA_ROOT."""

    def __init__(self, data_root: str | Path) -> None:
        """Bind the canonical domain-object namespace below DATA_ROOT/objects."""
        self.data_root = Path(data_root)
        self._storage_root = self.data_root / "objects"
        self._probe_identity_digest: str | None = None

    @classmethod
    def for_readiness_probe(cls, data_root: str | Path, probe_identity: str) -> "QualifiedDataRootImmutableFilesystem":
        """Create the same storage seam in a dedicated non-domain probe namespace."""
        if not probe_identity.startswith("readiness:f5:v1:"):
            raise ValueError("readiness probe identity must be explicitly non-domain")
        instance = cls(data_root)
        token = hashlib.sha256(probe_identity.encode("utf-8")).hexdigest()
        instance._storage_root = instance.data_root / ".aife-readiness" / token
        instance._probe_identity_digest = token
        return instance

    @staticmethod
    def _validate_digest(digest: str) -> str:
        """Validate a lowercase/uppercase SHA-256 identity and return lowercase form."""
        normalized = digest.lower()
        if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
            raise ValueError("sha256 digest required")
        return normalized

    def locator(self, digest: str) -> Path:
        """Resolve implementation-only physical locator for one content digest."""
        normalized = self._validate_digest(digest)
        return self._storage_root / "sha256" / normalized[:2] / normalized

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        """Durably flush directory-entry changes for a local qualified filesystem."""
        directory_fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    def write_immutable(self, payload: bytes, *, expected_digest: str | None = None) -> ImmutableObjectEvidence:
        """Durably create immutable bytes without overwriting an existing target."""
        digest = hashlib.sha256(payload).hexdigest()
        if expected_digest is not None and self._validate_digest(expected_digest) != digest:
            raise ImmutableObjectConflict("payload digest differs from expected identity")
        target = self.locator(digest)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return self.readback_verify(digest, expected_size=len(payload))

        descriptor, temporary_name = tempfile.mkstemp(prefix="." + digest + ".", dir=target.parent)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())

            # Same-filesystem hard-link creation is an atomic create-if-absent operation:
            # it cannot replace an existing name, unlike portable os.rename/os.replace.
            try:
                os.link(temporary_path, target)
            except FileExistsError:
                pass
            finally:
                temporary_path.unlink(missing_ok=True)

            self._fsync_directory(target.parent)
            return self.readback_verify(digest, expected_size=len(payload))
        finally:
            temporary_path.unlink(missing_ok=True)

    def read_exact(self, content_digest: str) -> bytes:
        """Read exact bytes using a new independent file handle."""
        with self.locator(content_digest).open("rb") as handle:
            return handle.read()

    def readback_verify(self, content_digest: str, *, expected_size: int) -> ImmutableObjectEvidence:
        """Independently recompute SHA-256 and size through a new read handle."""
        digest = self._validate_digest(content_digest)
        path = self.locator(digest)
        hasher = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                hasher.update(chunk)
        if size != expected_size or hasher.hexdigest() != digest:
            raise ImmutableObjectConflict("independent readback identity mismatch")
        return ImmutableObjectEvidence(digest, size, path.relative_to(self.data_root).as_posix())

    def cleanup_readiness_probe(self, content_digest: str) -> None:
        """Delete only an object created inside this dedicated readiness namespace."""
        if self._probe_identity_digest is None:
            raise RuntimeError("readiness cleanup is forbidden for the domain object namespace")
        target = self.locator(content_digest)
        target.unlink(missing_ok=True)
        self._fsync_directory(target.parent)

        # Remove only empty directories below the unique probe namespace.  Never recurse
        # into DATA_ROOT/objects or any sibling probe namespace.
        for path in (target.parent, target.parent.parent, self._storage_root):
            try:
                path.rmdir()
            except OSError:
                break
        readiness_root = self.data_root / ".aife-readiness"
        try:
            readiness_root.rmdir()
        except OSError:
            pass
