-- A member cannot churn twice without coming back in between, or come back without having churned
with ordered as (
    select
        member_id, happened_on, event_name,
        lag(event_name) over (partition by member_id order by happened_on, event_name) as prior_event
    from {{ ref('lifecycle_events') }}
    where event_name in ('churned', 'reactivated')
)
select *
from ordered
where (event_name = 'churned'     and prior_event = 'churned')
   or (event_name = 'reactivated' and coalesce(prior_event, 'none') != 'churned')
