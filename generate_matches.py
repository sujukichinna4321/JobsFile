import json, os, re, sys
from datetime import datetime, timedelta, timezone
import requests
import pytz

# poster_maker থেকে ফাংশন ইমপোর্ট করা
try:
    from assets.poster_maker import create_poster
except ImportError:
    print("Warning: poster_maker.py not found in assets folder. Posters will not be generated.")

# বাংলাদেশ টাইমজোন
BD = pytz.timezone("Asia/Dhaka")
NOW_BD = datetime.now(BD)
TODAY_BD = NOW_BD.date()
END_DATE = TODAY_BD + timedelta(days=2) # আগামী ৩ দিন

DEFAULT_IMAGE = os.environ.get("DEFAULT_IMAGE", "https://i.postimg.cc/2jPs7rBr/HOME-LIVE-EVENT.png")
SUBTITLE_SUFFIX = os.environ.get("SUBTITLE_SUFFIX", " | Select 🅻🅸🅅🅴 🆂🅿🅾🆁🆃🆂 Button, Share Our Apps With Your Friends & Family.")

# গিটহাব রিপোজিটরি কনফিগারেশন (লিংক তৈরির জন্য)
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
    except Exception as e:
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

def extract_image(ev):
    if "src" in ev and isinstance(ev["src"], str): return ev["src"]
    if "ThumbnailStandard" in ev and isinstance(ev["ThumbnailStandard"], str): return ev["ThumbnailStandard"]
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
    return "T20"

def league_meta(sport, comp):
    c = (comp or "").lower()
    table = CRICKET_LEAGUES if sport == "cricket" else FOOTBALL_LEAGUES
    for key, val in table.items():
        if key in c: return val
    return ("🏏 CRICKET 2026" if sport == "cricket" else "⚽ FOOTBALL 2026", "Fancode" if sport == "cricket" else "T Sports")

def bst_str(dt):
    return dt.strftime("%d-%m-%Y-%I:%M 00 %p").lower()

def compute_multiple(sport, fmt, start_bd):
    if sport == "football": return start_bd + timedelta(minutes=60)
    if fmt == "T20": return start_bd + timedelta(minutes=105)
    if fmt == "T10": return start_bd + timedelta(minutes=55)
    if fmt == "ODI": return start_bd + timedelta(minutes=225)
    if fmt == "Test": return start_bd + timedelta(minutes=150)
    return None

def get_poster_link(t1, t2, sub_name, fmt, channel, sport, start):
    """পোস্টার তৈরি করে তার গিটহাব লিংক রিটার্ন করে"""
    try:
        # ফাইলের নাম তৈরি (স্পেস থাকলে আন্ডারস্কোর)
        t1_safe = t1.replace(" ", "_")
        t2_safe = t2.replace(" ", "_")
        date_str = start.strftime("%Y%m%d")
        filename = f"{sport}_{t1_safe}_vs_{t2_safe}_{date_str}.jpg"
        
        # পোস্টার মেকার কল করা
        sport_type = "Cricket" if sport == "cricket" else "Soccer"
        match_type = fmt if fmt else "MATCH"
        
        create_poster(
            team1=t1,
            team2=t2,
            series_name=sub_name,
            match_type=match_type,
            broadcaster=channel,
            output_filename=filename,
            sport_type=sport_type
        )
        
        # গিটহাব raw লিংক তৈরি
        raw_link = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/posters/{filename}"
        return raw_link
    except Exception as e:
        print(f"Poster generation failed for {t1} vs {t2}: {e}")
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
    
    # --- পোস্টার তৈরি এবং ইমেজ লিংক সেট করা ---
    poster_url = get_poster_link(t1, t2, sub_name, fmt, channel, sport, start)
    image = poster_url if poster_url else (extract_image(ev) or DEFAULT_IMAGE)
    
    date_time = bst_str(start - timedelta(minutes=5))

    is_premium = platform_tag in ["Fancode", "SonyLiv", "Tapmad"]
    is_big_match = any(x in comp.lower() for x in ["world cup", "ipl", "bbl", "psl", "test", "odi", "champions league", "premier league", "nations league"])
    
    multiple_on = is_premium and is_big_match
    multiple_time = ""
    
    if multiple_on:
        mt = compute_multiple(sport, fmt, start)
        if mt:
            multiple_time = f"({bst_str(mt)})"
        else:
            multiple_on = False

    return {
        "Date & Time": date_time,
        "multipleTimeRun": "On" if multiple_on else "Off",
        "multipleTime": multiple_time,
        "Title": title,
        "Subtitle": subtitle,
        "Image": image,
    }

def _sort_key(x):
    s = x["Date & Time"]
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})-(\d{2}):(\d{2})\s+00\s+([ap]m)", s)
    if not m: return datetime.max
    dd, mm, yy, hh, mi, ap = m.groups()
    hh = int(hh) % 12
    if ap == "pm": hh += 12
    return datetime(int(yy), int(mm), int(dd), hh, int(mi))

def main():
    results, seen = [], set()
    for name, url, tag in SOURCES:
        data = fetch_json(url)
        events = _iter_events(data)
        
        for ev in events:
            try:
                entry = build_entry(ev, tag)
            except Exception as e:
                print(f"Error processing event: {e}")
                continue
            if not entry: continue
            key = (entry["Title"], entry["Date & Time"])
            if key in seen: continue
            seen.add(key)
            results.append(entry)

    results.sort(key=_sort_key)

    with open("notifications.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Generated notifications.json with {len(results)} entries.", flush=True)

if __name__ == "__main__":
    main()
