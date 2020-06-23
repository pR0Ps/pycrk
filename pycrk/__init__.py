#!/usr/bin/env python

import logging
import re
from typing import Generator, Iterable, Iterator, List, Sequence

__log__ = logging.getLogger(__name__)


class InvalidFormat(ValueError):
    pass


CHANGE_RE = re.compile(r"^([0-9a-f]+)\s*:\s*([0-9a-f]{2})\s+([0-9a-f]{2})$", re.I)


class Change:
    """A single byte change to a file"""

    def __init__(self, offset: int, orig: bytes, patch: bytes):
        self.offset = offset
        self.orig = orig
        self.patch = patch

    def valid(self, fp) -> bool:
        """Check if this change is valid for the file"""
        fp.seek(self.offset)
        return fp.read(1) in (self.orig, self.patch)

    def applied(self, fp) -> bool:
        """Checks if the change has been applied to the file"""
        fp.seek(self.offset)
        return fp.read(1) == self.patch

    def apply(self, fp, unpatch=False) -> bool:
        """Applies the change to the file"""
        fp.seek(self.offset)
        return fp.write(self.orig if unpatch else self.patch) == 1

    @classmethod
    def parse(cls, s) -> "Change":
        if not (m := CHANGE_RE.fullmatch(s)):
            raise InvalidFormat(f"'{s}' is not a valid change")
        return cls(
            offset=int(m[1], 16), orig=bytes.fromhex(m[2]), patch=bytes.fromhex(m[3])
        )

    def __repr__(self) -> str:
        """Normal repr except the values are displayed in hex with the correct padding"""
        return f"{self.__class__.__name__}(offset={self.offset:08X}, orig={self.orig[0]:02X}, patch={self.patch[0]:02X})"


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
                'Invalid patch:\n"""\n{}\n"""'.format("\n".join(lines))
            ) from e

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self.title}", filename={self.filename}, changes={self.changes})'


class Crk:
    """Bundles up multiple patches"""

    def __init__(self, title: str, patches: Sequence[Patch]):
        self.title = title
        self.patches = patches

    def __iter__(self) -> Iterator[Patch]:
        return iter(self.patches)

    @classmethod
    def from_lines(cls, lines) -> "Crk":
        sections = _get_sections(lines)
        title = "\n".join(_strip_comments(next(sections)))
        patches = []
        for section in sections:
            try:
                patches.append(Patch.from_lines(section))
            except InvalidFormat:
                __log__.warning(
                    'Ignoring invalid patch:\n"""\n%s\n"""', "\n".join(section)
                )
        return cls(title, patches)

    @classmethod
    def from_file(cls, filename) -> "Crk":
        with open(filename, "rt") as f:
            return cls.from_lines(f.readlines())

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self.title}", patches={self.patches})'


def _strip_comments(lines: Iterable[str]) -> Generator[str, None, None]:
    """Strip comments off lines and yield back non-empty ones"""
    for line in lines:
        if l := line.split(";", 1)[0].strip():
            yield l


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
