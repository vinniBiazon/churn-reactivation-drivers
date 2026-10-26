-- Rescue rate by variant, and the "credit" a click-based report would give the email:
-- the share of rescued members whose return session came through the email link
select
    variant,
    count(*)                                                        as assigned,
    sum(rescued::int)                                               as rescued,
    avg(rescued::int)                                               as rescue_rate,
    avg(case when rescued then (return_entry_source = 'email_link')::int end) as share_of_rescues_via_email_link
from {{ ref('winback_outcomes') }}
where window_complete
group by 1
order by 1
