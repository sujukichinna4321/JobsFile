import json
import os
import re
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# --- কনফিগারেশন ---
POSTER_WIDTH = 1200
POSTER_HEIGHT = 600
FONT_BOLD_PATH = "assets/fonts/Oswald-Bold.ttf"
FONT_REGULAR_PATH = "assets/fonts/Oswald-Regular.ttf"
OUTPUT_DIR = "posters"
LOGO_BASE_DIR = "assets/Logo"
DEFAULT_LOGO_PATH = "assets/Logo.png" 

os.makedirs(OUTPUT_DIR, exist_ok=True)

IGNORE_WORDS = ["women", "w", "fc", "afc", "cf", "sc", "club", "u19", "u21", "u23", "vs", "match", "round", "of", "day", "practice", "men", "milan", "city", "united"]

def clean_name(name):
    name = name.lower()
    for word in IGNORE_WORDS:
        name = re.sub(r'\b' + re.escape(word) + r'\b', '', name)
    return re.sub(r'[^a-z0-9]', '', name).strip()

def find_logo_path(team_name):
    team_clean = clean_name(team_name)
    if not team_clean: return None
    best_match = None
    
    for root, dirs, files in os.walk(LOGO_BASE_DIR):
        for file in files:
            if file.lower().endswith(".png"):
                file_name_clean = clean_name(file.lower().replace(".png", ""))
                if team_clean == file_name_clean:
                    return os.path.join(root, file)
                if team_clean in file_name_clean or file_name_clean in team_clean:
                    best_match = os.path.join(root, file)
    return best_match

def get_team_logo(team_name):
    path = find_logo_path(team_name)
    if path and os.path.exists(path):
        return Image.open(path).convert("RGBA")
    if os.path.exists(DEFAULT_LOGO_PATH):
        return Image.open(DEFAULT_LOGO_PATH).convert("RGBA")
    img = Image.new("RGBA", (300, 300), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, 300, 300), fill=(255, 255, 255, 50))
    return img

def get_font_size_to_fit(text, font_path, max_width, max_size=75):
    size = max_size
    while size > 20:
        try:
            font = ImageFont.truetype(font_path, size)
        except:
            return ImageFont.load_default()
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        if text_w <= max_width:
            return font
        size -= 5
    return ImageFont.truetype(font_path, 20)

def create_poster(team1, team2, series_name, match_type, output_filename, sport_type="Soccer"):
    print(f"Generating poster for {team1} vs {team2}...")
    
    bg_path = "assets/Football-BG.png" if sport_type.lower() == "soccer" else "assets/Cricket-BG.png"
    if not os.path.exists(bg_path): bg_path = "assets/bg_main.png"
        
    if os.path.exists(bg_path):
        canvas = Image.open(bg_path).convert("RGBA")
        canvas = canvas.resize((POSTER_WIDTH, POSTER_HEIGHT))
        canvas = ImageEnhance.Brightness(canvas).enhance(0.5)
    else:
        canvas = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (20, 20, 30, 255))

    draw = ImageDraw.Draw(canvas)

    try:
        font_match = ImageFont.truetype(FONT_BOLD_PATH, 30)
        font_vs = ImageFont.truetype(FONT_BOLD_PATH, 90) # VS ফন্ট বড় করা হলো
        font_powered = ImageFont.truetype(FONT_REGULAR_PATH, 25) # Powered by ফন্ট
    except:
        font_match = font_vs = font_powered = ImageFont.load_default()

    # ১. সিরিজের নাম
    series_clean = re.sub(r'[^\w\s\-/\.]', '', series_name).strip().upper()
    font_series_fit = get_font_size_to_fit(series_clean, FONT_BOLD_PATH, 1000, 40)
    bbox = draw.textbbox((0, 0), series_clean, font=font_series_fit)
    text_w = bbox[2] - bbox[0]
    draw.text(((POSTER_WIDTH - text_w) / 2 + 2, 22), series_clean, font=font_series_fit, fill="black")
    draw.text(((POSTER_WIDTH - text_w) / 2, 20), series_clean, font=font_series_fit, fill="white")

    # ২. Powered by SAWARID APPS (নতুন যুক্ত হলো)
    powered_text = "Powered by: SAWARID APPS"
    bbox_p = draw.textbbox((0, 0), powered_text, font=font_powered)
    p_w = bbox_p[2] - bbox_p[0]
    draw.text(((POSTER_WIDTH - p_w) / 2, 75), powered_text, font=font_powered, fill="#CCCCCC")

    # ৩. লোগো বসানো
    logo_size = 300
    logo1 = get_team_logo(team1).resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    logo2 = get_team_logo(team2).resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    canvas.paste(logo1, (POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 130), logo1)
    canvas.paste(logo2, (3*POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 130), logo2)

    draw = ImageDraw.Draw(canvas)

    # ৪. মাঝখানে VS (বড় করে)
    bbox_vs = draw.textbbox((0, 0), "VS", font=font_vs)
    vs_w = bbox_vs[2] - bbox_vs[0]
    draw.text(((POSTER_WIDTH - vs_w) / 2, POSTER_HEIGHT//2 - 60), "VS", font=font_vs, fill="white")

    # ৫. দলের নাম
    team_text = f"{team1.upper()} vs {team2.upper()}"
    font_teams_fit = get_font_size_to_fit(team_text, FONT_BOLD_PATH, 1100, 65)
    bbox_t = draw.textbbox((0, 0), team_text, font=font_teams_fit)
    t_w = bbox_t[2] - bbox_t[0]
    
    text_y = POSTER_HEIGHT - 130
    draw.text(((POSTER_WIDTH - t_w) / 2 + 2, text_y + 2), team_text, font=font_teams_fit, fill="black")
    draw.text(((POSTER_WIDTH - t_w) / 2, text_y), team_text, font=font_teams_fit, fill="white")

    # ৬. ম্যাচের ধরন (যদি থাকে)
    if match_type:
        m_text = match_type.upper()
        bbox_m = draw.textbbox((0, 0), m_text, font=font_match)
        m_w = bbox_m[2] - bbox_m[0]
        draw.text(((POSTER_WIDTH - m_w) / 2, text_y + 70), m_text, font=font_match, fill="#FFD700")

    output_path = os.path.join(OUTPUT_DIR, output_filename)
    canvas.convert("RGB").save(output_path, quality=90)
    return output_path
