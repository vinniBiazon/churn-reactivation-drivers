-- How long members took to come back after the email date, for everyone who came back within a year
-- (not only the rescues). A few very late returns pull the mean far above the median, so the median
-- and the upper percentiles describe a "typical" return better.
select
    variant,
    count(*)                           as returned_within_a_year,
    avg(days_to_return)                as mean_days,
    quantile_cont(days_to_return, 0.5)  as median_days,
    quantile_cont(days_to_return, 0.75) as p75_days,
    quantile_cont(days_to_return, 0.9)  as p90_days
from {{ ref('winback_outcomes') }}
where assigned_on + 365 <= date '{{ var("as_of") }}'
  and days_to_return <= 365
group by 1
order by 1
