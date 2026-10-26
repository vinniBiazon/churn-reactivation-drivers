select member_id, cast(joined_on as date) as joined_on
from {{ source('raw', 'members') }}
