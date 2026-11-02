import os
import html
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

USERNAME = os.getenv("GITHUB_USERNAME", "otp-katana")
TOKEN = os.getenv("GITHUB_TOKEN")

OUTPUT = Path("assets/github-signal.svg")

BG = "#08080F"
PANEL = "#12101A"
ACCENT = "#BEAED5"
BRIGHT = "#E8D5EF"
MUTED = "#AAA5B9"
DIM = "#625C70"
GRID = "#282333"

if not TOKEN:
    raise RuntimeError("GITHUB_TOKEN environment variable is missing.")

def github_graphql(query):
    payload = json.dumps({"query": query}).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "ACE-GitHub-Signal",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise RuntimeError(f"GitHub GraphQL error: {result['errors']}")

    return result["data"]["user"]


def safe(value):
    return html.escape(str(value))


def format_number(value):
    return f"{value:,}"


def contribution_streak(days):
    active_dates = {
        day["date"]
        for day in days
        if day["contributionCount"] > 0
    }

    today = datetime.now(timezone.utc).date()
    current = today.isoformat()

    if current not in active_dates:
        current = (today - timedelta(days=1)).isoformat()

    streak = 0
    cursor = datetime.fromisoformat(current).date()

    while cursor.isoformat() in active_dates:
        streak += 1
        cursor -= timedelta(days=1)

    longest = 0
    running = 0
    previous = None

    for date_string in sorted(active_dates):
        date = datetime.fromisoformat(date_string).date()

        if previous and date == previous + timedelta(days=1):
            running += 1
        else:
            running = 1

        longest = max(longest, running)
        previous = date

    return streak, longest


def heat_color(count):
    if count == 0:
        return "#211D2B"
    if count <= 2:
        return "#554665"
    if count <= 5:
        return "#806A9A"
    if count <= 9:
        return "#A58ABF"
    return ACCENT


