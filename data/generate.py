"""Generate the synthetic data for the churn and reactivation case study.

A recipe and meal planning app. Members use it in spells: a few weeks of regular use, then a quiet
period that either ends with a return or never ends. A member is "churned" after 90 days without a
session. At 60 days of silence, a win-back email goes out to 90% of members; 10% are held out at random.

Planted truth:
  - Most members who return after the email would have returned anyway; the email adds a few points.
  - Members who come back from churn drop off again faster than new members.
Data is "as of" 2026-10-25. Run from the repository root: python data/generate.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(31)
OUT = Path("data/raw")
OUT.mkdir(parents=True, exist_ok=True)

AS_OF = pd.Timestamp("2026-10-25")
FIRST_JOIN, LAST_JOIN = pd.Timestamp("2023-01-01"), pd.Timestamp("2026-06-30")
HORIZON = (AS_OF - FIRST_JOIN).days

N = 20_000
WINBACK_DAY = 60            # days of silence before the win-back email
HOLDOUT_SHARE = 0.10
EMAIL_EXTRA_RETURN = 0.05   # chance the email brings back someone who would not have returned by day 90
SPELL_MEAN = {"new": 75, "reactivated": 40}       # reactivated members stay active for less time
NEVER_RETURN = {"new": 0.45, "reactivated": 0.55}

join_day = rng.integers(0, (LAST_JOIN - FIRST_JOIN).days, N)
engagement = rng.uniform(0.08, 0.6, N)  # daily chance of a session while in an active spell

sessions_member, sessions_day, sessions_source = [], [], []
assign_rows, truth_rows = [], []

for i in range(N):
    day = int(join_day[i])
    kind = "new"
    first = True
    while day <= HORIZON:
        # Active spell: the first day always has a session (the signup or the return)
        length = max(1, int(rng.geometric(1 / SPELL_MEAN[kind])))
        days_active = day + np.nonzero(rng.random(length) < engagement[i])[0]
        days_active = np.unique(np.concatenate([[day], days_active]))
        days_active = days_active[days_active <= HORIZON]
        sources = rng.choice(["app_open", "push", "web"], len(days_active), p=[0.7, 0.2, 0.1]).astype(object)
        if not first:
            sources[0] = return_source
        sessions_member.extend([i] * len(days_active))
        sessions_day.extend(days_active.tolist())
        sessions_source.extend(sources.tolist())
        last = int(days_active[-1])
        first = False

        # Quiet period: maybe a return, maybe never
        organic_gap = np.inf if rng.random() < NEVER_RETURN[kind] else max(2.0, rng.lognormal(np.log(70), 0.8))
        gap = organic_gap
        return_source = "app_open"
        if organic_gap > WINBACK_DAY and last + WINBACK_DAY <= HORIZON:
            variant = "holdout" if rng.random() < HOLDOUT_SHARE else "email"
            email_effect = False
            if variant == "email":
                if organic_gap > 90 and rng.random() < EMAIL_EXTRA_RETURN:
                    gap = WINBACK_DAY + max(1.0, rng.lognormal(np.log(4), 1.6))
                    email_effect = True
                    return_source = "email_link" if rng.random() < 0.9 else "app_open"
                elif organic_gap <= 90 and rng.random() < 0.55:
                    return_source = "email_link"  # would have come back anyway, but clicked the email
            assign_rows.append((i, last + WINBACK_DAY, variant))
            truth_rows.append((i, last + WINBACK_DAY, variant, bool(organic_gap <= 90), email_effect))
        if not np.isfinite(gap):
            break
        day = last + int(np.ceil(gap))
        kind = "reactivated" if gap >= 90 else kind

ids = np.array([f"c{100000 + i}" for i in range(N)])
to_date = lambda d: (FIRST_JOIN + pd.to_timedelta(np.asarray(d), unit="D")).date

pd.DataFrame({"member_id": ids, "joined_on": to_date(join_day)}).to_csv(OUT / "members.csv", index=False)
pd.DataFrame({
    "member_id": ids[np.array(sessions_member)],
    "session_date": to_date(sessions_day),
    "entry_source": sessions_source,
}).sort_values(["member_id", "session_date"]).to_csv(OUT / "sessions.csv", index=False)
a = pd.DataFrame(assign_rows, columns=["m", "day", "variant"])
pd.DataFrame({
    "member_id": ids[a.m], "campaign": "winback_60d", "assigned_on": to_date(a.day), "variant": a.variant,
}).to_csv(OUT / "winback_assignments.csv", index=False)
# Not something a real company has: what each member would have done without the email
t = pd.DataFrame(truth_rows, columns=["m", "day", "variant", "would_return_by_day_90", "returned_because_of_email"])
pd.DataFrame({
    "member_id": ids[t.m], "assigned_on": to_date(t.day), "variant": t.variant,
    "would_return_by_day_90": t.would_return_by_day_90, "returned_because_of_email": t.returned_because_of_email,
}).to_csv(OUT / "truth_winback.csv", index=False)

print(f"members: {N:,}  sessions: {len(sessions_day):,}  win-back assignments: {len(a):,} "
      f"(holdout {(a.variant == 'holdout').mean():.1%})")
