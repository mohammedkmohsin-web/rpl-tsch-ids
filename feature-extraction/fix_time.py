"""
Normalize Cooja log timestamps to the MM:SS.mmm format expected by
make_network_dataset.py.

Some Cooja runs emit integer microsecond timestamps at the start of each
line (for example "16191000 ID:4 ...") instead of the "00:16.191  ID:4 ..."
minute:second.millisecond format. Feeding the microsecond format directly
into make_network_dataset.py silently yields zero windows. This script
rewrites the affected files in place.

Usage:
    python3 fix_time.py FILE1.txt FILE2.txt ...
"""

import re
import sys


def convert(path):
    out = []
    changed = False
    for line in open(path):
        m = re.match(r'^(\d+)\s+ID:(.*)$', line)
        if m:
            micros = int(m.group(1))
            total_s = micros / 1_000_000.0
            mm = int(total_s // 60)
            ss = total_s - mm * 60
            out.append(f"{mm:02d}:{ss:06.3f}\tID:{m.group(2)}\n")
            changed = True
        else:
            out.append(line)
    open(path, 'w').writelines(out)
    print(f"Converted {path}" if changed else f"No change needed: {path}")


if __name__ == '__main__':
    files = sys.argv[1:]
    if not files:
        print("Usage: python3 fix_time.py FILE1.txt FILE2.txt ...")
        sys.exit(1)
    for f in files:
        convert(f)
