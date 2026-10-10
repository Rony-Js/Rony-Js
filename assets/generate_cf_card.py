import requests
from datetime import datetime

HANDLE = "Rony-js"


def fetch_user_info(handle):
    url = f"https://codeforces.com/api/user.info?handles={handle}"
    response = requests.get(url, timeout=10)
    data = response.json()

    if data.get("status") != "OK":
        raise Exception("Failed to fetch Codeforces user info")

    return data["result"][0]


def fetch_submissions(handle):
    url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=10000"
    response = requests.get(url, timeout=15)
    data = response.json()

    if data.get("status") != "OK":
        raise Exception("Failed to fetch Codeforces submissions")

    return data["result"]


def count_solved_problems(submissions):
    solved = set()

    for sub in submissions:
        if sub.get("verdict") == "OK":
            problem = sub.get("problem", {})
            contest_id = problem.get("contestId", "")
            index = problem.get("index", "")
            name = problem.get("name", "")
            solved.add(f"{contest_id}-{index}-{name}")

    return len(solved)


def get_rank_color(rank):
    colors = {
        "newbie": "#808080",
        "pupil": "#008000",
        "specialist": "#03A89E",
        "expert": "#0000FF",
        "candidate master": "#AA00AA",
        "master": "#FF8C00",
        "international master": "#FF8C00",
        "grandmaster": "#FF0000",
        "international grandmaster": "#FF0000",
        "legendary grandmaster": "#FF0000",
    }
    return colors.get(str(rank).lower(), "#58A6FF")


def safe_text(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def shorten(text, limit=18):
    text = safe_text(text)
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def generate_svg(user, solved_count):
    handle = user.get("handle", HANDLE)

    first_name = user.get("firstName", "")
    last_name = user.get("lastName", "")
    full_name = f"{first_name} {last_name}".strip()

    if not full_name:
        full_name = "Not Set"

    full_name = shorten(full_name, 18)

    rank = user.get("rank", "unrated")
    rating = user.get("rating", "N/A")
    max_rank = user.get("maxRank", "unrated")
    max_rating = user.get("maxRating", "N/A")
    friends = user.get("friendOfCount", 0)

    rank_color = get_rank_color(rank)
    updated = datetime.now().astimezone().strftime("%Y-%m-%d")

    svg = f'''<svg width="800" height="280" viewBox="0 0 800 280" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="800" height="280" rx="22" fill="#0D1117"/>
  <rect x="1" y="1" width="798" height="278" rx="22" stroke="#30363D" stroke-width="2"/>

<rect x="55" y="24" width="10" height="30" rx="2" fill="#F7B100"/>
<rect x="70" y="14" width="10" height="40" rx="2" fill="#1F8ACB"/>
<rect x="85" y="29" width="10" height="25" rx="2" fill="#D9534F"/>

 <text x="112" y="52" fill="#FFFFFF" font-size="30" font-family="Segoe UI, Arial, sans-serif">CODEFORCES</text>

  <text x="30" y="78" fill="#8B949E" font-size="14" font-family="Segoe UI, Arial, sans-serif">
    Competitive Programming Progress
  </text>

  <rect x="30" y="105" width="740" height="130" rx="16" fill="#161B22"/>
  <rect x="30" y="105" width="740" height="130" rx="16" stroke="#30363D"/>

  <text x="55" y="145" fill="#8B949E" font-size="15" font-family="Segoe UI, Arial, sans-serif">Name</text>
  <text x="205" y="145" fill="#F0F6FC" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="600">{full_name}</text>

  <text x="55" y="175" fill="#8B949E" font-size="15" font-family="Segoe UI, Arial, sans-serif">Handle</text>
  <text x="205" y="175" fill="#58A6FF" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{safe_text(handle)}</text>

  <text x="55" y="205" fill="#8B949E" font-size="15" font-family="Segoe UI, Arial, sans-serif">Friends</text>
  <text x="205" y="205" fill="#F0F6FC" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="600">{friends}</text>

  <text x="490" y="145" fill="#8B949E" font-size="15" font-family="Segoe UI, Arial, sans-serif">Rating</text>
  <text x="640" y="145" fill="{rank_color}" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{rating} ({safe_text(rank)})</text>

  <text x="490" y="175" fill="#8B949E" font-size="15" font-family="Segoe UI, Arial, sans-serif">Max Rating</text>
  <text x="640" y="175" fill="#F0F6FC" font-size="17" font-family="Segoe UI, Arial, sans-serif" font-weight="600">{max_rating} ({safe_text(max_rank)})</text>

  <text x="490" y="205" fill="#8B949E" font-size="15" font-family="Segoe UI, Arial, sans-serif">Solved</text>
  <text x="640" y="205" fill="#58A6FF" font-size="18" font-family="Segoe UI, Arial, sans-serif" font-weight="700">{solved_count}</text>

  <text x="30" y="258" fill="#8B949E" font-size="13" font-family="Segoe UI, Arial, sans-serif">
    Updated: {updated} • Keep solving, keep improving.
  </text>
</svg>'''

    return svg


def main():
    user = fetch_user_info(HANDLE)
    submissions = fetch_submissions(HANDLE)
    solved_count = count_solved_problems(submissions)

    svg = generate_svg(user, solved_count)

    with open("assets/codeforces-stats.svg", "w", encoding="utf-8") as file:
        file.write(svg)


if __name__ == "__main__":
    main()
