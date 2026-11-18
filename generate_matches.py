import json, os, re
from datetime import datetime, timedelta
import requests
import pytz

from poster_maker import create_poster

BD = pytz.timezone("Asia/Dhaka")
NOW_BD = datetime.now(BD)
TODAY_BD = NOW_BD.date()
END_DATE = TODAY_BD + timedelta(days=2)

SONYLIV_API = os.getenv("SonyLiv_API")
FANCEODE_API = os.getenv("FANCEODE_API")
TAPMAD_API = os.getenv("TAPMAD_API")

DEFAULT_IMAGE = os.environ.get("DEFAULT_IMAGE", "https://i.postimg.cc/2jPs7rBr/HOME-LIVE-EVENT.png")
SUBTITLE_SUFFIX = os.environ.get("SUBTITLE_SUFFIX", " | Select 🅻🅸🅅🅴 🆂🅿🅾🆁🆃🆂 Button, Share Our Apps With Your Friends & Family.")

GITHUB_USER = "sujukichinna4321"
GITHUB_REPO = "JobsFile"
GITHUB_BRANCH = "main"

FOOTBALL_LEAGUES = {
    "premier league":   ("ENGLISH PREMIER LEAGUE 2026/27", "TNT 1"),
    "la liga":          ("SPANISH LA LIGA 2026/27",       "SonyLiv"),
    "bundesliga":       ("GERMAN BUNDESLIGA 2026/27",      "SonyLiv"),
    "serie a":          ("ITALIAN SERIE A 2026/27",        "SonyLiv"),
    "ligue 1":          ("FRENCH LIGUE 1 2026/27",         "SonyLiv"),
    "champions league": ("UEFA CHAMPIONS LEAGUE 2026/27",  "SonyLiv"),
    "europa league":    ("UEFA EUROPA LEAGUE 2026/27",     "SonyLiv"),
    "nations league":   ("FRIENDLY MATCH NATIONS LEAGUE 2026/27", "SonyLiv"),
    "fifa world cup":   ("FIFA WORLD CUP 2026",            "T Sports"),
    "friendly":         ("FRIENDLY MATCH 2026",            "T Sports"),
}

CRICKET_LEAGUES = {
    "t20i":      ("T20I CRICKET 2026",              "Fancode"),
    "t20":       ("T20 CRICKET 2026",               "Fancode"),
    "t10":       ("T10 CRICKET 2026",               "Fancode"),
    "odi":       ("ODI CRICKET 2026",               "Fancode"),
    "test":      ("TEST CRICKET 2026",              "Fancode"),
    "world cup": ("ICC MEN'S T20 WORLD CUP 2026", "Willow"),
    "ipl":       ("INDIAN PREMIER LEAGUE 2026",     "SonyLiv"),
    "bbl":       ("BIG BASH LEAGUE 2026",           "SonyLiv"),
    "psl":       ("PSL 2026",                       "Tapmad"),
    "bpl":       ("BPL 2026",                       "T Sports"),
    "nepal":     ("NEPAL PREMIER LEAGUE 2026",      "Fancode"),
}

POPULAR_KEYWORDS = [
    "bangladesh", "pakistan", "india", "bpl", "psl", "ipl", "world cup", 
    "asia cup", "champions trophy", "premier league", "la liga", "champions league",
    "real madrid", "barcelona", "manchester", "liverpool", "arsenal", "chelsea", 
    "bayern", "psg", "juventus", "brazil", "argentina", "kolkata", "mumbai", 
    "chennai", "karachi", "lahore", "dhaka", "comilla", "brisbane", "sydney", 
    "melbourne", "perth", "hobart", "women", "inter"
]

IGNORE_SPORTS = [
    "doubles", "atp", "wta", "tur", "turin", "day 1", "day 2", "day 3", "day 4",
    "race", "practice", "qualifying", "grand prix", "tennis", "golf",
    "georgia", "spain", "barcelona", "las vegas", "circuit", "round of 16"
]

