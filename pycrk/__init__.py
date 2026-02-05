#!/usr/bin/env python

from binascii import hexlify
import io
import logging
import os
import os.path
import re
from typing import Generator, Iterable, Iterator, List, Sequence


__log__ = logging.getLogger(__name__)

CHANGE_RE = re.compile(r"^([0-9a-f]+)\s*:\s*([0-9a-f]{2})\s+([0-9a-f]{2})$", re.I)

READ_BUFFER = 1024 * 4  # Read files in 4KB chunks


class InvalidFormat(ValueError):
    pass


class Change:
    """A single byte change to a file"""

    def __init__(self, offset: int, orig: int, patch: int):
        self.offset = offset
        self.orig = orig
        self.patch = patch

    def valid(self, fp) -> bool:
        """Check if this change is valid for the file"""
        fp.seek(self.offset)
        return fp.read(1)[0] in (self.orig, self.patch)

    def applied(self, fp) -> bool:
        """Checks if the change has been applied to the file"""
        fp.seek(self.offset)
        return fp.read(1)[0] == self.patch

    def apply(self, fp, unpatch=False) -> bool:
        """Applies the change to the file"""
        fp.seek(self.offset)
        return fp.write(bytes([self.orig if unpatch else self.patch])) == 1

    @classmethod
    def parse(cls, s) -> "Change":
        if not (m := CHANGE_RE.fullmatch(s)):
            raise InvalidFormat(f"'{s}' is not a valid change")
        return cls(
            offset=int(m[1], 16),
            orig=int(m[2], 16),
            patch=int(m[3], 16)
        )

    def __repr__(self) -> str:
        return "{}(offset={:08X}, orig={:02X}, patch={:02X})".format(
            self.__class__.__name__,
            self.offset,
            self.orig,
            self.patch
        )

    def serialize(self) -> str:
        """The change as it would appear in a crk file"""
        return "{:08X}: {:02X} {:02X}".format(
            self.offset,
            self.orig,
            self.patch
        )


class Patch:
    """A patch for a file"""

    def __init__(self, title: str, filename: str, changes: Sequence[Change]):
        self.title = title
        self.filename = filename
        self.changes = changes

    def __iter__(self) -> Iterator[Change]:
        return iter(self.changes)

    def valid(self, fp) -> bool:
        """Checks if the patch is valid for the file"""
        return all(c.valid(fp) for c in self)

    def applied(self, fp) -> bool:
        """Checks if the patch has been applied to the file"""
        return all(c.applied(fp) for c in self)

    def apply(self, fp, unpatch=False) -> bool:
        """Applies the patch to the file"""
        applied = True
        for c in self:
            applied &= c.apply(fp, unpatch=unpatch)
        return applied

    @classmethod
    def from_lines(cls, lines) -> "Patch":
        lines_stripped = iter(_strip_comments(lines))
        try:
            title = next(lines_stripped)
            filename = next(lines_stripped)
            changes = [Change.parse(line) for line in lines_stripped]

            if not changes:
                raise ValueError("No changes specified")

            return cls(title, filename, changes)

        except (StopIteration, ValueError) as e:
            raise InvalidFormat(
                "Invalid patch:\n```\n{}\n```".format("\n".join(lines))
            ) from e

    def __repr__(self) -> str:
        return '{}("{}", filename={}, changes={})'.format(
            self.__class__.__name__,
            self.title,
            self.filename,
            self.changes
        )

    def serialize(self) -> str:
        """Serialize the patch for inclusion in a crk file"""
        title = "\n;".join(self.title.splitlines())
        return "{}\n{}\n{}\n{}".format(
            title,
            self.filename,
            ";" + "-" * (max(map(len, title.splitlines())) - 1),
            "\n".join(x.serialize() for x in self.changes)
        )


