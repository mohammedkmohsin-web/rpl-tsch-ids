# -*- coding: utf-8 -*-
"""Builds the network-level, grouped dataset used throughout the letter.

Each row is one 30-second window's network-level feature vector, tagged with
a 'group' column identifying the raw log file (simulation run) it came from.
This group tag is what lets every evaluation script split by run rather than
by window, avoiding the leakage a naive random split would introduce.

Usage: python3 build_grouped_dataset.py OUTPUT.csv
Run from the directory containing the raw-logs/ folder (or edit RAW_DIR).
"""
import re
import sys
import numpy as np
import pandas as pd

WINDOW_SEC = 30
RAW_DIR = "raw-logs"

PATTERN = re.compile(
    r'(\d+):(\d+)\.(\d+).*?ID:(\d+).*?FEATURES '
    r'node=(\d+) rank=(\d+) parent=(\d+) rank_changes=(\d+) '
    r'tx=(\d+) rx=(\d+) missed=(\d+) routes=(\d+) tx_e=(\d+) rx_e=(\d+) '
    r'dio=(\d+) dis=(\d+) dao=(\d+) disrx=(\d+) version=(\d+)'
)

FEATURE_COLUMNS = [
    'n_nodes', 'rank_mean', 'rank_std', 'rank_max', 'rank_min',
    'rc_mean', 'rc_std', 'rc_max', 'dis_mean', 'dis_std', 'dis_max',
    'dio_mean', 'dio_max', 'disrx_mean', 'disrx_max', 'version_spread',
    'txe_mean', 'txe_std', 'rxe_mean', 'pdr_mean', 'pdr_min',
]

FILES_10N = (
    [(f"data_normal{suf}.txt", 0) for suf in ["", "_s2", "_s3", "_s4", "_s5", "_s6", "_s7"]] +
    [(f"data_rank{suf}.txt", 1) for suf in ["", "_a5", "_a11", "_s2", "_s3", "_s4", "_s5"]] +
    [(f"data_version{suf}.txt", 2) for suf in ["", "_a5", "_a11", "_s2", "_s3", "_s4", "_s5"]] +
    [(f"data_flood{suf}.txt", 3) for suf in ["", "_a5", "_a11", "_s2", "_s3", "_s4", "_s5"]]
)


def parse_file(path, label, group, window_sec=WINDOW_SEC):
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
                'version': int(g[18]),
            })
    if not records:
        return []
    max_t = max(r['t'] for r in records)
    snapshots = []
    for w_start in range(0, max_t + 1, window_sec):
        window_recs = [r for r in records if w_start <= r['t'] < w_start + window_sec]
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
            txes.mean(), txes.std(), rxes.mean(),
            pdrs.mean(), pdrs.min(),
        ]
        snapshots.append(feat + [label, group])
    return snapshots


def build(files, raw_dir=RAW_DIR, window_sec=WINDOW_SEC):
    rows = []
    for fname, label in files:
        path = f"{raw_dir}/{fname}"
        rows.extend(parse_file(path, label, fname.replace('.txt', ''), window_sec))
    cols = FEATURE_COLUMNS + ['label', 'group']
    return pd.DataFrame(rows, columns=cols)


if __name__ == '__main__':
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'dataset_large_grouped.csv'
    df = build(FILES_10N)
    df.to_csv(out_path, index=False)
    print(f"Total windows: {len(df)}")
    print(df['label'].value_counts().sort_index())
    print(f"Saved to: {out_path}")
