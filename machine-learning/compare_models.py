"""
Compare six machine learning classifiers for RPL/TSCH attack detection.

Trains and evaluates Random Forest, Gradient Boosting, Decision Tree,
SVM (RBF), KNN, and Logistic Regression on a stratified 70/30 split,
and reports accuracy, precision, recall, F1, and five-fold cross-validated
F1 (mean and standard deviation) for each model.

Usage:
    python3 compare_models.py            # expects dataset_big.csv in cwd
"""

import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

DATASET = 'dataset_big.csv'

print("=" * 70)
print("  Machine learning classifier comparison for RPL/TSCH attack detection")
print("=" * 70)

df = pd.read_csv(DATASET)
X = df.drop(columns=['label'])
y = df['label']
print(f"\nWindows: {len(df)} | Features: {X.shape[1]} | Classes: {y.nunique()}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.30, random_state=42, stratify=y)

models = {
    'Random Forest':       RandomForestClassifier(n_estimators=200, random_state=42, class_weight='balanced', n_jobs=-1),
    'Gradient Boosting':   GradientBoostingClassifier(n_estimators=200, random_state=42),
    'Decision Tree':       DecisionTreeClassifier(random_state=42, class_weight='balanced'),
    'SVM (RBF)':           make_pipeline(StandardScaler(), SVC(kernel='rbf', class_weight='balanced', random_state=42)),
    'KNN (k=5)':           make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5)),
    'Logistic Regression': make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)),
}

results = []
print("\n" + "-" * 70)
print(f"{'Model':<22}{'Accuracy':>10}{'Precision':>11}{'Recall':>9}{'F1':>8}{'CV-F1':>14}")
print("-" * 70)
for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    rec = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
    cv = cross_val_score(model, X, y, cv=5, scoring='f1_weighted')
    results.append((name, acc, prec, rec, f1, cv.mean(), cv.std()))
    print(f"{name:<22}{acc*100:>9.2f}%{prec*100:>10.2f}%{rec*100:>8.2f}%{f1*100:>7.2f}%{cv.mean()*100:>8.2f}% (+/-{cv.std()*100:.2f})")
print("-" * 70)

best = max(results, key=lambda r: r[5])
print(f"\nBest (by CV-F1): {best[0]} - {best[5]*100:.2f}% (+/-{best[6]*100:.2f}%)")
print("=" * 70)
