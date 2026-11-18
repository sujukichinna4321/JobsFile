import json, os, re
from datetime import datetime, timedelta
import requests
import pytz

from poster_maker import create_poster

BD = pytz.timezone("Asia/Dhaka")
NOW_BD = datetime.now(BD)
TODAY_BD = NOW_BD.date()
END_DATE = NOW_BD + timedelta(hours=48) # আগামী ৪৮ ঘণ্টা

SONYLIV_API = os.getenv("SonyLiv_API")
FANCEODE_API = os.getenv("FANCEODE_API")
TAPMAD_API = os.getenv("TAPMAD_API")

DEFAULT_IMAGE = "https://raw.githubusercontent.com/samnite2290/img/gh-pages/HOME/HOME-LIVE-EVENT.png"
SUBTITLE_SUFFIX = " | Select 🅻🅸🅅🅴 🆂🅿🅾🆁🆃🆂 Button, Share Our Apps With Your Friends & Family."

GITHUB_USER = "samnite2290"
GITHUB_REPO = "job"
GITHUB_BRANCH = "gh-pages"

# যেসকল ম্যাচ "On" হবে (খুব গুরুত্বপূর্ণ ম্যাচ)
IMPORTANT_LEAGUES = ["world cup", "nations league", "ipl", "bpl", "psl", "premier league", "champions league", "la liga"]

FOOTBALL_LEAGUES = {
    "premier league":   ("🏆 ENGLISH ⚽ PREMIER LEAGUE 2026/27", "TNT 1"),
    "la liga":          ("🏆 SPANISH ⚽ LA LIGA 2026/27",       "SonyLiv"),
    "bundesliga":       ("🏆 GERMAN ⚽ BUNDESLIGA 2026/27",      "SonyLiv"),
    "serie a":          ("🏆 ITALIAN ⚽ SERIE A 2026/27",        "SonyLiv"),
    "ligue 1":          ("🏆 FRENCH ⚽ LIGUE 1 2026/27",         "SonyLiv"),
    "champions league": ("🏆 UEFA ⚽ CHAMPIONS LEAGUE 2026/27",  "SonyLiv"),
    "europa league":    ("🏆 UEFA ⚽ EUROPA LEAGUE 2026/27",     "SonyLiv"),
    "nations league":   ("🏆 UEFA ⚽ NATIONS LEAGUE 2026/27",    "SonyLiv"),
    "fifa world cup":   ("🏆 FIFA ⚽ WORLD CUP 2026",            "T Sports"),
    "friendly":         ("🏆 Friendly Match ⚽ 2026",            "T Sports"),
}

