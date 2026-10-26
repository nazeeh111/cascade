from datetime import datetime, timedelta
import pytest
from cascade.simulation import bounded_propagation, allocate, replay, handled_flights


def test_slack_absorbs_inbound_lateness():
    assert bounded_propagation(4,20,70,.8,35)==3.2
    assert bounded_propagation(4,60,50,.8,35)==45


def test_budget_and_airport_caps_are_enforced():
    result=allocate({'A':[20,18],'B':[10,9],'C':[8]}, {'A':2,'B':2,'C':1},budget=3,optimize=True)
    assert result=={'A':2,'B':1,'C':0}
    assert sum(result.values())==3
    assert max(result.values())<=2
    with pytest.raises(ValueError):
        allocate({}, {}, budget=-1)


def flights():
    cutoff=datetime(2023,10,1,16)
    rows=[]
    for i,a in enumerate(['A','B']):
        rows.append({'flight_id':str(i),'origin':a,'dest':'B' if a=='A' else 'C','sched_dep':cutoff+timedelta(hours=i),
                     'local_hour':16+i,'cancelled':False,'diverted':False,'from_flight_id':str(i-1) if i else None,
                     'sched_gap_min':35 if i else None,'prev_actual_arr':None,'prev_arr_delay':None})
    return cutoff,rows


def test_resource_reduction_propagates_and_cannot_create_negative_delay():
    cutoff,rows=flights()
    base,_=replay(rows,{('*',-1):30},{('*','*'):0},{},cutoff,alpha=1)
    served,_=replay(rows,{('*',-1):30},{('*','*'):0},{},cutoff,{'A':1},alpha=1)
    assert served['0']==15
    assert all(v>=0 for v in served.values())
    assert sum(served.values())<=sum(base.values())


def test_cancelled_scheduled_leg_consumes_service_slot():
    cutoff,rows=flights()
    rows[0]['cancelled']=True
    handled=handled_flights(rows,{'A':1},cutoff)
    assert '0' in handled
    simulated,_=replay(rows,{('*',-1):30},{('*','*'):0},{},cutoff,{'A':1})
    assert '0' not in simulated


def test_future_arrival_seed_is_not_used():
    cutoff,rows=flights()
    rows[0]['prev_actual_arr']=cutoff+timedelta(minutes=5)
    rows[0]['prev_arr_delay']=1000
    rows[0]['sched_gap_min']=35
    pred,_=replay(rows,{('*',-1):5},{('*','*'):0},{},cutoff,alpha=1)
    assert pred['0']==5


def test_service_cannot_erase_aircraft_readiness():
    cutoff,rows=flights()
    rows[0]['prev_actual_arr']=cutoff-timedelta(minutes=20)
    rows[0]['prev_arr_delay']=60
    rows[0]['sched_gap_min']=35
    base,_=replay(rows,{('*',-1):5},{('*','*'):0},{},cutoff,alpha=.5)
    served,_=replay(rows,{('*',-1):5},{('*','*'):0},{},cutoff,{'A':1},alpha=.5)
    assert base['0']==60
    assert served['0']==60


def test_observed_inflight_departure_initializes_arrival_without_future_outcome():
    cutoff,rows=flights()
    rows[0].update(prev_actual_arr=cutoff+timedelta(minutes=10),prev_arr_delay=1000,
      prev_actual_dep=cutoff-timedelta(hours=1),prev_dep_delay=60,prev_sched_dep=cutoff-timedelta(hours=2),
      prev_origin='X',prev_local_hour=14,sched_gap_min=35)
    prediction,_=replay(rows,{('*',-1):5},{('X','A'):-5,('*','*'):0},{},cutoff)
    assert prediction['0']==55


def test_already_observed_departure_cannot_receive_service():
    cutoff,rows=flights()
    rows[0].update(actual_dep=cutoff-timedelta(minutes=20),dep_delay=-20)
    assert '0' not in handled_flights(rows,{'A':1},cutoff)


def test_eventual_cancellation_does_not_erase_an_observed_gate_out():
    cutoff,rows=flights()
    rows[0].update(cancelled=True,actual_dep=None,observed_gate_out=cutoff-timedelta(minutes=20))
    assert '0' not in handled_flights(rows,{'A':1},cutoff)
