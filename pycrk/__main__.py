#!/usr/bin/env python

import argparse
import logging
import os
import sys
from typing import Optional

from pycrk import make_file_crk, make_dir_crk, Crk, IPSPatch


def generate_crk() -> None:
    """Generate a CRK file using two sets of file(s) and print it"""
    logging.basicConfig(format="[%(levelname)8s] %(message)s", level=logging.WARNING)

    parser = argparse.ArgumentParser(
        description="Generate a CRK patch from 2 files/directories"
    )
    parser.add_argument(
        "original",
        help="The original file/directory"
    )
    parser.add_argument(
        "patched",
        help="The patched file/directory"
    )
    parser.add_argument(
        "-o", "--output",
        metavar="<path>",
        help="Write generated CRK patch to <path> instead of stdout",
        type=argparse.FileType('w', encoding='utf-8'),
        default="-"
    )

    args = parser.parse_args()

    for x in (args.original, args.patched):
        if not os.path.exists(x):
            raise ValueError(f"Path '{x}' does not exist")

    original_file, patched_file = (os.path.isfile(x) for x in (args.original, args.patched))
    if original_file ^ patched_file:
        raise ValueError("The two inputs need to both be files or directories")

    if original_file:
        crk = make_file_crk(args.original, args.patched)
    else:
        crk = make_dir_crk(args.original, args.patched)

    # Ignore BrokenPipeErrors on output
    try:
        print(crk.serialize(), file=args.output)
        args.output.flush()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), args.output.fileno())
        sys.exit(128 + 13) # SIGPIPE


def apply_crk():
    logging.basicConfig(format="[%(levelname)8s] %(message)s", level=logging.WARNING)

    parser = argparse.ArgumentParser(description="Apply a CRK patch")
    parser.add_argument(
        "file",
        type=argparse.FileType('rt'),
        help="The CRK file to apply (use '-' for stdin)"
    )
    parser.add_argument(
        "--wd",
        help="The directory that contains the file(s) to patch (default: %(default)s)",
        default="."
    )
    parser.add_argument(
        "--ask",
        help="Ask to apply individual patches? (requires --patch/--unpatch)",
        action="store_true",
    )
    parser.add_argument(
        "--unpatch",
        help="Remove the patches (default: show patched/unpatched status)",
        dest="apply",
        action="store_false",
        default=None,
    )
    parser.add_argument(
        "--patch",
        help="Apply the patches (default: show patched/unpatched status)",
        dest="apply",
        action="store_true",
        default=None,
    )

    args = parser.parse_args()

    crk = Crk.from_file(args.file)

    filename_size = 0
    for patch in crk:
        l = len(patch.filename)
        if l > filename_size:
            filename_size = l

    questions = ["Remove", "Apply"]
    actions = ["UNPATCHED", "PATCHED"]

    def msg(status, patch):
        print(f"[{status:^9}] [{patch.filename:<{filename_size}}] {patch.title}")

    print(crk.title)
    print()
    for patch in crk:
        path = os.path.join(args.wd, patch.filename)
        if not os.path.isfile(path):
            msg("NO FILE", patch)
            continue
        with open(path, "r+b") as f:
            if not patch.valid(f):
                msg("INVALID", patch)
            elif (patched := patch.applied(f)) == args.apply or args.apply is None:
                msg(actions[patched], patch)
            elif (
                not args.ask
                or input(f"{questions[args.apply]} '{patch.title}'? [y/N]: ").lower() == "y"
            ):
                patch.apply(f, unpatch=not args.apply)
                msg(actions[args.apply], patch)
            else:
                msg("SKIPPED", patch)


def crk_to_ips():
    """Given a crk file, convert it into an IPS patch"""
    logging.basicConfig(format="[%(levelname)8s] %(message)s", level=logging.WARNING)

    parser = argparse.ArgumentParser(
        description="Convert a CRK patch to IPS patches"
    )
    parser.add_argument(
        "file",
        type=argparse.FileType('rt'),
        help="The CRK file to convert (use '-' for stdin)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        metavar="<directory>",
        help="Directory to write the IPS patch(es) into",
        default="."
    )

    args = parser.parse_args()

    crk = Crk.from_file(args.file)

    i = 0
    for ips in IPSPatch.from_crk(crk):
        filename = ips.filename
        if not ips.filename:
            i += 1
            filename = f"patch_{i}"
        path = os.path.join(args.output_dir, f"{filename}.ips")

        print(f"Writing IPS patch with {len(ips.records)} records to {path}")
        with open(path, "wb") as fp:
            fp.write(ips.serialize())


def crk_from_ips():
    """Given an IPS patch, convert it into a CRK"""
    logging.basicConfig(format="[%(levelname)8s] %(message)s", level=logging.WARNING)

    parser = argparse.ArgumentParser(
        description="Convert an IPS patch to a CRK patch"""
    )
    parser.add_argument(
        "file",
        type=argparse.FileType('rb'),
        help="The original unpatched file the IPS patch applies to"
    )
    parser.add_argument(
        "ips",
        type=argparse.FileType('rb'),
        help="The IPS file to convert (use '-' for stdin)"
    )
    parser.add_argument(
        "-o", "--output",
        metavar="<path>",
        help="Write generated CRK patch to <path> instead of stdout",
        type=argparse.FileType('wt'),
        default="-"
    )

    args = parser.parse_args()

    ips = IPSPatch.from_file(args.ips)
    crk = Crk.from_ips_with_file(ips, args.file, filename=os.path.basename(args.file.name))

    # Ignore BrokenPipeErrors on output
    try:
        print(crk.serialize(), file=args.output)
        args.output.flush()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), args.output.fileno())
        sys.exit(128 + 13) # SIGPIPE

if __name__ == "__main__":
    apply_crk()
