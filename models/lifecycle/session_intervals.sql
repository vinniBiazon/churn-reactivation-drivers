-- Days since the member's previous session, for every session
select
    member_id,
    session_date,
    entry_source,
    lag(session_date) over (partition by member_id order by session_date) as prior_session_date,
    session_date - lag(session_date) over (partition by member_id order by session_date) as gap_days
from {{ ref('stg_sessions') }}
