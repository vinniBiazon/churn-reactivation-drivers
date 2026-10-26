"""Build the dbt project, add the statistics and print the readouts.

Run from the repository root after `python data/generate.py`:
    python run_analysis.py
"""
import math
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

DB = "churn.duckdb"
Z = 1.96


def build():
    """dbt build: models and every data test. Stops if a test fails."""
    dbt = shutil.which("dbt") or str(Path(sys.executable).with_name("dbt"))
    result = subprocess.run([dbt, "build", "--profiles-dir", "."], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout[-3000:])
        sys.exit("dbt build failed")


def uplift(con):
    """Email minus holdout rescue rate, with a 95% interval, and how much of the email's credit is real."""
    r = con.sql("select * from winback_readout").df().set_index("variant")
    p_e, p_h = r.loc["email", "rescue_rate"], r.loc["holdout", "rescue_rate"]
    n_e, n_h = r.loc["email", "assigned"], r.loc["holdout", "assigned"]
    diff = p_e - p_h
    se = math.sqrt(p_e * (1 - p_e) / n_e + p_h * (1 - p_h) / n_h)
    return {
        "email_rate": p_e, "holdout_rate": p_h, "uplift": diff,
        "ci_low": diff - Z * se, "ci_high": diff + Z * se,
        "credit_by_clicks": r.loc["email", "share_of_rescues_via_email_link"],
        "credit_by_holdout": diff / p_e,  # share of email-group rescues the email actually caused
        "assigned_email": n_e, "assigned_holdout": n_h,
    }


def true_uplift(con):
    """From the generator: share of email-group assignments rescued only because of the email."""
    truth = pd.read_csv("data/raw/truth_winback.csv", parse_dates=["assigned_on"])
    out = con.sql("select member_id, assigned_on, rescued from winback_outcomes where window_complete and variant = 'email'").df()
    out["assigned_on"] = pd.to_datetime(out["assigned_on"])
    df = out.merge(truth, on=["member_id", "assigned_on"])
    return (df.rescued & df.returned_because_of_email).mean()


def partial_month_effect(con):
    """What the heatmap would show if the running month (October 2026) were included."""
    return con.sql("""
        with m as (select member_id, date_trunc('month', joined_on)::date as cohort_month from stg_members),
        act as (select distinct member_id, date_trunc('month', session_date)::date as month from stg_sessions)
        select
            m.cohort_month,
            avg((a1.member_id is not null)::int) as share_active_sep,
            avg((a2.member_id is not null)::int) as share_active_oct_so_far
        from m
        left join act a1 on a1.member_id = m.member_id and a1.month = date '2026-09-01'
        left join act a2 on a2.member_id = m.member_id and a2.month = date '2026-10-01'
        where m.cohort_month between date '2026-03-01' and date '2026-06-01'
        group by 1 order by 1
    """).df()


def main():
    build()
    con = duckdb.connect(DB, read_only=True)
    pd.set_option("display.width", 160)

    print("\n=== 1. Where members stand on 2026-10-25 ===")
    print(con.sql("select status, count(*) as members from member_status group by 1 order by 2 desc").df().to_string(index=False))

    print("\n=== 2. Win-back email: credit vs causation ===")
    u = uplift(con)
    print(f"Rescued within 30 days: email {u['email_rate']:.1%} (n={u['assigned_email']:,}), "
          f"holdout {u['holdout_rate']:.1%} (n={u['assigned_holdout']:,})")
    print(f"Uplift: {u['uplift'] * 100:+.1f} pp (95% CI {u['ci_low'] * 100:+.1f} to {u['ci_high'] * 100:+.1f})")
    print(f"Share of email-group rescues credited to the email by clicks: {u['credit_by_clicks']:.0%}")
    print(f"Share actually caused by the email (uplift / email rate): {u['credit_by_holdout']:.0%}")
    print(f"True uplift from the generator: {true_uplift(con) * 100:+.1f} pp")
    print("\nRescue rate by engagement before going quiet:")
    print(con.sql("select * from rescue_by_engagement").df().round(3).to_string(index=False))

    print("\n=== 3. Time to return (everyone who came back within a year) ===")
    print(con.sql("select * from time_to_return").df().round(1).to_string(index=False))

    print("\n=== 4. Retention: new members vs members back from churn ===")
    rc = con.sql("select * from retention_curves").df()
    print(rc.pivot(index="cohort_kind", columns="months_since", values="share_active").round(3).to_string())
    print("\nWhy the running month is left out (Mar to Jun 2026 joiners):")
    print(partial_month_effect(con).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
