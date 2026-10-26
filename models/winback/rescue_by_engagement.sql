-- Rescue rate by how engaged the member was before going quiet, for each variant.
-- The holdout column shows who comes back on their own; the gap between columns is the email.
select
    prior_engagement,
    count(*) filter (where variant = 'email')                        as assigned_email,
    count(*) filter (where variant = 'holdout')                      as assigned_holdout,
    avg(rescued::int) filter (where variant = 'email')               as rescue_rate_email,
    avg(rescued::int) filter (where variant = 'holdout')             as rescue_rate_holdout
from {{ ref('winback_outcomes') }}
where window_complete
group by 1
order by 1
