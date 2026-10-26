-- Every win-back assignment must come exactly {{ var("near_churn_days") }} days after the member's last session
with last_before as (
    select w.member_id, w.assigned_on, max(s.session_date) as last_session_before
    from {{ ref('stg_winback_assignments') }} w
    join {{ ref('stg_sessions') }} s
        on s.member_id = w.member_id and s.session_date <= w.assigned_on
    group by 1, 2
)
select *
from last_before
where assigned_on - last_session_before != {{ var("near_churn_days") }}
