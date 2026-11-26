from datetime import datetime, timedelta

import duckdb
import pytest

from cascade.simulation import calibrate


@pytest.fixture
def con():
    with duckdb.connect(config={"threads": 1}) as db:
        db.execute("""CREATE TABLE flights (
            flight_id VARCHAR, origin VARCHAR, dest VARCHAR, origin_tz VARCHAR,
            sched_dep TIMESTAMP, actual_dep TIMESTAMP, actual_arr TIMESTAMP,
            dep_delay DOUBLE, arr_delay DOUBLE, cancelled BOOLEAN, diverted BOOLEAN,
            arrival_inconsistent BOOLEAN, scheduled_arr_clock_inconsistent BOOLEAN,
            actual_dep_clock_inconsistent BOOLEAN)""")
        db.execute("""CREATE TABLE rotations (
            from_flight_id VARCHAR, to_flight_id VARCHAR, tail VARCHAR, airport VARCHAR,
            sched_gap_min DOUBLE, actual_gap_min DOUBLE, inbound_arr_delay DOUBLE,
            outbound_dep_delay DOUBLE)""")
        yield db


def flight(con, fid, sched, delay=10, **changes):
    sched = datetime.fromisoformat(sched) if isinstance(sched, str) else sched
    row = dict(flight_id=fid, origin="A", dest="B", origin_tz="UTC",
               sched_dep=sched, actual_dep=sched + timedelta(minutes=delay),
               actual_arr=sched + timedelta(hours=2, minutes=delay),
               dep_delay=delay, arr_delay=delay - 5, cancelled=False, diverted=False,
               arrival_inconsistent=False, scheduled_arr_clock_inconsistent=False,
               actual_dep_clock_inconsistent=False)
    row.update(changes)
    con.execute("INSERT INTO flights VALUES (" + ",".join("?" for _ in row) + ")", list(row.values()))


def test_requested_boundary_controls_all_fitted_outcome_priors(con):
    flight(con, "old", "2023-06-20", 10)
    flight(con, "later", "2023-08-20", 100, arr_delay=200)
    early = calibrate(con, "2023-07-01")
    assert early[-1] == 1
    assert early[1][("*", -1)] == 10
    assert early[2][("*", "*")] == -5
    assert early[3] == {"A": 0.0}
    later = calibrate(con)
    assert later[-1] == 2
    assert later[1][("*", -1)] > early[1][("*", -1)]
    assert later[2] != early[2]
    assert later[3] == {"A": 0.5}
    assert later[4] == early[4]


@pytest.mark.parametrize("field,lag", [
    ("sched_dep", timedelta(hours=14)),
    ("actual_dep", timedelta(minutes=15)),
    ("actual_arr", timedelta(minutes=15)),
])
def test_strict_event_maturity_and_schedule_boundaries(con, field, lag):
    boundary = datetime(2023, 6, 1)
    for name, delta in [("before", -1), ("equal", 0), ("after", 1)]:
        flight(con, name, "2023-05-30", **{
            field: boundary - lag + timedelta(microseconds=delta)})
    assert calibrate(con, boundary.isoformat())[-1] == 1
    assert con.execute("SELECT flight_id FROM sim_train").fetchall() == [("before",)]


def test_future_outcomes_rotations_and_schedules_cannot_change_early_priors(con):
    flight(con, "old", "2023-05-20")
    flight(con, "future", "2023-06-20", 100, dest="C", origin="X")
    flight(con, "unmatured", "2023-05-30",
           actual_arr=datetime(2023, 6, 1), arr_delay=10000)
    flight(con, "unknown-inbound", "2023-05-20")
    con.execute("INSERT INTO rotations VALUES ('missing','unknown-inbound','T','A',35,35,9999,10)")
    early = calibrate(con, "2023-06-01")
    assert early[-1] == 1
    con.execute("UPDATE flights SET dep_delay=99999, arr_delay=-99999 WHERE flight_id='future'")
    con.execute("UPDATE flights SET arr_delay=-99999 WHERE flight_id='unmatured'")
    con.execute("UPDATE rotations SET inbound_arr_delay=-99999")
    flight(con, "new-future-route", "2023-06-15", origin="X", dest="Z")
    assert calibrate(con, "2023-06-01") == early
    assert early[4] == {"A": 2.0}


def test_degree_prior_has_strict_cutoff_and_frozen_july_cap(con):
    flight(con, "old", "2023-05-20")
    flight(con, "at-boundary", "2023-06-01", dest="C")
    flight(con, "after-july", "2023-08-01", origin="X", dest="D")
    assert calibrate(con, "2023-06-01")[4] == {"A": 2.0}
    assert calibrate(con)[4] == {"A": 2.0}
    con.execute("DELETE FROM flights WHERE flight_id='at-boundary'")
    assert calibrate(con)[4] == {"A": 2.0}


def test_offsets_are_normalized_to_utc_and_empty_history_is_defined(con):
    flight(con, "old", "2023-05-20")
    assert calibrate(con, "2023-06-01") == calibrate(con, "2023-06-01T02:00:00+02:00")
    empty = calibrate(con, "2023-01-02")
    assert empty == (1.0, {("*", -1): 0.0}, {("*", "*"): 0.0}, {}, {}, 0)


@pytest.mark.parametrize("cutoff", [
    "nonsense", "2023-07-01'; DROP TABLE flights; --", None,
    "2023-01-01", "2022-12-31", "2023-10-01T00:00:00.000001", "2024-01-01",
])
def test_invalid_or_holdout_cutoffs_fail_before_sql(con, cutoff):
    with pytest.raises(ValueError, match="cutoff"):
        calibrate(con, cutoff)
    assert con.execute("SELECT count(*) FROM flights").fetchone()[0] == 0


def test_production_rotation_inbound_maturity_and_missing_or_ambiguous_links(con):
    boundary = datetime(2023, 6, 1)
    for name, delta in [("before", -1), ("equal", 0), ("after", 1)]:
        flight(con, "in-" + name, "2023-05-30", actual_arr=boundary - timedelta(minutes=15) + timedelta(microseconds=delta))
        flight(con, "out-" + name, "2023-05-30")
        con.execute("INSERT INTO rotations VALUES (?, ?, 'T', 'A', 35, 35, 5, 10)", ["in-" + name, "out-" + name])
    flight(con, "out-missing", "2023-05-30")
    con.execute("INSERT INTO rotations VALUES ('absent', 'out-missing', 'T', 'A', 35, 35, 5, 10)")
    flight(con, "in-duplicate", "2023-05-30")
    flight(con, "in-duplicate", "2023-05-30")
    flight(con, "out-duplicate", "2023-05-30")
    con.execute("INSERT INTO rotations VALUES ('in-duplicate', 'out-duplicate', 'T', 'A', 35, 35, 5, 10)")
    flight(con, "out-rotation-duplicate", "2023-05-30")
    con.execute("INSERT INTO rotations VALUES ('in-before', 'out-rotation-duplicate', 'T', 'A', 35, 35, 5, 10), ('in-before', 'out-rotation-duplicate', 'T', 'A', 35, 35, 5, 10)")
    calibrate(con, boundary.isoformat())
    included = {row[0] for row in con.execute("SELECT flight_id FROM sim_train").fetchall()}
    assert "out-before" in included
    assert not included.intersection({"out-equal", "out-after", "out-missing", "out-duplicate", "out-rotation-duplicate"})
