"""gta6-twitch-ccu-forecast-01 entry: comparable-launch shape forecaster.

Reads a case (<id>.in), learns the launch-day hour-by-hour shape from the
comparable launches embedded in the case, and writes <id>.out with 5 quantiles
for each of hours 2..24. Standard library only, no network, deterministic.

Strategy:
  p1 = hour-1 print (from `known`, floor at 1 viewer)
  For each comparable: align its hourly points to launch-day hours
     (hour h = [day_start + (h-1)h, day_start + h*h)), average viewers per hour,
     compute ratio v_h / v_1 per hour.
  Aggregate ratios per hour across comparables (size-weighted median).
  Spread per hour from the dispersion of ratios across comparables (IQR -> log sigma),
  floored at the house baseline's 0.15*sqrt(h-1) so we never under-spread.
  q_tau(h) = p1 * r_h * exp(z_tau * sigma_h), rounded to 2 decimals (half up).
"""

import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]
SIGMA_BASE = 0.15  # house baseline spread, log units per sqrt hour


def round2(x):
    """Round to 2 decimals, half up, like JS Math.round(x*100)/100."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 1.0
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


def percentile(vals, p):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 1.0
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def comparable_size_weight(comp):
    """Weight a comparable by its peak launch-day viewers (bigger = more like GTA VI)."""
    hourly = comp.get("hourly", [])
    day_start = comp.get("day_start")
    if not hourly or not day_start:
        return 1.0
    ds = parse_ts(day_start)
    peak = 0.0
    for pt in hourly:
        at = parse_ts(pt["from"])
        delta_h = (at - ds).total_seconds() / 3600.0
        if 0 <= delta_h < 24:
            peak = max(peak, float(pt.get("viewers", 0)))
    return max(peak, 1.0)


def launch_day_hourly(comp):
    """Return {hour: mean_viewers} for launch day hours 1..24, or None if no hour-1 data."""
    hourly = comp.get("hourly", [])
    day_start = comp.get("day_start")
    if not hourly or not day_start:
        return None
    ds = parse_ts(day_start)
    hour_vals = {}
    for pt in hourly:
        at = parse_ts(pt["from"])
        delta_h = (at - ds).total_seconds() / 3600.0
        if delta_h < 0 or delta_h >= 24:
            continue
        h = int(delta_h) + 1  # 1-indexed launch-day hour
        hour_vals.setdefault(h, []).append(float(pt.get("viewers", 0)))
    if 1 not in hour_vals:
        return None
    v1 = sum(hour_vals[1]) / len(hour_vals[1])
    if v1 <= 0:
        return None
    result = {}
    for h in range(1, 25):
        if h in hour_vals:
            result[h] = sum(hour_vals[h]) / len(hour_vals[h])
    result[1] = v1
    return result


def forecast_case(case, name):
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))

    # Collect (ratio, weight) per hour from comparables
    ratio_samples = {h: [] for h in range(2, 25)}  # h -> list of (ratio, weight)

    for comp in case.get("comparables", []):
        ld = launch_day_hourly(comp)
        if ld is None:
            continue
        weight = comparable_size_weight(comp)
        v1 = ld[1]
        for h in range(2, 25):
            if h in ld:
                ratio_samples[h].append((ld[h] / v1, weight))

    hours_out = []
    for h in range(2, 25):
        samples = ratio_samples[h]
        if samples:
            ratios = [r for r, _ in samples]
            weights = [w for _, w in samples]
            # Weighted median: sort by ratio, find middle by cumulative weight
            paired = sorted(zip(ratios, weights), key=lambda x: x[0])
            total_w = sum(weights)
            cum = 0.0
            r_h = paired[-1][0]  # fallback
            for r, w in paired:
                cum += w
                if cum >= total_w / 2:
                    r_h = r
                    break
            # Spread from weighted dispersion: use weighted quantiles of ratios
            # Simple approach: IQR of unweighted ratios, converted to log sigma
            q25_r = percentile(ratios, 0.25)
            q75_r = percentile(ratios, 0.75)
            iqr_log = math.log(max(q75_r, 1e-9)) - math.log(max(q25_r, 1e-9))
            sigma_h = iqr_log / 1.349  # IQR -> sigma for normal
            # Floor: never spread less than the house baseline at this hour
            sigma_h = max(sigma_h, SIGMA_BASE * math.sqrt(h - 1))
            sigma_h = min(sigma_h, 1.5)  # cap absurd spreads
        else:
            r_h = 1.0
            sigma_h = SIGMA_BASE * math.sqrt(h - 1)

        q = [round2(p1 * r_h * math.exp(z * sigma_h)) for z in Z]
        hours_out.append({"hour": h, "q": q})

    return {"hours": hours_out}


def main():
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(input_dir.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (output_dir / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
