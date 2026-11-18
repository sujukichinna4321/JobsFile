import json
import os
import time
import urllib.parse
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# --- কনফিগারেশন ---
POSTER_WIDTH = 1500
POSTER_HEIGHT = 750
BG_IMAGE_PATH = "assets/bg_main.png"  # আপনার ব্যাকগ্রাউন্ডের নাম
FONT_BOLD_PATH = "assets/fonts/Oswald-Bold.ttf" # আপনার বোল্ড ফন্টের নাম
FONT_REGULAR_PATH = "assets/fonts/Oswald-Regular.ttf" # আপনার রেগুলার ফন্টের নাম
TEAM_COLORS_FILE = "assets/team_colors.json"
OUTPUT_DIR = "posters"

# নিশ্চিত করা যে আউটপুট ফোল্ডার এবং লোগো ফোল্ডার আছে
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("assets/logos", exist_ok=True)

# এনভায়রনমেন্ট ভেরিয়েবল থেকে API Key নেওয়া
API_FOOTBALL_KEY = os.getenv("APIFOOTBALL_KEY", "")
CRICKET_DATA_KEY = os.getenv("CRICKETDATA_KEY", "")

def load_team_colors():
    """team_colors.json ফাইল থেকে কালার লোড করে"""
    if os.path.exists(TEAM_COLORS_FILE):
        with open(TEAM_COLORS_FILE, 'r') as f:
            return json.load(f)
    return {}

