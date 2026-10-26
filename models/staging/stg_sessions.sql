-- One row per member and day with at least one session
select
    member_id,
    cast(session_date as date) as session_date,
    entry_source               -- app_open, push, web, email_link
from {{ source('raw', 'sessions') }}