class Crk:
    """Bundles up multiple patches"""

    def __init__(self, title: str, patches: Sequence[Patch]):
        self.title = title
        self.patches = patches

    def __iter__(self) -> Iterator[Patch]:
        return iter(self.patches)

    @staticmethod
    def _get_sections(lines: Iterable[str]) -> Generator[List[str], None, None]:
        """Yield lists of lines within sections. Sections are newline-separated"""
        eof = False
        i = iter(lines)
        while not eof:
            current = []
            started = False
            for line in i:
                line = line.strip()
                if not line:
                    if not started:
                        continue
                    break
                started = True
                current.append(line)
            else:
                eof = True

            if current:
                yield current

    @classmethod
    def from_lines(cls, lines) -> "Crk":
        sections = cls._get_sections(lines)
        try:
            title = "\n".join(_strip_comments(next(sections)))
        except StopIteration as e:
            raise InvalidFormat(
                "Invalid Crk:\n```\n{}\n```".format("\n".join(lines))
            ) from e

        patches = []
        for section in sections:
            try:
                patches.append(Patch.from_lines(section))
            except InvalidFormat:
                __log__.warning(
                    "Ignoring invalid patch:\n```\n%s\n```", "\n".join(section)
                )
        return cls(title, patches)

    @classmethod
    def from_file(cls, file) -> "Crk":
        return cls.from_lines(file.readlines())

    @classmethod
    def from_path(cls, path) -> "Crk":
        with open(path, "rt") as fp:
            return cls.from_file(fp)

    @classmethod
    def from_ips_with_file(cls, ips: "IPSPatch", file, filename=None):
        filename = filename or getattr(file, "name", ips.filename)
        if not filename:
            raise ValueError("A CRK file requires the name of the file to patch")

        changes = []
        for r in ips.records:
            file.seek(r.offset)
            orig_data = file.read(len(r.patch))

            if len(r.patch) != len(orig_data):
                raise ValueError(
                    f"IPS patch does not apply to '{filename}' - the file is too small"
                )

            for i, (b1, b2) in enumerate(zip(orig_data, r.patch)):
                if b1 != b2:
                    changes.append(Change(offset=r.offset + i, orig=b1, patch=b2))

        if not changes:
            raise ValueError("IPS patch didn't specify any changes (is the file already patched?)")

        return cls(
            title=f"Patch for {filename}",
            patches=[
                Patch(
                    title=f"Patch {len(changes)} bytes in {filename}",
                    filename=filename,
                    changes=changes,
                )
            ]
        )

    @classmethod
    def from_ips_with_path(cls, ips: "IPSPatch", path):
        with open(path, "rb") as fp:
            return cls.from_ips_with_file(ips, fp)

    def __repr__(self) -> str:
        return '{}("{}", patches={})'.format(
            self.__class__.__name__,
            self.title,
            self.patches
        )

    def serialize(self) -> str:
        """Serialize to a crk file"""
        return "{}\n\n{}".format(
            "\n;".join(self.title.splitlines()),
            "\n\n".join(x.serialize() for x in self.patches)
        )


class IPSRecord:
    def __init__(self, offset: int, patch: bytes):
        self.offset = offset
        self.patch = patch

    def __repr__(self) -> str:
        return "{}(offset={:08X}, patch={})".format(
            self.__class__.__name__,
            self.offset,
            hexlify(self.patch).decode()
        )

    @classmethod
    def from_crk_patch(cls, patch: Patch) -> Iterable["IPSRecord"]:
        """Make IPSRecords from a CRK Patch"""
        changes = iter(sorted(patch.changes, key=lambda c: c.offset))

        # preload first change to make later logic easier
        c = next(changes, None)
        if c is None:
            return
        curr_data = [c.patch]
        curr_offset = c.offset
        prev_offset = c.offset

        for c in changes:
            # switch to a new IPS record once the patch skips a byte or get too big
            if c.offset != prev_offset + 1 or len(curr_data) >= 65535:
                yield cls(offset=curr_offset, patch=bytes(curr_data))

                curr_offset = c.offset
                curr_data.clear()
            curr_data.append(c.patch)
            prev_offset = c.offset

        yield cls(offset=curr_offset, patch=bytes(curr_data))

    @classmethod
    def from_file(cls, file) -> "IPSRecord":
        def _read(s):
            d = file.read(s)
            if len(d) < s:
                raise ValueError("Failed to parse IPS record - not enough data")
            return d

        offset = int.from_bytes(_read(3), byteorder="big")
        size = int.from_bytes(_read(2), byteorder="big")
        if size == 0:
            size = int.from_bytes(_read(2), byteorder="big")
            data = _read(1) * size
        else:
            data = _read(size)
        return cls(offset=offset, patch=data)

    def serialize(self) -> bytes:
        if len(self.patch) > 3 and all(x == self.patch[0] for x in self.patch):
            # optimize with run-length encoding
            return (
                self.offset.to_bytes(3, byteorder="big") +
                bytes(2) +
                len(self.patch).to_bytes(2, byteorder="big") +
                bytes([self.patch[0]])
            )
        return (
            self.offset.to_bytes(3, byteorder="big") +
            len(self.patch).to_bytes(2, byteorder="big") +
            self.patch
        )


