-- Join, churn and reactivation events.
--   churned     : the day a member reaches {{ var("churn_days") }} days without a session
--   reactivated : the first session after being churned
-- A gap still open at the end of the data counts as a churn once it has lasted long enough.
with latest_session as (
    select member_id, max(session_date) as latest_session_date
    from {{ ref('stg_sessions') }}
    group by 1
)
select member_id, joined_on as happened_on, 'joined' as event_name
from {{ ref('stg_members') }}

union all

select member_id, prior_session_date + {{ var("churn_days") }}, 'churned'
from {{ ref('session_intervals') }}
where gap_days >= {{ var("churn_days") }}

union all

select member_id, session_date, 'reactivated'
from {{ ref('session_intervals') }}
where gap_days >= {{ var("churn_days") }}

union all

select member_id, latest_session_date + {{ var("churn_days") }}, 'churned'
from latest_session
where latest_session_date + {{ var("churn_days") }} <= date '{{ var("as_of") }}'
