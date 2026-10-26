select airport,cutoff from {{ ref('features') }} group by 1,2 having count(*)<>1
union all
select airport,cutoff from {{ ref('features') }}
where target_rate not between 0 and 1 or lag_rate_2h not between 0 and 1
 or lag_rate_6h not between 0 and 1 or target_n<0 or target_late_n>target_n or backlog_n<0
