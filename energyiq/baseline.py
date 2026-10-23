"""Counterfactual baseline: what each meter *should* have used given time, calendar and weather.

Predictions are out-of-fold (week-blocked folds), so the model never judges an hour it trained on.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import lightgbm as lgb

N_FOLDS = 5


def make_features(index: pd.DatetimeIndex, weather: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=index)
    f["hour"] = index.hour
    f["dow"] = index.dayofweek
    f["weekend"] = (index.dayofweek >= 5).astype(int)
    doy = index.dayofyear
    f["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    f["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    for c in weather.columns:
        f[c] = weather[c].reindex(index).values
    tcols = [c for c in weather.columns if "temp" in c.lower()]
    if tcols:
        t = weather[tcols[0]].reindex(index)
        f["temp_24h_mean"] = t.rolling(24, min_periods=1).mean().values  # thermal inertia
        f["temp_max_today"] = t.groupby(index.date).transform("max").values
    return f


def _model():
    return lgb.LGBMRegressor(
        objective="l1",              # median regression: robust to the anomalies we're hunting
        n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=20,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.9, verbose=-1,
    )


def fit_baseline(y: pd.Series, weather: pd.DataFrame) -> dict:
    """Return OOF expected values, importances, and accuracy metrics for one meter."""
    y = y.dropna()
    X = make_features(y.index, weather)
    week = ((y.index - y.index[0]).days // 7).values
    fold = week % N_FOLDS
    oof = np.full(len(y), np.nan)
    imp = np.zeros(X.shape[1])
    for k in range(N_FOLDS):
        tr, te = fold != k, fold == k
        m = _model().fit(X[tr], y.values[tr])
        oof[te] = m.predict(X[te])
        imp += m.booster_.feature_importance("gain")
    expected = pd.Series(oof, index=y.index, name="expected")

    # Naive reference: hour x weekday median profile (what a simple dashboard would use)
    prof = y.groupby([y.index.dayofweek, y.index.hour]).transform("median")
    metrics = {
        "model_mape": _mape(y, expected), "profile_mape": _mape(y, prof),
        "model_r2": _r2(y, expected), "profile_r2": _r2(y, prof),
    }
    importance = pd.Series(imp / imp.sum(), index=X.columns).sort_values(ascending=False)
    return {"expected": expected, "importance": importance, "metrics": metrics}


def _mape(y, p):
    m = y.abs() > y.abs().quantile(0.05)  # skip near-zero hours
    return float((np.abs(y[m] - p[m]) / y[m].abs()).mean() * 100)


def _r2(y, p):
    return float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())
