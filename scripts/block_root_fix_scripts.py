#!/usr/bin/env python3
"""Pre-commit hook to block root-level fix/apply scripts."""
import sys
import re
import os


def main():
    staged = sys.argv[1:]
    blocked = []
    for f in staged:
        # Only check files at repository root (no directory separator)
        if os.path.basename(f) == f:  # no path separators
            if re.match(r'^(fix.*|apply_).*\.py$', f):
                blocked.append(f)

    if blocked:
        print(f'ERROR: Root-level fix/apply scripts are not allowed: {blocked}')
        print('Move them to a subdirectory or rename them.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
