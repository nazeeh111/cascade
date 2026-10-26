select airport,cutoff from {{ ref('features') }}
where weather_available_at>cutoff or max_event_available_at>cutoff
 or label_available_at<cutoff+interval '2 hours'
