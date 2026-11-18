import json, os, re
from datetime import datetime, timedelta
import requests
import pytz

from poster_maker import create_poster

BD = pytz.timezone("Asia/Dhaka")
NOW_BD = datetime.now(BD)
TODAY_BD = NOW_BD.date()
END_DATE = TODAY_BD + timedelta(days=2)

DEFAULT_IMAGE = os.environ.get("DEFAULT_IMAGE", "https://i.postimg.cc/2jPs7rBr/HOME-LIVE-EVENT.png")
SUBTITLE_SUFFIX = os.environ.get("SUBTITLE_SUFFIX", " | Select 🅻🅸🅅🅴 🆂🅿🅾🆁🆃🆂 Button, Share Our Apps With Your Friends & Family.")

GITHUB_USER = "sujukichinna4321"
GITHUB_REPO = "JobsFile"
GITHUB_BRANCH = "main"

FOOTBALL_LEAGUES = {
    "premier league":   ("🏆 ENGLISH ⚽ PREMIER LEAGUE 2026/27", "TNT 1"),
    "la liga":          ("🏆 SPANISH ⚽ LA LIGA 2026/27",       "SonyLiv"),
    "bundesliga":       ("🏆 GERMAN ⚽ BUNDESLIGA 2026/27",      "SonyLiv"),
    "serie a":          ("🏆 ITALIAN ⚽ SERIE A 2026/27",        "SonyLiv"),
    "ligue 1":          ("🏆 FRENCH ⚽ LIGUE 1 2026/27",         "SonyLiv"),
    "champions league": ("🏆 UEFA ⚽ CHAMPIONS LEAGUE 2026/27",  "SonyLiv"),
    "europa league":    ("🏆 UEFA ⚽ EUROPA LEAGUE 2026/27",     "SonyLiv"),
    "nations league":   ("🏆 Friendly Match ⚽ NATIONS LEAGUE 2026/27", "SonyLiv"),
    "fifa world cup":   ("🏆 FIFA ⚽ WORLD CUP 2026",            "T Sports"),
    "friendly":         ("🏆 Friendly Match ⚽ 2026",            "T Sports"),
}

CRICKET_LEAGUES = {
    "t20i":      ("🏏 T20I CRICKET 2026",              "Fancode"),
    "t20":       ("🏏 T20 CRICKET 2026",               "Fancode"),
    "t10":       ("🏏 T10 CRICKET 2026",               "Fancode"),
    "odi":       ("🏏 ODI CRICKET 2026",               "Fancode"),
    "test":      ("🏏 TEST CRICKET 2026",              "Fancode"),
    "world cup": ("🏆 ICC 🏏 MEN'S T20 WORLD CUP 2026", "Willow"),
    "ipl":       ("🏏 INDIAN PREMIER LEAGUE 2026",     "SonyLiv"),
    "bbl":       ("🏏 BIG BASH LEAGUE 2026",           "SonyLiv"),
    "psl":       ("🏏 PSL 2026",                       "Tapmad"),
    "bpl":       ("🏏 BPL 2026",                       "T Sports"),
    "nepal":     ("🏏 NEPAL PREMIER LEAGUE 2026",      "Fancode"),
}

SOURCES = [
    ("fancode", "https://raw.githubusercontent.com/drmlive/fancode-live-events/main/fancode.json", "Fancode"),
    ("sonyliv", "https://raw.githubusercontent.com/drmlive/sliv-live-events/main/sonyliv.json",   "SonyLiv"),
    ("tapmad",  "https://gist.githubusercontent.com/albatr0ssss/3cff7a26be49b1d352c15f615067e7cd/raw/tapmad_bd.json", "Tapmad"),
]

def fetch_json(url):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []

def _iter_events(data):
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for k in ("events", "data", "matches", "items", "results"):
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
        return parts[0].strip(), parts[1].strip()
    return "", ""

def extract_competition(ev):
    if "CategoryName" in ev: return ev["CategoryName"]
    if "event_name" in ev: return ev["event_name"]
    return ""

def extract_channel(ev, default_channel):
    keys = ("channel", "broadcaster", "platform", "channel_name", "broadcast", "network")
    for k in keys:
        v = ev.get(k)
        if isinstance(v, str) and v.strip(): return v.strip()
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], str): return v[0].strip()
    return default_channel

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
    return "T20"

def league_meta(sport, comp):
    c = (comp or "").lower()
    table = CRICKET_LEAGUES if sport == "cricket" else FOOTBALL_LEAGUES
    for key, val in table.items():
        if key in c: return val
    return ("🏏 CRICKET 2026" if sport == "cricket" else "⚽ FOOTBALL 2026", "Fancode" if sport == "cricket" else "T Sports")

def bst_str(dt):
    return dt.strftime("%d-%m-%Y-%I:%M 00 %p").lower()

def get_poster_link(t1, t2, sub_name, fmt, sport, start):
    try:
        t1_safe = re.sub(r'[^a-zA-Z0-9]', '_', t1)
        t2_safe = re.sub(r'[^a-zA-Z0-9]', '_', t2)
        date_str = start.strftime("%Y%m%d")
        filename = f"{sport}_{t1_safe}_vs_{t2_safe}_{date_str}.jpg"
        
        sport_type = "Cricket" if sport == "cricket" else "Soccer"
        match_type = fmt if fmt else "MATCH"
        
        create_poster(
            team1=t1,
            team2=t2,
            series_name=sub_name,
            match_type=match_type,
            output_filename=filename,
            sport_type=sport_type
        )
        
        raw_link = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/posters/{filename}"
        return raw_link
    except Exception as e:
        print(f"Poster generation failed: {e}")
        return None

def build_entry(ev, platform_tag):
    start = parse_start(ev)
    if not start: return None
    if not (TODAY_BD <= start.date() <= END_DATE): return None 
        
    t1, t2 = extract_teams(ev)
    if not t1 or not t2: return None

    comp = extract_competition(ev)
    sport = detect_sport(ev, comp)
    sub_name, default_channel = league_meta(sport, comp)
    channel = extract_channel(ev, default_channel)
    fmt = guess_format(comp) if sport == "cricket" else ""

    title = f"{t1} 🆚 {t2} । Watch on {channel}"
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
    for name, url, tag in SOURCES:
        data = fetch_json(url)
        events = _iter_events(data)
        
        for ev in events:
            try:
                entry = build_entry(ev, tag)
            except Exception:
                continue
            if not entry: continue
            key = (entry["Title"], entry["Date & Time"])
            if key in seen: continue
            seen.add(key)
            results.append(entry)

    with open("notifications.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Generated notifications.json with {len(results)} entries.", flush=True)

if __name__ == "__main__":
    main()
