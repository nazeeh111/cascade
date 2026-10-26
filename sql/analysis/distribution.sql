-- Q: What is hidden by a mean delay? Nulls remain a separate group.
select case when cancelled then 'cancelled' when dep_delay is null then 'missing_non_cancelled'
 when dep_delay<0 then 'early' when dep_delay<15 then '0_to_14'
 when dep_delay<60 then '15_to_59' when dep_delay<180 then '60_to_179'
 else '180_plus' end as delay_bin,count(*) as n
from flights group by 1 order by 1