CRICKET_LEAGUES = {
    "t20i":      ("🏏 ICC MEN'S T20I CRICKET 2026",    "Fancode"),
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

POPULAR_KEYWORDS = ["bangladesh", "pakistan", "india", "bpl", "psl", "ipl", "world cup", "asia cup", "champions trophy", "premier league", "la liga", "champions league", "real madrid", "barcelona", "manchester", "liverpool", "arsenal", "chelsea", "bayern", "psg", "juventus", "brazil", "argentina", "kolkata", "mumbai", "chennai", "karachi", "lahore", "dhaka", "comilla", "brisbane", "sydney", "melbourne", "perth", "hobart", "women", "inter", "nations league"]

IGNORE_SPORTS = ["doubles", "atp", "wta", "tur", "turin", "day 1", "day 2", "day 3", "day 4", "race", "practice", "qualifying", "grand prix", "tennis", "golf", "georgia", "spain", "barcelona", "las vegas", "circuit", "round of 16"]

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
    except Exception:
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

def extract_image(ev):
    if "src" in ev and isinstance(ev["src"], str): return ev["src"]
    if "ThumbnailStandard" in ev and isinstance(ev["ThumbnailStandard"], str): return ev["ThumbnailStandard"]
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
    return ""

def league_meta(sport, comp):
    c = (comp or "").lower()
    table = CRICKET_LEAGUES if sport == "cricket" else FOOTBALL_LEAGUES
    for key, val in table.items():
        if key in c: return val
    return ("🏏 CRICKET 2026" if sport == "cricket" else "⚽ FOOTBALL 2026", "Fancode" if sport == "cricket" else "T Sports")

def bst_str(dt):
    return dt.strftime("%d-%m-%Y-%I:%M 00 %p").lower()

def calc_multiple_time(sport, fmt, start_bd):
    """হাফটাইম বা ইনিংস ব্রেক শেষে খেলা শুরুর আনুমানিক সময়"""
    if sport == "football":
        # প্রথমার্ধ ৪৫ মিনিট + হাফটাইম ১৫ মিনিট = ৬০ মিনিট
        return start_bd + timedelta(minutes=60)
    
    if fmt == "T20":
        # ২০ ওভার (প্রায় ৮৫-৯০ মিনিট) + ইনিংস ব্রেক (১৫ মিনিট) = ১০৫ মিনিট
        return start_bd + timedelta(minutes=105)
    if fmt == "T10":
        # ১০ ওভার (প্রায় ৪৫ মিনিট) + ইনিংস ব্রেক (১০ মিনিট) = ৫৫ মিনিট
        return start_bd + timedelta(minutes=55)
    if fmt == "ODI":
        # ৫০ ওভার (প্রায় ২১০ মিনিট) + ইনিংস ব্রেক (৩০ মিনিট) = ২৪০ মিনিট
        return start_bd + timedelta(minutes=240)
    if fmt == "Test":
        # লাঞ্চ বা টি ব্রেক (প্রায় ২ ঘন্টা ৩০ মিনিট পর)
        return start_bd + timedelta(minutes=150)
    
    return start_bd + timedelta(minutes=60)

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
    
    # আগামী ৪৮ ঘণ্টার ফিল্টার
    if not (NOW_BD <= start <= END_DATE): return None 
        
    t1, t2 = extract_teams(ev)
    if not t1 or not t2: return None

    comp = extract_competition(ev)
    if not is_popular_and_valid(t1, t2, comp): return None

    sport = detect_sport(ev, comp)
    sub_name, default_channel = league_meta(sport, comp)
    
    channel = extract_channel(ev, default_channel)
    fmt = guess_format(comp) if sport == "cricket" else ""

    t1_fmt = format_team_name(t1)
    t2_fmt = format_team_name(t2)
    title = f"{t1_fmt} 🆚 {t2_fmt} । Watch on {channel}"
    
    # সাবটাইটেলে সাফিক্স যুক্ত করা
    subtitle = f"{sub_name}{SUBTITLE_SUFFIX}"
    
    # ইমেজ লিংক
    img_link = extract_image(ev) or DEFAULT_IMAGE
    poster_url = get_poster_link(t1, t2, sub_name, fmt, sport, start)
    image = poster_url if poster_url else img_link
    
    # ম্যাচ শুরুর ৫ মিনিট আগে
    date_time = bst_str(start - timedelta(minutes=5))

    # মাল্টিপল টাইম লজিক
    is_important = any(k in comp.lower() for k in IMPORTANT_LEAGUES)
    multiple_on = "On" if is_important else "Off"
    
    multiple_time = ""
    if is_important:
        mt_time = calc_multiple_time(sport, fmt, start)
        multiple_time = f"({bst_str(mt_time)})"

    return {
        "Date & Time": date_time,
        "multipleTimeRun": multiple_on,
        "multipleTime": multiple_time,
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
        if not url: continue
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

    # তারিখ অনুযায়ী সাজানো
    results.sort(key=lambda x: datetime.strptime(x["Date & Time"], "%d-%m-%Y-%I:%M 00 %p"))

    # ১৫০ লাইনের গ্যাপ তৈরি করা
    gap = "\n" * 150
    json_output = json.dumps(results, ensure_ascii=False, indent=2)
    
    # ফাইলে লেখা (গ্যাপসহ)
    with open("notifications.json", "w", encoding="utf-8") as f:
        f.write(gap + json_output)
        
    print(f"Generated notifications.json with {len(results)} entries.", flush=True)

if __name__ == "__main__":
    main()
