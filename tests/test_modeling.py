from datetime import datetime, timedelta
import numpy as np
import pytest
from cascade.modeling import availability_audit, matrix, seasonal_fit, seasonal_predict, metrics, BASE_FEATURES


def row(**kw):
    r = {"airport": "DEN", "cutoff": datetime(2023, 1, 1, 12), "target_rate": .25,
         "hour": 12, "dow": 0, "month": 1, "weather_available_at": None, "max_event_available_at": None}
    r.update(kw)
    return r


def test_future_observation_is_rejected():
    with pytest.raises(ValueError, match="Availability"):
        availability_audit([row(weather_available_at=datetime(2023, 1, 1, 12, 1))])


def test_future_event_is_rejected():
    with pytest.raises(ValueError, match="Availability"):
        availability_audit([row(max_event_available_at=datetime(2023, 1, 1, 12, 1))])


def test_target_and_tail_cannot_enter_feature_matrix():
    a = row(target_rate=.25, tail="N123", actual_dep=datetime(2023, 1, 2))
    b = row(target_rate=1.0, tail="N999", actual_dep=datetime(2024, 1, 2))
    assert np.array_equal(matrix([a], ["DEN"]), matrix([b], ["DEN"]), equal_nan=True)
    assert "target_rate" not in BASE_FEATURES


def test_seasonal_unseen_cohort_falls_back_without_future_labels():
    fit = seasonal_fit([row(target_rate=.2), row(target_rate=.4)])
    assert seasonal_predict(fit, [row(hour=23, target_rate=1)])[0] == pytest.approx(.3)


def test_severe_and_calibration_metrics_have_declared_denominator():
    result = metrics([0, 1, .5, .25], [0, .75, .25, .25])
    assert result["n"] == 4
    assert result["severe_events"] == 2
    assert result["severe_recall"] == .5
    assert sum(b["n"] for b in result["calibration_bins"]) == 4


def test_training_cannot_accept_an_unmatured_target():
    from cascade.modeling import fit_predict
    r=row(label_available_at=datetime(2023,8,1,1))
    with pytest.raises(ValueError, match="Unmatured"):
        fit_predict([r],[r],["DEN"],{},datetime(2023,8,1))


def test_calibration_bins_cover_every_boundary():
    from cascade.modeling import metrics
    import numpy as np
    values=np.linspace(0,1,11)
    result=metrics(np.zeros(11),values)
    assert sum(b['n'] for b in result['calibration_bins'])==11
    assert abs(result['calibration_mae']-.5)<1e-12
    assert metrics([0],[.6])['calibration_mae']==.6


def test_prediction_bulk_write_preserves_types_and_prior_table_on_invalid_batch():
    import duckdb
    from datetime import datetime
    from cascade.modeling import persist_predictions
    c=duckdb.connect()
    row=('DEN',datetime(2023,10,1,16),'tabular',.6,.5,12,'test','heldout')
    persist_predictions(c,[row])
    assert c.execute('select * from predictions').fetchone()==row
    import pytest
    with pytest.raises(ValueError):persist_predictions(c,[(*row[:3],float('nan'),*row[4:])])
    with pytest.raises(ValueError):persist_predictions(c,[row,row])
    assert c.execute('select * from predictions').fetchone()==row
