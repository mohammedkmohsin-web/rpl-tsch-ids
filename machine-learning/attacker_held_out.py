# -*- coding: utf-8 -*-
"""Reproduces Table V (attacker-held-out generalization across three
positions) and the fair node-level baseline comparison from the letter.

For each of the three attacker positions (5, 8, 11), trains the Random
Forest on the other two positions and tests exclusively on attacks
originating from the position withheld. The node-level baseline is
evaluated under the identical partition: it classifies each node
independently from fourteen per-node features and raises a network-level
alarm when any node is flagged, without assuming which node is malicious.

Usage: python3 attacker_held_out.py
Run from the directory containing the raw-logs/ folder (or edit RAW_DIR).
"""
import re
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

RAW_DIR = "raw-logs"
WINDOW_SEC = 30

PATTERN = re.compile(
    r'(\d+):(\d+)\.(\d+).*?ID:(\d+).*?FEATURES '
    r'node=(\d+) rank=(\d+) parent=(\d+) rank_changes=(\d+) '
    r'tx=(\d+) rx=(\d+) missed=(\d+) routes=(\d+) tx_e=(\d+) rx_e=(\d+) '
    r'dio=(\d+) dis=(\d+) dao=(\d+) disrx=(\d+) version=(\d+)'
)

CLASS_NAMES = ['Benign', 'Decreased Rank', 'Version Number', 'DIS Flooding']

BENIGN_TRAIN = ['data_normal.txt', 'data_normal_s2.txt', 'data_normal_s3.txt',
                'data_normal_s4.txt', 'data_normal_s5.txt']
BENIGN_TEST = ['data_normal_s6.txt', 'data_normal_s7.txt']

ATTACK_FILES = {
    1: ['data_rank.txt', 'data_rank_s2.txt', 'data_rank_s3.txt', 'data_rank_s4.txt',
        'data_rank_s5.txt', 'data_rank_a5.txt', 'data_rank_a11.txt'],
    2: ['data_version.txt', 'data_version_s2.txt', 'data_version_s3.txt', 'data_version_s4.txt',
        'data_version_s5.txt', 'data_version_a5.txt', 'data_version_a11.txt'],
    3: ['data_flood.txt', 'data_flood_s2.txt', 'data_flood_s3.txt', 'data_flood_s4.txt',
        'data_flood_s5.txt', 'data_flood_a5.txt', 'data_flood_a11.txt'],
}


def position_of(fname):
    if fname.endswith('_a5.txt'):
        return 5
    if fname.endswith('_a11.txt'):
        return 11
    return 8


def parse_records(path):
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
    return records


def network_windows(path, label, window_sec=WINDOW_SEC):
    records = parse_records(path)
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
            len(nodes), ranks.mean(), ranks.std(), ranks.max(), ranks.min(),
            rcs.mean(), rcs.std(), rcs.max(), diss.mean(), diss.std(), diss.max(),
            dios.mean(), dios.max(), disrxs.mean(), disrxs.max(),
            int(versions.max() - versions.min()), txes.mean(), txes.std(), rxes.mean(),
            pdrs.mean(), pdrs.min(),
        ]
        snapshots.append(feat + [label])
    return snapshots


def per_node_rows(path, label, window_id_start, window_sec=WINDOW_SEC):
    records = parse_records(path)
    if not records:
        return [], window_id_start
    max_t = max(r['t'] for r in records)
    rows = []
    wid = window_id_start
    for w_start in range(0, max_t + 1, window_sec):
        window_recs = [r for r in records if w_start <= r['t'] < w_start + window_sec]
        if len(window_recs) < 3:
            continue
        latest = {}
        for r in window_recs:
            latest[r['node']] = r
        for node_id, n in latest.items():
            pdr = n['rx'] / n['tx'] if n['tx'] > 0 else 1.0
            feat = [n['rank'], n['rank_changes'], n['tx'], n['rx'], n['missed'],
                    n['routes'], n['txe'], n['rxe'], n['dio'], n['dis'],
                    n['dao'], n['disrx'], n['version'], pdr]
            rows.append(feat + [label, wid])
        wid += 1
    return rows, wid


