-- Grain: directed focal route at one replay cutoff; scheduled next2h volume, no tails.
select origin,dest,count(*) as flights from flights f
join airports a on f.origin=a.airport and a.focal
join airports b on f.dest=b.airport and b.focal
where f.sched_dep>=? and f.sched_dep<? group by origin,dest order by origin,dest
