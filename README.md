pycrk
=====

Applies/removes patches using the `.crk` format.


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
a lot of data changes or shifts around. Something like [xdelta](https://github.com/jmacd/xdelta)
would be better for these use cases.

Installation
------------
```
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv)$ pip install git+https://github.com/pR0Ps/pycrk.git
```

Usage
-----
```
$ pycrk --help
usage: pycrk [-h] [--wd WD] [--ask] [--unpatch] [--patch] file

Applies patches from CRK files

positional arguments:
  file        The CRK file to use

optional arguments:
  -h, --help  show this help message and exit
  --wd WD     The directory that holds the file(s) to patch
  --ask       Ask to apply individual patches? (requires --patch/--unpatch)
  --unpatch   Remove the patches (default: show patched/unpatched status)
  --patch     Apply the patches (default: show patched/unpatched status)
```

Format overview
---------------
The CRK format consists of a title, a blank line, then a series of patches, each separated by a
blank line. The individual patches consist of a title, filename and a series of offsets and changes.

Example:
```crk
This is an example CRK file
; Comments can be added anywhere using semicolons

Apply patch 1            ; The title of the first patch
file.ext                 ; The filename the patch applies to
00000000: FF AA          ; Change byte at 0x00000000 from 0xFF to 0xAA
0000000A: FF AA          ; Another change

; To start writing another patch, use a blank line
; (note: lines with comments are not considered "blank")
Apply patch 2
another_file.ext
00000001: 00 01

; Optionally many more patches
```

Generating CRK files
--------------------

This tool will probably grow the ability to generate `*.crk` files in the future. For the moment use the
tools below to generate the patch data and manually edit the result to conform to the CRK format.

### Windows
```powershell
# Note: when using Powershell `fc` is an alias for `Format-Custom` so `fc.exe` is required.
# In cmd.exe just `fc` will work.
fc.exe <file1> <file2>
```

### Unix
```bash
cmp -l <file1> <file2> | gawk '{printf "%08X: %02X %02X\n", $1-1, strtonum(0$2), strtonum(0$3)}'
```

The above commands will produce the `xxxxxxxx: yy zz` data. To convert this to the CRK format just
add a title, blank line, patch title, and the filename it applies to.

Take the output:
```
00000000: FF AA
0000000A: FF AA
```

and add information like so:
```crk
CRK title

Patch title
filename.ext
00000000: FF AA
0000000A: FF AA
```

License
=======
Licensed under the [Mozilla Public License, version 2.0](https://www.mozilla.org/en-US/MPL/2.0)
