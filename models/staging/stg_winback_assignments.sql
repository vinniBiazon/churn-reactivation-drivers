-- Every member who reached 60 silent days was assigned at random: email (90%) or holdout (10%)
select
    member_id,
    campaign,
    cast(assigned_on as date) as assigned_on,
    variant
from {{ source('raw', 'winback_assignments') }}
