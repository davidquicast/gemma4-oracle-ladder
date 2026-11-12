"""Passes when the patch touches no test file and no test runner configuration."""
import sys

from _diff import changed, is_protected

bad = [f for f in changed() if is_protected(f)]
if bad:
    print("protected files in the patch: " + ", ".join(bad))
    sys.exit(1)