def build_svg(user):
    repositories = user["repositories"]["nodes"]

    stars = sum(repo["stargazerCount"] for repo in repositories)
    forks = sum(repo["forkCount"] for repo in repositories)

    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]

    days = [
        day
        for week in weeks
        for day in week["contributionDays"]
    ]

    current_streak, longest_streak = contribution_streak(days)

    total_contributions = calendar["totalContributions"]
    commits = user["contributionsCollection"]["totalCommitContributions"]
    pull_requests = user["contributionsCollection"]["totalPullRequestContributions"]
    issues = user["contributionsCollection"]["totalIssueContributions"]

    updated = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")

    def metric(x, label, value):
        return f"""
        <g>
          <text x="{x}" y="150" class="metric-label">{label}</text>
          <text x="{x}" y="184" class="metric-value">{safe(format_number(value))}</text>
        </g>
        """

    metrics = "".join([
        metric(42, "PUBLIC REPOSITORIES", user["repositories"]["totalCount"]),
        metric(285, "TOTAL STARS", stars),
        metric(528, "TOTAL FORKS", forks),
        metric(771, "FOLLOWERS", user["followers"]["totalCount"]),
    ])

    heatmap = []
    cell = 11
    gap = 4
    start_x = 44
    start_y = 278

    for week_index, week in enumerate(weeks[-53:]):
        for day in week["contributionDays"]:
            date = datetime.fromisoformat(day["date"]).date()
            weekday = date.weekday()

            x = start_x + week_index * (cell + gap)
            y = start_y + weekday * (cell + gap)

            heatmap.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'rx="2" fill="{heat_color(day["contributionCount"])}">'
                f'<title>{safe(day["date"])}: '
                f'{day["contributionCount"]} contributions</title></rect>'
            )

    heatmap_svg = "".join(heatmap)

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
      width="1000" height="420" viewBox="0 0 1000 420"
      role="img" aria-labelledby="title description">

      <title id="title">ACE GitHub Signal — {safe(USERNAME)}</title>
      <desc id="description">
        GitHub profile statistics and contribution activity for {safe(USERNAME)}.
      </desc>

      <defs>
        <linearGradient id="accentLine" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="{ACCENT}"/>
          <stop offset="100%" stop-color="{DIM}"/>
        </linearGradient>
      </defs>

      <style>
        text {{
          font-family: 'Segoe UI', Arial, sans-serif;
        }}
        .eyebrow {{
          fill: {ACCENT};
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 2.4px;
        }}
        .heading {{
          fill: {BRIGHT};
          font-size: 22px;
          font-weight: 600;
          letter-spacing: 1px;
        }}
        .muted {{
          fill: {MUTED};
          font-size: 11px;
        }}
        .metric-label {{
          fill: {MUTED};
          font-size: 10px;
          letter-spacing: 1.5px;
        }}
        .metric-value {{
          fill: {BRIGHT};
          font-size: 27px;
          font-weight: 600;
        }}
        .small-value {{
          fill: {ACCENT};
          font-size: 16px;
          font-weight: 600;
        }}
      </style>

      <rect width="1000" height="420" rx="10" fill="{BG}"/>
      <rect x="1" y="1" width="998" height="418" rx="9"
        fill="none" stroke="{GRID}"/>

      <text x="42" y="42" class="eyebrow">ACE / DATA TERMINAL</text>
      <text x="42" y="76" class="heading">GITHUB SIGNAL</text>
      <text x="42" y="101" class="muted">
        @{safe(USERNAME)} · PUBLIC PROFILE ANALYTICS
      </text>

      <text x="958" y="43" text-anchor="end" class="eyebrow">
        SYSTEM ONLINE
      </text>
      <circle cx="966" cy="64" r="3" fill="{ACCENT}"/>
      <text x="958" y="89" text-anchor="end" class="muted">
        UPDATED {safe(updated)}
      </text>

      <rect x="32" y="119" width="936" height="86" rx="6"
        fill="{PANEL}" stroke="{GRID}"/>
      {metrics}

      <line x1="42" y1="222" x2="958" y2="222"
        stroke="url(#accentLine)" opacity=".65"/>

      <text x="42" y="250" class="eyebrow">ACTIVITY MATRIX</text>
      <text x="958" y="250" text-anchor="end" class="muted">
        LAST 12 MONTHS · {format_number(total_contributions)} CONTRIBUTIONS
      </text>

      {heatmap_svg}

      <text x="42" y="388" class="muted">
        COMMITS <tspan class="small-value">{format_number(commits)}</tspan>
      </text>
      <text x="285" y="388" class="muted">
        PULL REQUESTS <tspan class="small-value">{format_number(pull_requests)}</tspan>
      </text>
      <text x="528" y="388" class="muted">
        ISSUES <tspan class="small-value">{format_number(issues)}</tspan>
      </text>
      <text x="771" y="388" class="muted">
        CURRENT STREAK <tspan class="small-value">{current_streak}D</tspan>
      </text>

      <text x="958" y="407" text-anchor="end"
        fill="{DIM}" font-size="9" letter-spacing="1">
        ACE // REACH TO PEAK
      </text>
    </svg>
    """


def main():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=365)

    query = f'''
    {{
      user(login: "{USERNAME}") {{
        login
        followers {{
          totalCount
        }}
        repositories(
          first: 100
          ownerAffiliations: OWNER
          privacy: PUBLIC
        ) {{
          totalCount
          nodes {{
            stargazerCount
            forkCount
          }}
        }}
        contributionsCollection(
          from: "{start.strftime("%Y-%m-%dT%H:%M:%SZ")}"
          to: "{now.strftime("%Y-%m-%dT%H:%M:%SZ")}"
        ) {{
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          contributionCalendar {{
            totalContributions
            weeks {{
              contributionDays {{
                date
                contributionCount
              }}
            }}
          }}
        }}
      }}
    }}
    '''

    user = github_graphql(query)

    if not user:
        raise RuntimeError(f"GitHub user not found: {USERNAME}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_svg(user), encoding="utf-8")

    print(f"ACE GitHub Signal generated: {OUTPUT}")


if __name__ == "__main__":
    main()
