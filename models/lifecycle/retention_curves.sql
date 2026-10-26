-- The heatmap collapsed into one curve per cohort type: share active N months after starting,
-- weighting every cohort by its size, over cohorts that have reached month N
select
    cohort_kind,
    months_since,
    sum(members_active) / sum(cohort_size) as share_active,
    sum(cohort_size)                       as starts_measured
from {{ ref('retention_heatmap') }}
where cohort_month >= date '2024-01-01'
group by 1, 2
order by 1, 2
