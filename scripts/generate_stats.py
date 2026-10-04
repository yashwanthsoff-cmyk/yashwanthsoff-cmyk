"""Fetch live contribution data from GitHub's GraphQL API and render an SVG card."""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone

LOGIN = os.environ.get("GH_LOGIN", "yashwanthsoff-cmyk")
OUT = os.environ.get("OUT_PATH", "stats/contributions.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(token):
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    return cal["totalContributions"], days


def compute_streaks(days):
    today = datetime.now(timezone.utc).date()
    series = sorted(
        (date.fromisoformat(d["date"]), d["contributionCount"]) for d in days
    )
    series = [(d, c) for d, c in series if d <= today]

    longest = (0, None, None)
    run, start = 0, None
    for d, c in series:
        if c > 0:
            if run == 0:
                start = d
            run += 1
            if run > longest[0]:
                longest = (run, start, d)
        else:
            run = 0

    # Current streak: today may not have contributions yet, so allow it to be empty.
    cur, cur_start = 0, None
    i = len(series) - 1
    if i >= 0 and series[i][1] == 0:
        i -= 1
    while i >= 0 and series[i][1] > 0:
        cur += 1
        cur_start = series[i][0]
        i -= 1
    cur_end = series[-1][0] if cur else None
    return (cur, cur_start, cur_end), longest


def fmt_range(start, end):
    if not start or not end:
        return "-"
    f = lambda d: d.strftime("%b ") + str(d.day)
    return f(start) if start == end else f"{f(start)} - {f(end)}"


def render(total, current, longest):
    cur_n, cur_s, cur_e = current
    lon_n, lon_s, lon_e = longest
    font = "font-family=\"'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif\""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="GitHub contributions: {total} in the last year, current streak {cur_n}, longest streak {lon_n}">
  <rect x="0.5" y="0.5" width="494" height="194" rx="4.5" fill="#20232a"/>
  <line x1="165" y1="28" x2="165" y2="167" stroke="#61dafb" stroke-opacity="0.35"/>
  <line x1="330" y1="28" x2="330" y2="167" stroke="#61dafb" stroke-opacity="0.35"/>

  <g text-anchor="middle" {font}>
    <text x="82" y="94" font-size="28" font-weight="700" fill="#ffffff">{total}</text>
    <text x="82" y="122" font-size="14" fill="#61dafb">Total Contributions</text>
    <text x="82" y="146" font-size="12" fill="#ffffff">Last 12 months</text>

    <circle cx="247" cy="82" r="40" fill="none" stroke="#61dafb" stroke-width="5"/>
    <text x="247" y="92" font-size="28" font-weight="700" fill="#ffffff">{cur_n}</text>
    <text x="247" y="148" font-size="14" font-weight="700" fill="#61dafb">Current Streak</text>
    <text x="247" y="168" font-size="12" fill="#ffffff">{fmt_range(cur_s, cur_e)}</text>

    <text x="412" y="94" font-size="28" font-weight="700" fill="#ffffff">{lon_n}</text>
    <text x="412" y="122" font-size="14" fill="#61dafb">Longest Streak</text>
    <text x="412" y="146" font-size="12" fill="#ffffff">{fmt_range(lon_s, lon_e)}</text>
  </g>
</svg>
"""


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GH_TOKEN is not set")
    total, days = fetch(token)
    current, longest = compute_streaks(days)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(total, current, longest))
    print(f"total={total} current={current[0]} longest={longest[0]}")


if __name__ == "__main__":
    main()
