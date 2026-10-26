-- Share of a cohort with at least one session N months after it started, for two kinds of cohort:
--   new         : members, by the month they joined
--   reactivated : returns from churn, by the month of the return (a member who returns twice counts twice)
-- Only calendar months that have fully ended are shown. A month that is still running would look
-- like a drop, because its members have had only part of the month to show up.
with starts as (
    select member_id, joined_on as start_date, 'new' as cohort_kind
    from {{ ref('stg_members') }}
    union all
    select member_id, happened_on, 'reactivated'
    from {{ ref('lifecycle_events') }}
    where event_name = 'reactivated'
),
cohorts as (
    select
        row_number() over () as start_id,
        member_id, cohort_kind, start_date,
        date_trunc('month', start_date)::date as cohort_month
    from starts
),
active_months as (
    select distinct member_id, date_trunc('month', session_date)::date as active_month
    from {{ ref('stg_sessions') }}
),
grid as (
    select c.*, k.months_since,
           (c.cohort_month + to_months(k.months_since))::date as period_month
    from cohorts c
    cross join (select unnest(range(0, {{ var("heatmap_months") }} + 1)) as months_since) k
)
select
    g.cohort_kind,
    g.cohort_month,
    g.months_since,
    g.period_month,
    count(*)                                            as cohort_size,
    count(a.member_id)                                  as members_active,
    count(a.member_id) / count(*)                       as share_active
from grid g
left join active_months a
    on a.member_id = g.member_id and a.active_month = g.period_month
where (g.period_month + interval 1 month)::date <= date '{{ var("as_of") }}' + 1
group by 1, 2, 3, 4
order by 1, 2, 3
