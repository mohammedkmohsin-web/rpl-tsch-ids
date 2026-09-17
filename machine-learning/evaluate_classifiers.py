# -*- coding: utf-8 -*-
"""Reproduces Table III (six-classifier comparison), Table IV (per-class
performance), and Table VI (feature ablation) from the letter.

The evaluation protocol: for twenty repetitions, two of the seven independent
runs per class are withheld entirely for testing and the remaining five are
used for training, so no window from a given run ever appears on both sides
of the split. Reports mean and standard deviation of accuracy and F1 across
repetitions.

Usage: python3 evaluate_classifiers.py dataset_large_grouped.csv
"""
import sys
import random
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

N_REPEATS = 20
N_TEST_GROUPS_PER_CLASS = 2
CLASS_NAMES = ['Benign', 'Decreased Rank', 'Version Number', 'DIS Flooding']

RANK = ['rank_mean', 'rank_std', 'rank_max', 'rank_min', 'rc_mean', 'rc_std', 'rc_max']
CONTROL = ['dis_mean', 'dis_std', 'dis_max', 'dio_mean', 'dio_max', 'disrx_mean', 'disrx_max']
VERSION = ['version_spread']
PDR = ['pdr_mean', 'pdr_min']
OTHER = ['n_nodes', 'txe_mean', 'txe_std', 'rxe_mean']
ALL_FEATURES = RANK + CONTROL + VERSION + PDR + OTHER
PROTOCOL_ONLY = RANK + CONTROL + VERSION
PERFORMANCE_ONLY = PDR + OTHER

ABLATION_CONDITIONS = [
    ('Full feature set', ALL_FEATURES, None),
    ('Without rank features', [c for c in ALL_FEATURES if c not in RANK], 1),
    ('Without control-message features', [c for c in ALL_FEATURES if c not in CONTROL], 3),
    ('Without version feature', [c for c in ALL_FEATURES if c not in VERSION], 2),
    ('Without PDR features', [c for c in ALL_FEATURES if c not in PDR], None),
    ('Only protocol-level features', PROTOCOL_ONLY, None),
    ('Only network-performance features', PERFORMANCE_ONLY, None),
]

MODELS = {
    'Random Forest': RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced', n_jobs=-1),
    'Decision Tree': DecisionTreeClassifier(random_state=42, class_weight='balanced'),
    'Gradient Boosting': GradientBoostingClassifier(random_state=42),
    'Logistic Regression': make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight='balanced')),
    'SVM (RBF)': make_pipeline(StandardScaler(), SVC(kernel='rbf', class_weight='balanced')),
    'KNN (k=5)': make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5)),
}


def make_split(df, groups_all, y_all, seed):
    rng = random.Random(seed)
    class_groups = {c: sorted(df.loc[y_all == c, 'group'].unique()) for c in sorted(y_all.unique())}
    test_groups = set()
    for _, gs in class_groups.items():
        shuffled = gs[:]
        rng.shuffle(shuffled)
        test_groups.update(shuffled[:N_TEST_GROUPS_PER_CLASS])
    test_mask = groups_all.isin(test_groups)
    return ~test_mask, test_mask


def run_model_comparison(df):
    y_all = df['label']
    groups_all = df['group']
    per_class_f1 = {c: [] for c in range(4)}
    print("=" * 70)
    print("  Table III: model comparison (twenty balanced, run-independent partitions)")
    print("=" * 70)
    print(f"{'Model':<22}{'Acc mean':>10}{'Acc SD':>9}{'F1 mean':>10}{'F1 SD':>8}")
    for name, base_model in MODELS.items():
        accs, f1s = [], []
        for i in range(N_REPEATS):
            train_mask, test_mask = make_split(df, groups_all, y_all, i)
            X = df[ALL_FEATURES]
            clf = clone(base_model)
            clf.fit(X[train_mask], y_all[train_mask])
            pred = clf.predict(X[test_mask])
            accs.append(accuracy_score(y_all[test_mask], pred) * 100)
            f1s.append(f1_score(y_all[test_mask], pred, average='weighted') * 100)
            if name == 'Random Forest':
                p, r, f, _ = precision_recall_fscore_support(y_all[test_mask], pred, labels=[0, 1, 2, 3], zero_division=0)
                for c in range(4):
                    per_class_f1[c].append(f[c] * 100)
        accs, f1s = np.array(accs), np.array(f1s)
        print(f"{name:<22}{accs.mean():>10.2f}{accs.std():>9.2f}{f1s.mean():>10.2f}{f1s.std():>8.2f}")

    print()
    print("=" * 70)
    print("  Table IV: per-class F1 (Random Forest)")
    print("=" * 70)
    for c in range(4):
        arr = np.array(per_class_f1[c])
        print(f"  {CLASS_NAMES[c]:<18} F1 = {arr.mean():.2f} +/- {arr.std():.2f}")


def run_ablation(df):
    y_all = df['label']
    groups_all = df['group']
    print()
    print("=" * 70)
    print("  Table VI: feature ablation (Random Forest)")
    print("=" * 70)
    for name, feats, target_class in ABLATION_CONDITIONS:
        accs, f1s = [], []
        target_f1 = []
        for i in range(N_REPEATS):
            train_mask, test_mask = make_split(df, groups_all, y_all, i)
            X = df[feats]
            clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced', n_jobs=-1)
            clf.fit(X[train_mask], y_all[train_mask])
            pred = clf.predict(X[test_mask])
            accs.append(accuracy_score(y_all[test_mask], pred) * 100)
            f1s.append(f1_score(y_all[test_mask], pred, average='weighted') * 100)
            if target_class is not None:
                p, r, f, _ = precision_recall_fscore_support(y_all[test_mask], pred, labels=[0, 1, 2, 3], zero_division=0)
                target_f1.append(f[target_class] * 100)
        accs, f1s = np.array(accs), np.array(f1s)
        target_str = "-"
        if target_class is not None:
            tf = np.array(target_f1)
            target_str = f"{CLASS_NAMES[target_class]} F1={tf.mean():.2f}+/-{tf.std():.2f}"
        print(f"{name:<34} #feat={len(feats):>2}  Acc={accs.mean():6.2f}+/-{accs.std():4.2f}  {target_str}")


if __name__ == '__main__':
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'dataset_large_grouped.csv'
    df = pd.read_csv(csv_path)
    run_model_comparison(df)
    run_ablation(df)
