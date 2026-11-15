"""Machine-learning risk engine: Isolation Forest (unsupervised anomaly score)
+ Random Forest (supervised attack probability), blended into a 0-100 risk score."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split

LOGIN_FEATURES = ["hour", "success", "failed_streak", "new_device", "new_country", "logins_last_hour"]
FILE_FEATURES = ["hour", "size_mb", "files_last_10min", "mb_last_hour", "sensitivity", "is_download"]
NIGHT = [0, 1, 2, 3, 4, 5, 23]


def _hours(rng, n, night_share, lo=8, hi=20):
    return np.where(rng.random(n) < night_share, rng.choice(NIGHT, n), rng.integers(lo, hi, n))


def synth_login_data(n=6000, seed=42):
    """Bootstrap training data that mimics normal vs. attack login behaviour."""
    rng = np.random.default_rng(seed)
    na = int(n * 0.10); nn = n - na
    normal = pd.DataFrame({
        "hour": _hours(rng, nn, 0.03), "success": rng.choice([1, 0], nn, p=[.95, .05]),
        "failed_streak": rng.choice([0, 1, 2], nn, p=[.9, .08, .02]),
        "new_device": rng.choice([0, 1], nn, p=[.95, .05]),
        "new_country": rng.choice([0, 1], nn, p=[.99, .01]),
        "logins_last_hour": rng.integers(0, 3, nn), "y": 0})
    attack = pd.DataFrame({
        "hour": _hours(rng, na, 0.6), "success": rng.choice([0, 1], na, p=[.7, .3]),
        "failed_streak": rng.integers(3, 12, na), "new_device": rng.choice([0, 1], na, p=[.2, .8]),
        "new_country": rng.choice([0, 1], na, p=[.5, .5]),
        "logins_last_hour": rng.integers(4, 30, na), "y": 1})
    stealth = rng.random(na) < 0.15          # "low-and-slow" attacks that look almost normal
    attack.loc[stealth, ["failed_streak", "logins_last_hour"]] = [1, 2]
    attack.loc[stealth, "hour"] = rng.integers(8, 20, stealth.sum())
    return pd.concat([normal, attack], ignore_index=True)


def synth_file_data(n=6000, seed=7):
    rng = np.random.default_rng(seed)
    na = int(n * 0.08); nn = n - na
    size = rng.lognormal(1.0, 0.8, nn)
    normal = pd.DataFrame({
        "hour": _hours(rng, nn, 0.02), "size_mb": size,
        "files_last_10min": rng.integers(1, 6, nn), "mb_last_hour": size * rng.integers(1, 8, nn),
        "sensitivity": rng.choice([0, 1, 2, 3], nn, p=[.3, .4, .25, .05]),
        "is_download": rng.choice([0, 1], nn, p=[.6, .4]), "y": 0})
    attack = pd.DataFrame({
        "hour": _hours(rng, na, 0.6), "size_mb": rng.lognormal(3.5, 0.7, na),
        "files_last_10min": rng.integers(15, 120, na), "mb_last_hour": rng.uniform(300, 3000, na),
        "sensitivity": rng.choice([1, 2, 3], na, p=[.1, .45, .45]),
        "is_download": rng.choice([0, 1], na, p=[.1, .9]), "y": 1})
    stealth = rng.random(na) < 0.15          # slow exfiltration that looks almost normal
    attack.loc[stealth, ["files_last_10min", "mb_last_hour", "size_mb"]] = [4, 12, 6]
    attack.loc[stealth, "hour"] = rng.integers(8, 20, stealth.sum())
    return pd.concat([normal, attack], ignore_index=True)


class RiskEngine:
    def __init__(self):
        self.metrics = {}
        self.train_login(synth_login_data())
        self.train_file(synth_file_data())

    @staticmethod
    def _fit(df, feats):
        X, y = df[feats], df["y"]
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=1)
        rf = RandomForestClassifier(n_estimators=300, class_weight="balanced_subsample",
                                    min_samples_leaf=2, max_features="sqrt",
                                    random_state=17, n_jobs=-1).fit(Xtr, ytr)
        normal_train = Xtr.loc[ytr == 0]
        iso = IsolationForest(n_estimators=250, contamination=0.06, max_samples="auto",
                              random_state=17, n_jobs=-1).fit(normal_train)
        normal_scores = -iso.score_samples(normal_train)
        cal = (float(np.percentile(normal_scores, 50)), float(np.percentile(normal_scores, 99)))
        rf_prob = rf.predict_proba(Xte)[:, 1]
        iso_scores = -iso.score_samples(Xte)
        iso_prob = np.clip((iso_scores - cal[0]) / (cal[1] - cal[0] + 1e-9), 0, 1)
        blended = 0.70 * rf_prob + 0.30 * iso_prob
        pred = (blended >= 0.50).astype(int)
        m = {"accuracy": float(accuracy_score(yte, pred)),
             "balanced_accuracy": float(balanced_accuracy_score(yte, pred)),
             "precision": float(precision_score(yte, pred, zero_division=0)),
             "recall": float(recall_score(yte, pred, zero_division=0)),
             "f1": float(f1_score(yte, pred, zero_division=0)),
             "roc_auc": float(roc_auc_score(yte, blended)),
             "rows": int(len(df)), "test_rows": int(len(Xte)),
             "evaluation": "stratified hold-out; synthetic bootstrap data"}
        rf.set_params(n_jobs=1)
        iso.set_params(n_jobs=1)
        return iso, rf, cal, m

    def train_login(self, df):
        self.l_iso, self.l_rf, self.l_cal, self.metrics["login"] = self._fit(df, LOGIN_FEATURES)

    def train_file(self, df):
        self.f_iso, self.f_rf, self.f_cal, self.metrics["file"] = self._fit(df, FILE_FEATURES)

    @staticmethod
    def _score(iso, rf, cal, X):
        s = -iso.score_samples(X)[0]
        iso_risk = float(np.clip((s - cal[0]) / (cal[1] - cal[0] + 1e-9), 0, 1))
        rf_risk = float(rf.predict_proba(X)[0][1])
        return round(100 * (0.30 * iso_risk + 0.70 * rf_risk), 1)

    def score_login(self, feats):
        X = pd.DataFrame([feats])[LOGIN_FEATURES]
        return self._score(self.l_iso, self.l_rf, self.l_cal, X)

    def score_file(self, feats):
        X = pd.DataFrame([feats])[FILE_FEATURES]
        return self._score(self.f_iso, self.f_rf, self.f_cal, X)


engine = RiskEngine()
