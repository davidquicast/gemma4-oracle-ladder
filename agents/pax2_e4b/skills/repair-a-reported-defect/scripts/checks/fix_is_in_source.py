"""Passes when the patch changes at least one non-test .py file."""
import sys

from _diff import changed, is_protected

source = [f for f in changed() if f.endswith(".py") and not is_protected(f)]
if not source:
    print("the patch changes no non-test .py file")
    sys.exit(1)
