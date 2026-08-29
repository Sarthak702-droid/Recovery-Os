"""Train only on genuine, verified merchant outcomes. No synthetic or public proxy labels."""
from pathlib import Path
import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sqlalchemy import select
from app.db import Outcome, RecoveryCase

MIN_REAL_LABELLED_CASES = 100


async def train_recovery_model(session, output_path: str = "artifacts/recovery-model.joblib") -> dict:
    cases = (await session.scalars(select(RecoveryCase).order_by(RecoveryCase.created_at))).all()
    outcomes = {o.case_id for o in (await session.scalars(select(Outcome))).all()}
    eligible = [c for c in cases if c.state in {"RECOVERED", "CLOSED", "FAILED"}]
    if len(eligible) < MIN_REAL_LABELLED_CASES:
        raise ValueError(f"Need at least {MIN_REAL_LABELLED_CASES} genuine labelled merchant cases; found {len(eligible)}")
    x = [[c.amount_minor, c.previous_attempts, int(c.disputed), sum(ord(ch) for ch in (c.failure_category or ""))] for c in eligible]
    y = [int(c.id in outcomes) for c in eligible]
    if len(set(y)) < 2: raise ValueError("Genuine dataset has only one outcome class")
    try:
        from lightgbm import LGBMClassifier
        base_estimator, algorithm = LGBMClassifier(n_estimators=120, learning_rate=.05, random_state=42), "LightGBM"
    except ImportError:
        base_estimator, algorithm = LogisticRegression(max_iter=2000), "LogisticRegression"
    estimator = CalibratedClassifierCV(base_estimator, method="sigmoid", cv=TimeSeriesSplit(n_splits=3))
    estimator.fit(x, y)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": estimator, "feature_version": "recovery-v1", "training_cases": len(eligible)}, output_path)
    return {"training_cases": len(eligible), "feature_version": "recovery-v1", "algorithm": algorithm, "path": output_path}
