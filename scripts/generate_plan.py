#!/usr/bin/env python3
"""
Generate a 26-week marathon-prep cardio plan (Jun 1 -> Nov 29 2026) and
patch the DEFAULT_WORKOUT_DATA JSON literal embedded on line 20 of index.html.

Design constraints (from the user):
  - AM + PM cardio every day, no weight lifting.
  - Modalities: cycling, running, rowing, ski erg, stretching.
  - Stretching/mobility every day (at least one session).
  - Marathon stays on Sun Nov 29, 2026.

Periodization
  W1-6   Base       long run 6 -> 11mi (cutback W4 at 7)
  W7-14  Build      long run 12 -> 18 with cutbacks at W10 (10) and W14 (14)
  W15-22 Peak       long run 19 -> 22 with cutbacks at W18 (15) and W22 (16)
  W23    Sharpen    last big workout, long run 12
  W24-26 Taper      long run 10 -> 6 -> Marathon
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

START = date(2026, 6, 1)        # Mon
RACE = date(2026, 11, 29)       # Sun, week 26 day 7

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---- session library ---------------------------------------------------------

def stretch_session(label="Mobility + Stretch (30 min)"):
    """Daily mobility / stretching slot, modeled as exercise-driven so it shows
    a checklist in the React tracker."""
    return {
        "session": label,
        "type": "Strength",
        "exercises": [
            {"name": "Foam roll: quads, IT band, calves",
             "sets": "1", "reps": "60s/area",
             "notes": "Slow passes; pause on tender spots."},
            {"name": "Couch stretch (hip flexor)",
             "sets": "1", "reps": "60-90s/side",
             "notes": "Glute squeeze; ribs down; no lumbar arch."},
            {"name": "Soleus wall stretch",
             "sets": "2", "reps": "30-45s/side",
             "notes": "Knee bent; target lower calf / Achilles."},
            {"name": "Pigeon stretch",
             "sets": "1", "reps": "60s/side",
             "notes": "Square hips; breathe into the glute."},
            {"name": "Adductor rockbacks",
             "sets": "2", "reps": "10/side",
             "notes": "Slow; neutral spine; pause at end range."},
            {"name": "Open books (T-spine)",
             "sets": "1", "reps": "8/side",
             "notes": "Exhale into rotation; keep knees stacked."},
            {"name": "90/90 hip switches",
             "sets": "2", "reps": "8/side",
             "notes": "Tall posture; control the transition."},
            {"name": "Standing hamstring stretch",
             "sets": "1", "reps": "45s/side",
             "notes": "Hinge from hip; soft knee."},
        ],
        "notes": None,
    }


def cardio(session, notes):
    return {"session": session, "type": "Run/Cardio", "exercises": None, "notes": notes}


# Bike / row / ski-erg prescriptions by week phase ------------------------------

def bike_easy(week):
    minutes = 40 if week <= 6 else 50 if week <= 14 else 60 if week <= 22 else 40
    return cardio("Cycling - Zone 2", f"{minutes} min easy spin, HR < 70% max, conversational.")


def bike_tempo(week):
    if week <= 6:
        body = "3 x 8 min tempo at RPE 7 / 2 min easy"
    elif week <= 14:
        body = "4 x 10 min tempo at RPE 7-8 / 2 min easy"
    elif week <= 22:
        body = "3 x 15 min sweet-spot at RPE 7-8 / 3 min easy"
    else:
        body = "2 x 8 min tempo at RPE 6-7 / 3 min easy (taper)"
    return cardio("Cycling - Tempo Intervals",
                  f"10 min warm-up; {body}; 10 min cool-down.")


def row_intervals(week):
    if week <= 6:
        body = "5 x 500m @ 2k+10s pace / 2 min easy paddle"
    elif week <= 14:
        body = "6 x 500m @ 2k+5s / 90s easy paddle"
    elif week <= 22:
        body = "4 x 1000m @ 2k+8s / 2 min easy paddle"
    else:
        body = "4 x 500m @ 2k+10s / 2 min easy (taper)"
    return cardio("Rowing - Intervals",
                  f"8 min easy warm-up; {body}; 8 min easy cool-down.")


def row_easy(week):
    minutes = 20 if week <= 6 else 25 if week <= 14 else 30 if week <= 22 else 20
    return cardio("Rowing - Steady",
                  f"{minutes} min steady at 22-24 spm, easy aerobic.")


def ski_erg(week):
    if week <= 6:
        body = "8 x 30s hard / 90s easy"
    elif week <= 14:
        body = "10 x 40s hard / 80s easy"
    elif week <= 22:
        body = "8 x 60s hard / 60s easy"
    else:
        body = "6 x 30s moderate / 90s easy (taper)"
    return cardio("Ski Erg - Power Intervals",
                  f"5 min warm-up; {body}; 5 min cool-down.")


def ski_erg_easy(week):
    minutes = 15 if week <= 6 else 20 if week <= 14 else 25 if week <= 22 else 15
    return cardio("Ski Erg - Aerobic",
                  f"{minutes} min steady, smooth long pulls, nasal breathing.")


# Running ----------------------------------------------------------------------

LONG_RUN_BY_WEEK = {
    1: 6, 2: 7, 3: 8, 4: 7, 5: 10, 6: 11,
    7: 12, 8: 13, 9: 14, 10: 10, 11: 15, 12: 16, 13: 17, 14: 14,
    15: 18, 16: 19, 17: 20, 18: 15, 19: 20, 20: 22, 21: 22, 22: 16,
    23: 12,
    24: 10, 25: 8, 26: 26.2,
}


def easy_run_miles(week):
    if week <= 6: return 4
    if week <= 14: return 5
    if week <= 22: return 6
    if week == 23: return 5
    if week == 24: return 4
    if week == 25: return 3
    return 2


def quality_run(week):
    if week <= 6:
        body = "5 x 3 min @ 5k pace / 2 min jog"
    elif week <= 14:
        body = "6 x 800m @ 5k pace / 400m jog"
    elif week <= 22:
        body = "3 x 1 mi @ 10k pace / 800m jog"
    elif week == 23:
        body = "4 x 800m @ 10k pace / 400m jog (sharpener)"
    elif week == 24:
        body = "3 x 1 mi @ marathon pace / 90s jog"
    elif week == 25:
        body = "2 x 1 mi @ marathon pace / 2 min jog"
    else:
        body = "20 min easy with 4 x 30s strides"
    return cardio("Quality Run",
                  f"15 min easy warm-up; {body}; 15 min easy cool-down.")


def easy_run(week):
    return cardio("Easy Run", f"{easy_run_miles(week)} mi easy, conversational pace.")


def long_run(week):
    miles = LONG_RUN_BY_WEEK[week]
    if week == 26:
        return cardio("Marathon Race", "26.2 mi - MARATHON DAY. Pace controlled; fuel early and consistently; hydrate to conditions.")
    # Peak weeks (non-cutback) get marathon-pace work mid-run.
    if 15 <= week <= 21 and week != 18:
        notes = f"{miles} mi long run, mostly easy; include 4-6 mi at goal marathon pace mid-run."
    elif week == 23:  # sharpen: dress rehearsal
        notes = f"{miles} mi long run with last 3 mi at goal marathon pace."
    elif week in (24, 25):  # taper: keep it easy
        notes = f"{miles} mi long run, easy aerobic with 4 x 30s strides in last mile."
    else:
        notes = f"{miles} mi long run, easy aerobic, last 2 mi steady."
    return cardio("Long Run", notes)


# ---- weekly template --------------------------------------------------------
# Returns (am, pm) for a given (week, weekday_index 0=Mon..6=Sun)

def day_plan(week, dow):
    # Marathon week overrides
    if week == 26:
        plans = {
            0: (easy_run(week), stretch_session("Race Week Mobility (light)")),                # Mon
            1: (cardio("Easy Spin", "20 min very easy spin, legs light."), stretch_session()), # Tue
            2: (cardio("Shakeout Run", "2 mi very easy + 4 x 20s strides."), stretch_session("Race Week Mobility (light)")),
            3: (stretch_session("Race -2 Mobility"), cardio("Easy Walk", "20-30 min easy walk; hydrate.")),
            4: (cardio("Shakeout Run", "15 min easy jog + 4 x 20s strides."), stretch_session("Race -1 Mobility (very gentle)")),
            5: (stretch_session("Race Eve Mobility (light)"), cardio("Easy Walk", "15-20 min easy walk; lay out gear.")),
            6: (long_run(week), stretch_session("Post-Marathon Mobility (very gentle)")),     # Race Sunday
        }
        return plans[dow]

    # Standard week (with taper-aware tweaks via week-conditional helpers)
    if dow == 0:   # Mon - bike Z2 + stretch
        return bike_easy(week), stretch_session()
    if dow == 1:  # Tue - AM easy run, PM row intervals
        return easy_run(week), row_intervals(week)
    if dow == 2:  # Wed - AM ski erg power, PM bike tempo or easy
        am = ski_erg(week)
        pm = bike_tempo(week) if week not in (4, 10, 14, 18, 22, 24, 25) else bike_easy(week)
        return am, pm
    if dow == 3:  # Thu - AM quality run, PM stretch
        return quality_run(week), stretch_session("Evening Mobility + Stretch")
    if dow == 4:  # Fri - AM bike easy, PM row easy + stretch
        return bike_easy(week), row_easy(week)
    if dow == 5:  # Sat - AM long run, PM post-run stretch
        return long_run(week), stretch_session("Post-Long-Run Mobility")
    if dow == 6:  # Sun - AM easy cross-train (alternate row / ski erg), PM stretch
        am = row_easy(week) if week % 2 == 1 else ski_erg_easy(week)
        return am, stretch_session("Sunday Recovery Mobility")
    raise ValueError(dow)


# ---- assemble ---------------------------------------------------------------

def build_plan():
    plan = {}
    d = START
    while d <= RACE:
        delta_days = (d - START).days
        week = delta_days // 7 + 1
        dow = delta_days % 7              # 0 = Mon (start is Mon)
        am, pm = day_plan(week, dow)
        plan[d.isoformat()] = {
            "date": d.isoformat(),
            "week": week,
            "day": DAY_NAMES[dow],
            "am": am,
            "pm": pm,
        }
        d += timedelta(days=1)
    return plan


def patch_index(plan):
    text = INDEX.read_text()
    json_blob = json.dumps(plan, ensure_ascii=False, separators=(", ", ": "))
    # The literal is wedged between two stable anchors. Non-greedy .*? alone
    # is unsafe because notes strings inside the JSON contain semicolons —
    # so we anchor on the next top-level statement instead.
    pattern = re.compile(
        r"(const DEFAULT_WORKOUT_DATA = )[\s\S]*?(\n\s*const STORAGE_KEYS)"
    )
    new_text, n = pattern.subn(
        lambda m: f"{m.group(1)}\n{json_blob};{m.group(2)}",
        text,
        count=1,
    )
    if n != 1:
        raise RuntimeError(f"DEFAULT_WORKOUT_DATA replacement failed (count={n})")
    INDEX.write_text(new_text)
    return len(plan)


def main():
    plan = build_plan()
    n = patch_index(plan)
    first = min(plan)
    last = max(plan)
    weeks = max(v["week"] for v in plan.values())
    print(f"Wrote {n} days, {first} -> {last}, {weeks} weeks. Race: {last}")


if __name__ == "__main__":
    main()
