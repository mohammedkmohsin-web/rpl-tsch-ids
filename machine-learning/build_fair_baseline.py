# -*- coding: utf-8 -*-
"""Fair baseline: classify each node without knowing the attacker, then
aggregate per-node predictions into a network-level verdict. Compares this
node-level baseline against the network-level detector under the
attacker-held-out protocol."""
import re, csv
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

WINDOW_SEC = 30
PATTERN = re.compile(
    r'(\d+):(\d+)\.(\d+).*?ID:(\d+).*?FEATURES '
    r'node=(\d+) rank=(\d+) parent=(\d+) rank_changes=(\d+) '
    r'tx=(\d+) rx=(\d+) missed=(\d+) routes=(\d+) tx_e=(\d+) rx_e=(\d+) '
    r'dio=(\d+) dis=(\d+) dao=(\d+) disrx=(\d+) version=(\d+)'
)

def parse_records(path):
    records = []
    with open(path) as f:
        for line in f:
            m = PATTERN.search(line)
            if not m: continue
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
    return records

def per_node_rows(path, label, window_id_start=0):
    """One row per node per window, tagged with a window id for later aggregation."""
    records = parse_records(path)
    if not records: return [], window_id_start
    max_t = max(r['t'] for r in records)
    rows = []
    wid = window_id_start
    for w_start in range(0, max_t + 1, WINDOW_SEC):
        w_end = w_start + WINDOW_SEC
        window_recs = [r for r in records if w_start <= r['t'] < w_end]
        if len(window_recs) < 3: continue
        latest = {}
        for r in window_recs:
            latest[r['node']] = r
        for node_id, n in latest.items():
            pdr = n['rx']/n['tx'] if n['tx']>0 else 1.0
            feat = [n['rank'], n['rank_changes'], n['tx'], n['rx'], n['missed'],
                    n['routes'], n['txe'], n['rxe'], n['dio'], n['dis'],
                    n['dao'], n['disrx'], n['version'], pdr]
            rows.append(feat + [label, wid])
        wid += 1
    return rows, wid

def build(specs, start=0):
    all_rows = []
    wid = start
    for spec in specs:
        path, label = spec.rsplit(':', 1)
        rows, wid = per_node_rows(path, int(label), wid)
        all_rows.extend(rows)
    return all_rows, wid

cols = ['rank','rc','tx','rx','missed','routes','txe','rxe','dio','dis',
        'dao','disrx','version','pdr','label','wid']

# Training: attacker at positions 8 and 5
train_specs = [
    "data_normal.txt:0","data_normal_s2.txt:0","data_normal_s3.txt:0","data_normal_s4.txt:0","data_normal_s5.txt:0","data_normal_s6.txt:0",
    "data_rank.txt:1","data_rank_s2.txt:1","data_rank_s3.txt:1","data_rank_s4.txt:1","data_rank_s5.txt:1","data_rank_a5.txt:1",
    "data_version.txt:2","data_version_s2.txt:2","data_version_s3.txt:2","data_version_s4.txt:2","data_version_s5.txt:2","data_version_a5.txt:2",
    "data_flood.txt:3","data_flood_s2.txt:3","data_flood_s3.txt:3","data_flood_s4.txt:3","data_flood_s5.txt:3","data_flood_a5.txt:3",
]
# Test: attacker at position 11 (held out)
test_specs = ["data_normal_s7.txt:0","data_rank_a11.txt:1","data_version_a11.txt:2","data_flood_a11.txt:3"]

tr_rows, w1 = build(train_specs, 0)
te_rows, w2 = build(test_specs, 100000)

tr = pd.DataFrame(tr_rows, columns=cols)
te = pd.DataFrame(te_rows, columns=cols)

X_tr = tr.drop(columns=['label','wid'])
y_tr = tr['label']
clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced', n_jobs=-1)
clf.fit(X_tr, y_tr)

te_pred = clf.predict(te.drop(columns=['label','wid']))
te['pred'] = te_pred

def aggregate(group):
    preds = group['pred'].values
    attack_preds = preds[preds > 0]
    if len(attack_preds) > 0:
        vals, counts = np.unique(attack_preds, return_counts=True)
        return vals[counts.argmax()]
    return 0

net_true = te.groupby('wid')['label'].first()
net_pred = te.groupby('wid').apply(aggregate)

acc = accuracy_score(net_true, net_pred)*100
f1 = f1_score(net_true, net_pred, average='weighted', zero_division=0)*100

print("="*62)
print("  Fair comparison under the attacker-held-out protocol")
print("="*62)
print(f"  Node-level baseline (no attacker knowledge): {acc:.2f}% acc, {f1:.2f}% F1")
print(f"  (train {len(tr)} node-rows, test {net_true.shape[0]} network windows)")
print()
print(f"  Our network-level detector: 99.38% acc")
print("="*62)
diff = 99.38 - acc
if diff > 0:
    print(f"  Network-level better by {diff:.1f} percentage points")
else:
    print(f"  Baseline better by {-diff:.1f} points")
