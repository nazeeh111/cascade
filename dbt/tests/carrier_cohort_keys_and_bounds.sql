select carrier,airport,period from {{ ref('carrier_cohorts') }} group by 1,2,3 having count(*)<>1
union all select carrier,airport,period from {{ ref('carrier_cohorts') }}
where disrupted_n>scheduled_n or cancelled_n>disrupted_n or unknown_n>scheduled_n or disruption_rate not between 0 and 1