def hex_to_rgb(hex_color):
    """Hex কালারকে RGB-তে রূপান্তর করে"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def search_logo_apifootball(team_name):
    """API-Football থেকে লোগো খোঁজে"""
    if not API_FOOTBALL_KEY:
        print("API-Football key not found.")
        return None
    try:
        url = f"https://v3.football.api-sports.io/teams?search={urllib.parse.quote(team_name)}"
        headers = {'x-apisports-key': API_FOOTBALL_KEY}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("response"):
            return data["response"][0]["team"]["logo"]
    except Exception as e:
        print(f"API-Football search failed for {team_name}: {e}")
    return None

def search_logo_cricketdata(team_name):
    """CricketData API থেকে লোগো খোঁজে (যদি থাকে)"""
    if not CRICKET_DATA_KEY:
        return None
    # দ্রষ্টব্য: CricketData.org সাধারণত সরাসরি লোগো দেয় না, তবে ভবিষ্যতে কাজে লাগতে পারে
    return None

def search_logo_thesportsdb(team_name, sport="Soccer"):
    """TheSportsDB API থেকে লোগো খোঁজে (সর্বজনীন ব্যাকআপ)"""
    try:
        url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={urllib.parse.quote(team_name)}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get("teams"):
            for team in data["teams"]:
                if team.get("strSport", "").lower() == sport.lower():
                    # নতুন ফিল্ড 'strBadge' চেক করা হচ্ছে, না পেলে পুরানো 'strTeamBadge'
                    logo_url = team.get("strBadge") or team.get("strTeamBadge") or team.get("strTeamLogo")
                    if logo_url:
                        return logo_url
    except Exception as e:
        print(f"TheSportsDB search failed for {team_name}: {e}")
    return None

def download_logo(logo_url, save_path):
    """URL থেকে লোগো ডাউনলোড করে নির্দিষ্ট পাথে সংরক্ষণ করে"""
    try:
        response = requests.get(logo_url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        img.save(save_path, "PNG")
        return True
    except Exception as e:
        print(f"Download failed for {save_path}: {e}")
        return False

def get_logo(team_name, sport="Soccer"):
    """
    প্রথমে লোকাল ফোল্ডার থেকে লোগো খোঁজে, না পেলে API থেকে ডাউনলোড করে
    """
    safe_name = team_name.lower().replace(" ", "_") + ".png"
    local_path = os.path.join("assets/logos", safe_name)
    
    # ১. লোকাল ফাইলে থাকলে সেটাই ব্যবহার করবে
    if os.path.exists(local_path):
        return Image.open(local_path).convert("RGBA")
    
    # ২. API থেকে খোঁজা শুরু
    logo_url = None
    print(f"Logo not found locally, searching API for: {team_name} ({sport})")
    
    if sport.lower() == "soccer" and API_FOOTBALL_KEY:
        logo_url = search_logo_apifootball(team_name)
        
    if not logo_url and sport.lower() == "cricket" and CRICKET_DATA_KEY:
        logo_url = search_logo_cricketdata(team_name)
        
    if not logo_url:
        # ব্যাকআপ হিসেবে TheSportsDB
        logo_url = search_logo_thesportsdb(team_name, sport)
    
    # ৩. ডাউনলোড এবং রিটার্ন
    if logo_url:
        if download_logo(logo_url, local_path):
            time.sleep(1) # API রেট লিমিট এড়াতে
            return Image.open(local_path).convert("RGBA")
    
    print(f"Warning: No logo found for {team_name}")
    return None

def create_poster(team1, team2, series_name, match_type, broadcaster, output_filename, sport_type="Soccer"):
    print(f"Generating poster for {team1} vs {team2}...")
    
    # ১. বেস ক্যানভাস তৈরি
    canvas = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (0, 0, 0, 255))
    
    # ২. ব্যাকগ্রাউন্ড লোড এবং ৫০% অফাসিটি করা
    if os.path.exists(BG_IMAGE_PATH):
        bg = Image.open(BG_IMAGE_PATH).convert("RGBA")
        bg = bg.resize((POSTER_WIDTH, POSTER_HEIGHT))
        
        # অফাসিটি ৫০% করা
        alpha = bg.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(0.5) 
        bg.putalpha(alpha)
        
        # কালো ব্যাকগ্রাউন্ডে ব্লেন্ড করা
        canvas.paste(bg, (0, 0), bg)
    else:
        print("Warning: Background image not found. Using black canvas.")

    # ৩. দলের কালার ওভারলে (বাম এবং ডান দিকে)
    colors = load_team_colors()
    c1_hex = colors.get(team1.lower(), "#1A237E") 
    c2_hex = colors.get(team2.lower(), "#B71C1C")
    
    c1_rgb = hex_to_rgb(c1_hex)
    c2_rgb = hex_to_rgb(c2_hex)
    
    overlay = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (0,0,0,0))
    draw_overlay = ImageDraw.Draw(overlay)
    
    # বাম দিকের কালার (টিম ১)
    draw_overlay.polygon([(0,0), (POSTER_WIDTH//2, 0), (POSTER_WIDTH//2 - 150, POSTER_HEIGHT), (0, POSTER_HEIGHT)], fill=c1_rgb + (140,))
    # ডান দিকের কালার (টিম ২)
    draw_overlay.polygon([(POSTER_WIDTH//2, 0), (POSTER_WIDTH, 0), (POSTER_WIDTH, POSTER_HEIGHT), (POSTER_WIDTH//2 + 150, POSTER_HEIGHT)], fill=c2_rgb + (140,))
    
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # ৪. ফন্ট লোড করা
    try:
        font_series = ImageFont.truetype(FONT_BOLD_PATH, 50)
        font_teams = ImageFont.truetype(FONT_BOLD_PATH, 90)
        font_match = ImageFont.truetype(FONT_REGULAR_PATH, 45)
        font_small = ImageFont.truetype(FONT_REGULAR_PATH, 35)
    except Exception as e:
        print(f"Font loading error: {e}. Using default font.")
        font_series = font_teams = font_match = font_small = ImageFont.load_default()

    # ৫. সিরিজের নাম (উপরে সেন্টারে)
    bbox = draw.textbbox((0, 0), series_name, font=font_series)
    text_w = bbox[2] - bbox[0]
    draw.text(((POSTER_WIDTH - text_w) / 2 + 2, 52), series_name, font=font_series, fill="black")
    draw.text(((POSTER_WIDTH - text_w) / 2, 50), series_name, font=font_series, fill="white")

    # ৬. লোগো বসানো
    logo1 = get_logo(team1, sport_type)
    logo2 = get_logo(team2, sport_type)
    
    logo_size = 300
    # বাম দিকের লোগো
    if logo1:
        logo1 = logo1.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        canvas.paste(logo1, (POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 120), logo1)
    # ডান দিকের লোগো
    if logo2:
        logo2 = logo2.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        canvas.paste(logo2, (3*POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 120), logo2)

    # ৭. মাঝখানে "V" চিহ্ন
    draw = ImageDraw.Draw(canvas)
    bbox_v = draw.textbbox((0, 0), "V", font=font_teams)
    v_w = bbox_v[2] - bbox_v[0]
    draw.text(((POSTER_WIDTH - v_w) / 2, POSTER_HEIGHT//2 - 100), "V", font=font_teams, fill="white")

    # ৮. দলের নাম (লোগোর নিচে)
    team_text = f"{team1.upper()} vs {team2.upper()}"
    bbox_t = draw.textbbox((0, 0), team_text, font=font_teams)
    t_w = bbox_t[2] - bbox_t[0]
    draw.text(((POSTER_WIDTH - t_w) / 2 + 2, POSTER_HEIGHT//2 + 202), team_text, font=font_teams, fill="black")
    draw.text(((POSTER_WIDTH - t_w) / 2, POSTER_HEIGHT//2 + 200), team_text, font=font_teams, fill="white")

    # ৯. ম্যাচের ধরন (নিচের দিকে)
    bbox_m = draw.textbbox((0, 0), match_type, font=font_match)
    m_w = bbox_m[2] - bbox_m[0]
    draw.text(((POSTER_WIDTH - m_w) / 2, POSTER_HEIGHT - 100), match_type, font=font_match, fill="gold")

    # ১০. ব্রডকাস্টার টেক্সট (নিচে ডান কোণায়)
    draw.text((POSTER_WIDTH - 400, POSTER_HEIGHT - 70), f"Watch on {broadcaster}", font=font_small, fill="white")

    # ১১. ফাইনাল ছবি সেভ করা
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    canvas.convert("RGB").save(output_path, quality=95) 
    print(f"Poster saved at {output_path}\n")
    return output_path

# --- টেস্ট করার জন্য ---
if __name__ == "__main__":
    create_poster(
        team1="Pakistan",
        team2="Sri Lanka",
        series_name="Sri Lanka Tour of Pakistan 2026",
        match_type="2ND TEST",
        broadcaster="Willow",
        output_filename="test_pak_vs_sl.jpg",
        sport_type="Cricket"
    )