class IPSPatch:
    def __init__(self, records: Sequence[IPSRecord], filename=None):
        self.records = records
        self.filename = filename

    @classmethod
    def from_crk(cls, crk: Crk) -> Iterable["IPSPatch"]:
        """Make IPSPatches from a Crk"""
        records = []
        curr_file = None
        for p in sorted(crk.patches, key=lambda p: p.filename):
            if curr_file is None:
                curr_file = p.filename
            if curr_file != p.filename and records:
                yield cls(records=records, filename=curr_file)
                records = []
                curr_file = p.filename
            records.extend(IPSRecord.from_crk_patch(p))

        if records:
            yield cls(records=records, filename=curr_file)

    @classmethod
    def from_file(cls, file) -> "IPSPatch":
        if file.read(5) != b"PATCH":
            raise InvalidFormat("IPS patch missing header")

        records = []
        # peek 4 bytes while checking for EOF to make sure we hit the end of the
        # file and not just a record with an offset of 0x454F46 ("EOF" in ascii)
        while (d := _peek(file, 4)) and d != b"EOF":
            records.append(IPSRecord.from_file(file))

        eof = file.read()
        if eof != b"EOF":
            __log__.warning("Incorrect data and end of IPS file: %r", eof)

        return cls(records=records)

    @classmethod
    def from_bytes(cls, data: bytes) -> "IPSPatch":
        return cls.from_file(io.BytesIO(data))

    @classmethod
    def from_path(cls, path) -> "IPSPatch":
        with open(path, "rb") as fp:
            return cls.from_file(fp)

    def __repr__(self) -> str:
        return '{}(records={})'.format(
            self.__class__.__name__,
            self.records,
        )

    def serialize(self) -> bytes:
        return (
            b"PATCH" +
            b"".join(r.serialize() for r in self.records) +
            b"EOF"
        )


def _peek(fp, size):
    """Peek at the next size bytes of fp"""
    pos = fp.tell()
    try:
        data = fp.read(size)
    finally:
        fp.seek(pos)
    return data


def _strip_comments(lines: Iterable[str]) -> Generator[str, None, None]:
    """Strip comments off lines and yield back non-empty ones"""
    for line in lines:
        if l := line.split(";", 1)[0].strip():
            yield l


def _walk_files(directory: os.PathLike):
    """Yield all files in a directory relative to the starting dir"""
    for root, _, files in os.walk(directory):
        for f in files:
            yield os.path.relpath(os.path.join(root, f), start=directory)


def _find_changes(original: os.PathLike, patched: os.PathLike) -> List[Change]:
    """Get a list of Change objects based on two files"""

    changes = []
    with open(original, "rb") as fp1, open(patched, "rb") as fp2:
        offset = 0

        while True:
            d1 = fp1.read(READ_BUFFER)
            d2 = fp2.read(READ_BUFFER)

            if len(d1) != len(d2):
                raise ValueError("Files are not the same size - can't diff them")

            if not d1:
                break

            for i, (b1, b2) in enumerate(zip(d1, d2)):
                if b1 != b2:
                    changes.append(Change(
                        offset=offset + i,
                        orig=b1,
                        patch=b2
                    ))

            offset += len(d1)

    return changes


def make_file_crk(original: os.PathLike, patched: os.PathLike) -> Crk:
    """Generate a Crk object from the differences between two files"""
    for x in (original, patched):
        if not os.path.exists(x):
            raise ValueError(f"Path '{x}' does not exist")
        if not os.path.isfile(x):
            raise ValueError(f"Path '{x}' is not a file")

    if not (changes := _find_changes(original, patched)):
        raise ValueError("Files are the same")

    name = os.path.basename(patched)
    return Crk(
        title=f"Patch for {name}",
        patches=[
            Patch(
                title=f"Patch {len(changes)} bytes in {name}",
                filename=name,
                changes=changes
            )
        ]
    )


def make_dir_crk(original_dir: os.PathLike, patched_dir: os.PathLike) -> Crk:
    """Generate a Crk object from the differences between two directories"""
    for x in (original_dir, patched_dir):
        if not os.path.exists(x):
            raise ValueError(f"Path '{x}' does not exist")
        if not os.path.isdir(x):
            raise ValueError(f"Path '{x}' is not a directory")

    original, patched = (set(_walk_files(x)) for x in (original_dir, patched_dir))

    if diff := original ^ patched:
        __log__.warning(
            "Ignoring the following files not common to both directories: %s",
            diff
        )

    num_files = 0
    patches = []
    for path in original & patched:
        num_files += 1
        try:
            if not (changes := _find_changes(
                os.path.join(original_dir, path),
                os.path.join(patched_dir, path)
            )):
                continue

            name = os.path.basename(path)
            patches.append(
                Patch(
                    title=f"Patch {len(changes)} bytes in {name}",
                    filename=path,
                    changes=changes
                )
            )
        except ValueError as e:
            __log__.warning("Skipping %s: %s", path, e)

    if not num_files:
        raise ValueError("No files to compare discovered")
    if not patches:
        raise ValueError(f"All {num_files} files are the same")

    head, dirname = os.path.split(original_dir)
    if not dirname:
        dirname = os.path.basename(head)
    return Crk(
        title=f"Patch for {len(patches)} files in `{dirname}`",
        patches=patches
    )
