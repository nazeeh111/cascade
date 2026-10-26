-- Source count exactly accounts for deduplication; no silent loss.
select 'count_reconciliation' as failure
where (select count(*) from {{ source('public_snapshot','raw_flights') }})
 <> (select sum(duplicate_n) from {{ ref('stg_flights') }})
union all
select 'cancel_reconciliation'
where (select sum(try_cast(Cancelled as double)) from {{ source('public_snapshot','raw_flights') }})
 <> (select sum(cancelled::integer*duplicate_n) from {{ ref('stg_flights') }})
union all
select 'signed_delay_sum_reconciliation'
where abs((select sum(try_cast(DepDelay as double)) from {{ source('public_snapshot','raw_flights') }} )
 - (select sum(dep_delay*duplicate_n) from {{ ref('stg_flights') }}))>0.0001
