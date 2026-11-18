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
FONT_BOLD_PATH = "assets/fonts/Oswald-Bold.ttf"
FONT_REGULAR_PATH = "assets/fonts/Oswald-Regular.ttf"
TEAM_COLORS_FILE = "assets/team_colors.json"
OUTPUT_DIR = "posters"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("assets/logos", exist_ok=True)

API_FOOTBALL_KEY = os.getenv("APIFOOTBALL_KEY", "")
CRICKET_DATA_KEY = os.getenv("CRICKETDATA_KEY", "")

def load_team_colors():
    if os.path.exists(TEAM_COLORS_FILE):
        with open(TEAM_COLORS_FILE, 'r') as f:
            return json.load(f)
    return {}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def search_logo_apifootball(team_name):
    if not API_FOOTBALL_KEY: return None
    try:
        url = f"https://v3.football.api-sports.io/teams?search={urllib.parse.quote(team_name)}"
        headers = {'x-apisports-key': API_FOOTBALL_KEY}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if data.get("response"):
            return data["response"][0]["team"]["logo"]
    except Exception as e:
        pass
    return None

def search_logo_thesportsdb(team_name, sport="Soccer"):
    try:
        url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={urllib.parse.quote(team_name)}"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data and data.get("teams"):
            for team in data["teams"]:
                # কেস-সেনসিটিভ এরর ঠিক করা হয়েছে (lowercase করা হয়েছে)
                if team.get("strSport", "").lower() == sport.lower():
                    return team.get("strBadge") or team.get("strTeamBadge")
    except Exception as e:
        pass
    return None

def download_logo(logo_url, save_path):
    try:
        response = requests.get(logo_url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        img.save(save_path, "PNG")
        return True
    except Exception:
        return False

def get_logo(team_name, sport="Soccer"):
    safe_name = team_name.lower().replace(" ", "_") + ".png"
    local_path = os.path.join("assets/logos", safe_name)
    
    if os.path.exists(local_path):
        return Image.open(local_path).convert("RGBA")
    
    logo_url = None
    if sport.lower() == "soccer":
        logo_url = search_logo_apifootball(team_name)
        
    if not logo_url:
        logo_url = search_logo_thesportsdb(team_name, sport)
    
    if logo_url:
        if download_logo(logo_url, local_path):
            time.sleep(0.5)
            return Image.open(local_path).convert("RGBA")
    
    print(f"Warning: No logo found for {team_name}")
    return None

def create_poster(team1, team2, series_name, match_type, output_filename, sport_type="Soccer"):
    print(f"Generating poster for {team1} vs {team2}...")
    
    # ১. স্পোর্টস অনুযায়ী ব্যাকগ্রাউন্ড সিলেক্ট করা
    bg_path = "assets/Football-BG.png" if sport_type.lower() == "soccer" else "assets/Cricket-BG.png"
    
    canvas = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (0, 0, 0, 255))
    
    if os.path.exists(bg_path):
        bg = Image.open(bg_path).convert("RGBA")
        bg = bg.resize((POSTER_WIDTH, POSTER_HEIGHT))
        
        # ব্যাকগ্রাউন্ড ৫০% ডার্ক করা (যাতে লোগো ও টেক্সট ফুটে ওঠে)
        alpha = bg.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(0.5) 
        bg.putalpha(alpha)
        canvas.paste(bg, (0, 0), bg)
    else:
        print(f"Warning: Background not found at {bg_path}")

    # ২. দলের কালার ওভারলে (হালকা করে)
    colors = load_team_colors()
    c1_rgb = hex_to_rgb(colors.get(team1.lower(), "#1A237E"))
    c2_rgb = hex_to_rgb(colors.get(team2.lower(), "#B71C1C"))
    
    overlay = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (0,0,0,0))
    draw_overlay = ImageDraw.Draw(overlay)
    # ওভারলে অপাসিটি ১২০ করা হয়েছে যাতে ব্যাকগ্রাউন্ড ঢেকে না যায়
    draw_overlay.polygon([(0,0), (POSTER_WIDTH//2, 0), (POSTER_WIDTH//2 - 200, POSTER_HEIGHT), (0, POSTER_HEIGHT)], fill=c1_rgb + (120,))
    draw_overlay.polygon([(POSTER_WIDTH//2, 0), (POSTER_WIDTH, 0), (POSTER_WIDTH, POSTER_HEIGHT), (POSTER_WIDTH//2 + 200, POSTER_HEIGHT)], fill=c2_rgb + (120,))
    
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # ৩. ফন্ট সাইজ সেট করা
    try:
        font_series = ImageFont.truetype(FONT_BOLD_PATH, 45)
        font_teams = ImageFont.truetype(FONT_BOLD_PATH, 75) # লেখা ছোট করা হয়েছে
        font_match = ImageFont.truetype(FONT_BOLD_PATH, 40)
    except:
        font_series = font_teams = font_match = ImageFont.load_default()

    # ৪. সিরিজের নাম (উপরে)
    bbox = draw.textbbox((0, 0), series_name, font=font_series)
    text_w = bbox[2] - bbox[0]
    draw.text(((POSTER_WIDTH - text_w) / 2 + 2, 42), series_name, font=font_series, fill="black")
    draw.text(((POSTER_WIDTH - text_w) / 2, 40), series_name, font=font_series, fill="white")

    # ৫. লোগো বসানো (মাঝখানে)
    logo1 = get_logo(team1, sport_type)
    logo2 = get_logo(team2, sport_type)
    
    logo_size = 250
    if logo1:
        logo1 = logo1.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        canvas.paste(logo1, (POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 130), logo1)
    if logo2:
        logo2 = logo2.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        canvas.paste(logo2, (3*POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 130), logo2)

    draw = ImageDraw.Draw(canvas)

    # ৬. মাঝখানে "V"
    bbox_v = draw.textbbox((0, 0), "V", font=font_teams)
    v_w = bbox_v[2] - bbox_v[0]
    draw.text(((POSTER_WIDTH - v_w) / 2, POSTER_HEIGHT//2 - 100), "V", font=font_teams, fill="white")

    # ৭. দলের নাম (নিচে)
    team_text = f"{team1.upper()} vs {team2.upper()}"
    bbox_t = draw.textbbox((0, 0), team_text, font=font_teams)
    t_w = bbox_t[2] - bbox_t[0]
    
    # টেক্সট পজিশন নিচে নামানো হয়েছে যাতে ম্যাচের লেখার সাথে ওভারল্যাপ না হয়
    text_y = POSTER_HEIGHT - 200
    draw.text(((POSTER_WIDTH - t_w) / 2 + 2, text_y + 2), team_text, font=font_teams, fill="black")
    draw.text(((POSTER_WIDTH - t_w) / 2, text_y), team_text, font=font_teams, fill="white")

    # ৮. ম্যাচের ধরন
    if match_type:
        bbox_m = draw.textbbox((0, 0), match_type, font=font_match)
        m_w = bbox_m[2] - bbox_m[0]
        # দলের নামের ঠিক নিচে বসানো হয়েছে
        draw.text(((POSTER_WIDTH - m_w) / 2, text_y + 90), match_type, font=font_match, fill="#FFD700")

    # ৯. সেভ করা (Watch On বাদ দেওয়া হয়েছে)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    canvas.convert("RGB").save(output_path, quality=95) 
    print(f"Poster saved at {output_path}\n")
    return output_path