def build_network(specs, raw_dir=RAW_DIR):
    cols = ['n_nodes', 'rank_mean', 'rank_std', 'rank_max', 'rank_min', 'rc_mean', 'rc_std', 'rc_max',
            'dis_mean', 'dis_std', 'dis_max', 'dio_mean', 'dio_max', 'disrx_mean', 'disrx_max',
            'version_spread', 'txe_mean', 'txe_std', 'rxe_mean', 'pdr_mean', 'pdr_min', 'label']
    rows = []
    for fname, label in specs:
        rows.extend(network_windows(f"{raw_dir}/{fname}", label))
    return pd.DataFrame(rows, columns=cols)


def build_node(specs, raw_dir=RAW_DIR, start=0):
    cols = ['rank', 'rc', 'tx', 'rx', 'missed', 'routes', 'txe', 'rxe', 'dio', 'dis',
            'dao', 'disrx', 'version', 'pdr', 'label', 'wid']
    rows, wid = [], start
    for fname, label in specs:
        r, wid = per_node_rows(f"{raw_dir}/{fname}", label, wid)
        rows.extend(r)
    return pd.DataFrame(rows, columns=cols), wid


def aggregate_node_predictions(group):
    preds = group['pred'].values
    attack_preds = preds[preds > 0]
    if len(attack_preds) > 0:
        vals, counts = np.unique(attack_preds, return_counts=True)
        return vals[counts.argmax()]
    return 0


if __name__ == '__main__':
    results_net, results_node = {}, {}
    print("=" * 70)
    print("  Table V: attacker-held-out generalization across three positions")
    print("=" * 70)
    for held_out in [5, 11, 8]:
        train_specs = [(f, 0) for f in BENIGN_TRAIN]
        test_specs = [(f, 0) for f in BENIGN_TEST]
        for label, files in ATTACK_FILES.items():
            for fn in files:
                (test_specs if position_of(fn) == held_out else train_specs).append((fn, label))

        tr = build_network(train_specs)
        te = build_network(test_specs)
        clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced', n_jobs=1)
        clf.fit(tr.drop(columns=['label']), tr['label'])
        pred = clf.predict(te.drop(columns=['label']))
        acc = accuracy_score(te['label'], pred) * 100
        f1 = f1_score(te['label'], pred, average='weighted') * 100
        results_net[held_out] = (len(tr), len(te), acc, f1)
        print(f"  Position {held_out} held out (network-level): train={len(tr)} test={len(te)} "
              f"Acc={acc:.2f}% F1={f1:.2f}%")

        tr_node, _ = build_node(train_specs, start=0)
        te_node, _ = build_node(test_specs, start=100000)
        clf_node = RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced', n_jobs=1)
        clf_node.fit(tr_node.drop(columns=['label', 'wid']), tr_node['label'])
        te_node = te_node.copy()
        te_node['pred'] = clf_node.predict(te_node.drop(columns=['label', 'wid']))
        net_true = te_node.groupby('wid')['label'].first()
        net_pred = te_node.groupby('wid').apply(aggregate_node_predictions)
        acc_b = accuracy_score(net_true, net_pred) * 100
        f1_b = f1_score(net_true, net_pred, average='weighted', zero_division=0) * 100
        results_node[held_out] = (len(tr_node), net_true.shape[0], acc_b, f1_b)
        print(f"  Position {held_out} held out (node-level baseline): "
              f"Acc={acc_b:.2f}% F1={f1_b:.2f}%")
        print()

    net_accs = [v[2] for v in results_net.values()]
    node_accs = [v[2] for v in results_node.values()]
    print("=" * 70)
    print(f"  Mean network-level accuracy: {np.mean(net_accs):.2f}%")
    print(f"  Mean node-level baseline accuracy: {np.mean(node_accs):.2f}%")
    print(f"  Mean gap: {np.mean(net_accs) - np.mean(node_accs):.1f} points")
