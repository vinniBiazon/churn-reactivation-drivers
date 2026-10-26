-- Where every member stands on the last day of data
with latest_session as (
    select member_id, max(session_date) as latest_session_date
    from {{ ref('stg_sessions') }}
    group by 1
)
select
    member_id,
    latest_session_date,
    date '{{ var("as_of") }}' - latest_session_date as days_since_latest_session,
    case
        when date '{{ var("as_of") }}' - latest_session_date >= {{ var("churn_days") }}      then 'churned'
        when date '{{ var("as_of") }}' - latest_session_date >= {{ var("near_churn_days") }} then 'near_churn'
        else 'active'
    end as status
from latest_session
