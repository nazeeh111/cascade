-- Q: Does one selected reporting carrier describe all carriers at these airports?
-- January only; separate airport cohorts prevent hiding route/airport composition.
select carrier,airport,period,scheduled_n,disrupted_n,cancelled_n,unknown_n,disruption_rate,
 mean_dep_delay,p99_dep_delay
from carrier_cohorts order by airport,scheduled_n desc,carrier
