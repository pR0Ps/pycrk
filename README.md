pycrk
=====

Generates/applies/removes patches in `.crk` format.


Why use CRK?
------------

The CRK format is a text-based binary diff that is human-readable and requires no special tooling to
create, read, or apply. Due to the format's text-based nature, CRK files can easily be stored in
source control. They can also contain comments, making them easier to understand/maintain.

Unlike other patch formats which are all-or-nothing, CRK files can include many independent patches,
allowing the user to only apply the ones they care about.

The format is a relic from the software pirates of the BBS days. Groups would distribute their
cracks for software as `*.CRK` files. Some used specialized programs for applying them while others
just manually applied the patches using a hex editor.

Personally, I came across this format while looking for a way to distribute byte-patches to an
executable file. I wanted the file to be human-readable and to be able to document the patches with
comments. As far as I can tell, there is no modern format for doing this.


Why not?
--------
The CRK format is a poor format for something like program updates, ROM hacks, or other cases where
a lot of data changes or shifts around. It also only works for in-place patches where the size of
the file stays the same.


Format overview
---------------
The CRK format consists of a title, a blank line, then a series of patches, each separated by a
blank line. The individual patches consist of a title, filename and a series of offsets and changes.

Example:
```
This is an example CRK file
; Comments can be added anywhere using semicolons

Apply patch 1            ; The title of the first patch
file.ext                 ; The filename the patch applies to
00000000: FF AA          ; Change byte at 0x00000000 from 0xFF to 0xAA
0000000A: 01 02          ; Change byte at 0x0000000A from 0x01 to 0x02

; To start writing another patch, use a blank line
; (note: lines with comments are not considered "blank")
Apply patch 2
another_file.ext
00000001: 00 01

; Optionally many more patches
```


Installation
------------
```
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv)$ pip install git+https://github.com/pR0Ps/pycrk.git
```


Applying patches from CRK files
------------------------------

The included `crk-apply` script applies CRK patches. When given a CRK patch and no other options it
will show a list of patches and if they have been applied to files in the working directory or not.
To have it make changes to the files, use the `--patch` or `--unpatch` flags. Using `--ask`
interactively asks about each individual patch.

```
$ crk-apply --help
usage: crk-apply [-h] [--wd WD] [--ask] [--unpatch] [--patch] file

Apply a CRK patch

positional arguments:
  file        The CRK file to apply (use '-' for stdin)

optional arguments:
  -h, --help  show this help message and exit
  --wd WD     The directory that contains the file(s) to patch (default: .)
  --ask       Ask to apply individual patches? (requires --patch/--unpatch)
  --unpatch   Remove the patches (default: show patched/unpatched status)
  --patch     Apply the patches (default: show patched/unpatched status)
```

Generating CRK files
--------------------

The included `crk-generate` script generates a CRK patch by comparing the differences in two files
or directories. By default the resulting CRK patch will be written to stdout.

```
$ crk-generate --help
usage: crk-generate [-h] [-o <path>] original patched

Generate a CRK patch from 2 files/directories

positional arguments:
  original              The original file/directory
  patched               The patched file/directory

optional arguments:
  -h, --help            show this help message and exit
  -o <path>, --output <path>
                        Write generated CRK patch to <path> instead of stdout
```

License
=======
Licensed under the [Mozilla Public License, version 2.0](https://www.mozilla.org/en-US/MPL/2.0)
