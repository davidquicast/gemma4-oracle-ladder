"""Passes when no file added by the patch looks like a reproduction or debug script."""
import re
import sys

from _diff import changed

SCRATCH = re.compile(r"(^|/)(repro|reproduce|scratch|debug|tmp|temp)[^/]*$", re.I)
bad = [f for f in changed("A") if SCRATCH.search(f) or "/" not in f]
if bad:
    print("files that look like scratch work: " + ", ".join(bad))
    sys.exit(1)
