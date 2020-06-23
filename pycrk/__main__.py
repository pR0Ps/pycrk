import argparse
import logging
import os
from typing import Optional

from pycrk import Crk


def parse_args():
    parser = argparse.ArgumentParser(description="Applies patches from CRK files")
    parser.add_argument("file", help="The CRK file to use")
    parser.add_argument(
        "--wd", help="The directory that holds the file(s) to patch", default="."
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

    return vars(parser.parse_args())


def process_crk(
    file: str, wd: str = ".", ask: bool = False, apply: Optional[bool] = None
) -> None:
    """Process the CRK file

    ask: if true, will ask before (un)applying patches
    apply: False=unpatch, None=show, True=patch
    """
    crk = Crk.from_file(file)

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
        path = os.path.join(wd, patch.filename)
        if not os.path.isfile(path):
            msg("NO FILE", patch)
            continue
        with open(path, "r+b") as f:
            if not patch.valid(f):
                msg("INVALID", patch)
            elif (patched := patch.applied(f)) == apply or apply is None:
                msg(actions[patched], patch)
            elif (
                not ask
                or input(f"{questions[apply]} '{patch.title}'? [y/N]: ").lower() == "y"
            ):
                patch.apply(f, unpatch=not apply)
                msg(actions[apply], patch)
            else:
                msg("SKIPPED", patch)


def main():
    logging.basicConfig(format="[%(levelname)8s] %(message)s", level=logging.ERROR)
    process_crk(**parse_args())


if __name__ == "__main__":
    main()
