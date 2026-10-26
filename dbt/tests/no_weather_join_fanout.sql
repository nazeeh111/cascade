select 'weather join cardinality' as failure
where (select count(*) from {{ ref('features') }}) <>
 (select count(*) from {{ ref('int_cutoff_features') }} where cutoff >=
   (select min(cutoff)+interval '48 hours' from {{ ref('int_airport_hours') }}))