def format_team_name(name):
    formatted = name
    formatted = re.sub(r'\bWomen\b', '(W)', formatted, flags=re.IGNORECASE)
    formatted = re.sub(r'\bMen\b', '(M)', formatted, flags=re.IGNORECASE)
    formatted = re.sub(r'\bU(\d+)\b', r'(U\1)', formatted, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', formatted).strip()

def fetch_json(url, headers=None):
    if not url: return []
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Warning: Failed to fetch data from {url}. Skipping...")
        return []

def _iter_events(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for k in ("events", "data", "matches", "items", "results", "response"):
            v = data.get(k)
            if isinstance(v, list): return v
    return []

def parse_start(ev):
    if "EventStartDate" in ev:
        try: return datetime.strptime(ev["EventStartDate"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=BD)
        except: pass
    if "startTime" in ev:
        try: return datetime.strptime(ev["startTime"], "%I:%M:%S %p %d-%m-%Y").replace(tzinfo=BD)
        except: pass
    return None

def extract_teams(ev):
    if "team_1" in ev and "team_2" in ev:
        return str(ev["team_1"]).strip(), str(ev["team_2"]).strip()
    if "VideoName" in ev and " vs " in ev["VideoName"]:
        parts = ev["VideoName"].split(" vs ")
        if len(parts) >= 2: return parts[0].strip(), parts[1].strip()
    return "", ""

def extract_competition(ev):
    if "CategoryName" in ev: return ev["CategoryName"]
    if "event_name" in ev: return ev["event_name"]
    return ""

def detect_sport(ev, comp):
    s = (ev.get("sport") or ev.get("sportType") or ev.get("event_category") or "").lower()
    c = (comp or "").lower()
    if "cricket" in s or any(x in c for x in ("cricket", "t20", "t10", "odi", "test", "ipl", "bbl", "psl", "bpl", "icc", "nepal")):
        return "cricket"
    return "football"

def guess_format(comp):
    c = (comp or "").lower()
    if "t10" in c: return "T10"
    if "t20" in c: return "T20"
    if "odi" in c or "one day" in c: return "ODI"
    if "test" in c: return "Test"
    return ""

def league_meta(sport, comp):
    c = (comp or "").lower()
    table = CRICKET_LEAGUES if sport == "cricket" else FOOTBALL_LEAGUES
    for key, val in table.items():
        if key in c: return val
    return ("CRICKET 2026" if sport == "cricket" else "FOOTBALL 2026", "Fancode" if sport == "cricket" else "T Sports")

def bst_str(dt):
    return dt.strftime("%d-%m-%Y-%I:%M 00 %p").lower()

def get_poster_link(t1, t2, sub_name, fmt, sport, start):
    try:
        t1_safe = re.sub(r'[^a-zA-Z0-9]', '_', t1)
        t2_safe = re.sub(r'[^a-zA-Z0-9]', '_', t2)
        date_str = start.strftime("%Y%m%d")
        filename = f"{sport}_{t1_safe}_vs_{t2_safe}_{date_str}.jpg"
        
        sport_type = "Cricket" if sport == "cricket" else "Soccer"
        match_type = fmt if fmt else ""
        
        create_poster(team1=t1, team2=t2, series_name=sub_name, match_type=match_type, output_filename=filename, sport_type=sport_type)
        
        raw_link = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/posters/{filename}"
        return raw_link
    except Exception:
        return None

def is_popular_and_valid(t1, t2, comp):
    full_text = f"{t1} {t2} {comp}".lower()
    if "tbc" in t1.lower() or "tbc" in t2.lower(): return False
    for word in IGNORE_SPORTS:
        if word in full_text: return False
    for keyword in POPULAR_KEYWORDS:
        if keyword in full_text: return True
    return False

def build_entry(ev, platform_tag):
    start = parse_start(ev)
    if not start: return None
    if not (TODAY_BD <= start.date() <= END_DATE): return None 
        
    t1, t2 = extract_teams(ev)
    if not t1 or not t2: return None

    comp = extract_competition(ev)
    if not is_popular_and_valid(t1, t2, comp): return None

    sport = detect_sport(ev, comp)
    sub_name, default_channel = league_meta(sport, comp)
    
    channel = default_channel
    if "channel" in ev: channel = ev["channel"]
    
    fmt = guess_format(comp) if sport == "cricket" else ""

    # নোটিফিকেশন টাইটেলে সংক্ষিপ্ত রূপ ব্যবহার
    t1_fmt = format_team_name(t1)
    t2_fmt = format_team_name(t2)
    title = f"{t1_fmt} 🆚 {t2_fmt} । Watch on {channel}"
    
    subtitle = f"{sub_name}{SUBTITLE_SUFFIX}"
    
    poster_url = get_poster_link(t1, t2, sub_name, fmt, sport, start)
    image = poster_url if poster_url else DEFAULT_IMAGE
    date_time = bst_str(start - timedelta(minutes=5))

    return {
        "Date & Time": date_time,
        "multipleTimeRun": "Off",
        "multipleTime": "",
        "Title": title,
        "Subtitle": subtitle,
        "Image": image,
    }

def main():
    results, seen = [], set()
    
    broadcast_sources = [
        ("fancode", FANCEODE_API, "Fancode"),
        ("sonyliv", SONYLIV_API, "SonyLiv"),
        ("tapmad",  TAPMAD_API, "Tapmad")
    ]
    
    for name, url, tag in broadcast_sources:
        if not url: 
            print(f"Warning: {name} API URL is not set in secrets. Skipping...")
            continue
            
        events = _iter_events(fetch_json(url))
        for ev in events:
            try:
                entry = build_entry(ev, tag)
                if entry:
                    key = (entry["Title"], entry["Date & Time"])
                    if key not in seen:
                        seen.add(key)
                        results.append(entry)
            except: pass

    with open("notifications.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Generated notifications.json with {len(results)} entries.", flush=True)

if __name__ == "__main__":
    main()
