-- The retention heatmap must not show a calendar month that has not ended yet
select *
from {{ ref('retention_heatmap') }}
where (period_month + interval 1 month)::date > date '{{ var("as_of") }}' + 1
