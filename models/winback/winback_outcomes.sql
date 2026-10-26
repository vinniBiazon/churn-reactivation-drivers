-- One row per win-back assignment: did the member come back within the rescue window, how fast,
-- through which entry point, and how engaged they were before going quiet
{% set window = var("rescue_window_days") %}
with first_return as (
    select
        w.member_id, w.assigned_on,
        min(s.session_date) as return_date
    from {{ ref('stg_winback_assignments') }} w
    join {{ ref('stg_sessions') }} s
        on s.member_id = w.member_id and s.session_date > w.assigned_on
    group by 1, 2
),
prior as (
    -- sessions in the 30 days before the last session, i.e. before the member went quiet
    select
        w.member_id, w.assigned_on,
        count(s.session_date) as sessions_last_30d_before_quiet
    from {{ ref('stg_winback_assignments') }} w
    left join {{ ref('stg_sessions') }} s
        on  s.member_id = w.member_id
        and s.session_date >  w.assigned_on - {{ var("near_churn_days") }} - 30
        and s.session_date <= w.assigned_on - {{ var("near_churn_days") }}
    group by 1, 2
)
select
    w.member_id,
    w.assigned_on,
    w.variant,
    w.assigned_on + {{ window }} <= date '{{ var("as_of") }}'           as window_complete,
    r.return_date,
    r.return_date - w.assigned_on                                       as days_to_return,
    coalesce(r.return_date <= w.assigned_on + {{ window }}, false)      as rescued,
    s.entry_source                                                      as return_entry_source,
    p.sessions_last_30d_before_quiet,
    case
        when p.sessions_last_30d_before_quiet >= 10 then '3. 10+ sessions'
        when p.sessions_last_30d_before_quiet >= 4  then '2. 4 to 9 sessions'
        else '1. 1 to 3 sessions'
    end                                                                 as prior_engagement
from {{ ref('stg_winback_assignments') }} w
left join first_return r using (member_id, assigned_on)
left join {{ ref('stg_sessions') }} s
    on s.member_id = w.member_id and s.session_date = r.return_date
left join prior p using (member_id, assigned_on)
