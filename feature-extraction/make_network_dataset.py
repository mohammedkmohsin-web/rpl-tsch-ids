"""
Build a network-level feature dataset from Cooja FEATURES logs.

Each 30-second non-overlapping window is summarized into 21 network-wide
features (statistics aggregated across all active nodes in the window),
producing one labeled sample per window.

Usage:
    python3 make_network_dataset.py OUTPUT.csv FILE1:LABEL FILE2:LABEL ...

Labels used in this work:
    0 = benign, 1 = decreased rank, 2 = version number, 3 = DIS flooding
"""

import re
import sys
import csv
import numpy as np

PATTERN = re.compile(
    r'(\d+):(\d+)\.(\d+)\s+ID:(\d+).*?'
    r'FEATURES node=(\d+) rank=(\d+) parent=(\d+) rank_changes=(\d+) '
    r'tx=(\d+) rx=(\d+) missed=(\d+) routes=(\d+) tx_e=(\d+) rx_e=(\d+) '
    r'dio=(\d+) dis=(\d+) dao=(\d+) disrx=(\d+) version=(\d+)'
)

WINDOW_SEC = 30


def parse_file(path, label):
    records = []
    with open(path) as f:
        for line in f:
            m = PATTERN.search(line)
            if not m:
                continue
            g = m.groups()
            t = int(g[0]) * 60 + int(g[1])
            records.append({
                't': t, 'node': int(g[4]), 'rank': int(g[5]),
                'rank_changes': int(g[7]), 'tx': int(g[8]), 'rx': int(g[9]),
                'missed': int(g[10]), 'routes': int(g[11]),
                'txe': int(g[12]), 'rxe': int(g[13]), 'dio': int(g[14]),
                'dis': int(g[15]), 'dao': int(g[16]), 'disrx': int(g[17]),
                'version': int(g[18])
            })
    if not records:
        return []

    max_t = max(r['t'] for r in records)
    snapshots = []
    for w_start in range(0, max_t + 1, WINDOW_SEC):
        w_end = w_start + WINDOW_SEC
        window_recs = [r for r in records if w_start <= r['t'] < w_end]
        if len(window_recs) < 3:
            continue
        latest = {}
        for r in window_recs:
            latest[r['node']] = r
        nodes = list(latest.values())

        ranks = np.array([n['rank'] for n in nodes])
        rcs = np.array([n['rank_changes'] for n in nodes])
        diss = np.array([n['dis'] for n in nodes])
        dios = np.array([n['dio'] for n in nodes])
        disrxs = np.array([n['disrx'] for n in nodes])
        versions = np.array([n['version'] for n in nodes])
        txes = np.array([n['txe'] for n in nodes])
        rxes = np.array([n['rxe'] for n in nodes])
        pdrs = np.array([(n['rx'] / n['tx'] if n['tx'] > 0 else 1.0) for n in nodes])

        feat = [
            len(nodes),
            ranks.mean(), ranks.std(), ranks.max(), ranks.min(),
            rcs.mean(), rcs.std(), rcs.max(),
            diss.mean(), diss.std(), diss.max(),
            dios.mean(), dios.max(),
            disrxs.mean(), disrxs.max(),
            int(versions.max() - versions.min()),
            txes.mean(), txes.std(),
            rxes.mean(),
            pdrs.mean(), pdrs.min(),
        ]
        snapshots.append(feat + [label])
    return snapshots


if __name__ == '__main__':
    out_file = sys.argv[1]
    specs = sys.argv[2:]
    header = ['n_nodes', 'rank_mean', 'rank_std', 'rank_max', 'rank_min',
              'rc_mean', 'rc_std', 'rc_max', 'dis_mean', 'dis_std', 'dis_max',
              'dio_mean', 'dio_max', 'disrx_mean', 'disrx_max', 'version_spread',
              'txe_mean', 'txe_std', 'rxe_mean', 'pdr_mean', 'pdr_min', 'label']

    all_rows = []
    counts = {}
    for spec in specs:
        path, label = spec.rsplit(':', 1)
        label = int(label)
        rows = parse_file(path, label)
        all_rows.extend(rows)
        counts[label] = counts.get(label, 0) + len(rows)

    with open(out_file, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(all_rows)

    names = {0: 'benign', 1: 'decreased_rank', 2: 'version_number', 3: 'dis_flooding'}
    print(f"Total windows: {len(all_rows)}")
    for lbl in sorted(counts):
        print(f"  class {lbl} ({names.get(lbl, '?')}): {counts[lbl]} windows")
    print(f"Saved to: {out_file}")
