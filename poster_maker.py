import json
import os
import re
import urllib.parse
import requests
import cairosvg
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# --- কনফিগারেশন (রেজুলেশন হালকা করা হয়েছে) ---
POSTER_WIDTH = 1200
POSTER_HEIGHT = 600
FONT_BOLD_PATH = "assets/fonts/Oswald-Bold.ttf"
FONT_REGULAR_PATH = "assets/fonts/Oswald-Regular.ttf"
OUTPUT_DIR = "posters"
LOGO_BASE_DIR = "assets/Logo"
COUNTRY_FLAG_DIR = "assets/Logo-Country" # নতুন ফ্ল্যাগ ফোল্ডার

os.makedirs(OUTPUT_DIR, exist_ok=True)

IGNORE_WORDS = ["women", "w", "fc", "afc", "cf", "sc", "club", "u19", "u21", "u23", "vs", "match", "round", "of", "day", "practice"]

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
                if team_clean == file_name_clean or team_clean in file_name_clean or file_name_clean in team_clean:
                    return os.path.join(root, file)
                if team_clean[:4] == file_name_clean[:4]:
                    best_match = os.path.join(root, file)
    return best_match

def get_team_logo(team_name):
    # ১. আগে ক্লাব লোগো (PNG) খুঁজবে
    path = find_logo_path(team_name)
    if path and os.path.exists(path):
        return Image.open(path).convert("RGBA")
    
    # ২. না পেলে দেশের ফ্ল্যাগ (SVG) খোঁজার চেষ্টা করবে
    # দলের নামের প্রথম ২ অক্ষর বা পুরো নাম দিয়ে দেশ খোঁজা হবে
    if os.path.exists(COUNTRY_FLAG_DIR):
        for root, dirs, files in os.walk(COUNTRY_FLAG_DIR):
            for file in files:
                if file.lower().endswith((".svg", ".png")):
                    # ধরুন ফাইলের নাম af.svg, ax.svg
                    file_name = file.lower().replace(".svg", "").replace(".png", "")
                    # যদি দলের নামের সাথে ফ্ল্যাগের নাম মিলে যায়
                    if file_name in team_name.lower() or file_name == team_name.lower():
                        flag_path = os.path.join(root, file)
                        if file.lower().endswith(".svg"):
                            # SVG ফাইলকে PNG-তে কনভার্ট করা
                            png_data = cairosvg.svg2png(url=flag_path, output_width=300, output_height=300)
                            return Image.open(BytesIO(png_data)).convert("RGBA")
                        else:
                            return Image.open(flag_path).convert("RGBA")

    # ৩. কিছুই না পেলে ডিফল্ট প্লেসহোল্ডার
    img = Image.new("RGBA", (200, 200), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, 200, 200), fill=(255, 255, 255, 50))
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
    if not os.path.exists(bg_path):
        bg_path = "assets/bg_main.png"
        
    if os.path.exists(bg_path):
        canvas = Image.open(bg_path).convert("RGBA")
        canvas = canvas.resize((POSTER_WIDTH, POSTER_HEIGHT))
        enhancer = ImageEnhance.Brightness(canvas)
        canvas = enhancer.enhance(0.5)
    else:
        canvas = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (20, 20, 30, 255))

    draw = ImageDraw.Draw(canvas)

    try:
        font_series = ImageFont.truetype(FONT_BOLD_PATH, 35) # ফন্ট একটু ছোট করা হলো
        font_match = ImageFont.truetype(FONT_BOLD_PATH, 30)
        font_v = ImageFont.truetype(FONT_BOLD_PATH, 70)
    except:
        font_series = font_match = font_v = ImageFont.load_default()

    # ১. সিরিজের নাম (ইমোজি বাদ দেওয়া হবে)
    # regex দিয়ে ইমোজি রিমুভ করা হচ্ছে
    series_clean = re.sub(r'[^\w\s\-/\.]', '', series_name).strip().upper()
    
    font_series_fit = get_font_size_to_fit(series_clean, FONT_BOLD_PATH, 1000, 40)
    bbox = draw.textbbox((0, 0), series_clean, font=font_series_fit)
    text_w = bbox[2] - bbox[0]
    draw.text(((POSTER_WIDTH - text_w) / 2 + 2, 32), series_clean, font=font_series_fit, fill="black")
    draw.text(((POSTER_WIDTH - text_w) / 2, 30), series_clean, font=font_series_fit, fill="white")

    # ২. লোগো বসানো (লোগো সাইজ বড় করা হলো ৩২০ পিক্সেল)
    logo_size = 320
    logo1 = get_team_logo(team1).resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    logo2 = get_team_logo(team2).resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    canvas.paste(logo1, (POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 160), logo1)
    canvas.paste(logo2, (3*POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 160), logo2)

    draw = ImageDraw.Draw(canvas)

    # ৩. মাঝখানে "V"
    bbox_v = draw.textbbox((0, 0), "V", font=font_v)
    v_w = bbox_v[2] - bbox_v[0]
    draw.text(((POSTER_WIDTH - v_w) / 2, POSTER_HEIGHT//2 - 60), "V", font=font_v, fill="white")

    # ৪. দলের নাম (নিচে)
    team_text = f"{team1.upper()} vs {team2.upper()}"
    font_teams_fit = get_font_size_to_fit(team_text, FONT_BOLD_PATH, 1100, 65)
    bbox_t = draw.textbbox((0, 0), team_text, font=font_teams_fit)
    t_w = bbox_t[2] - bbox_t[0]
    
    text_y = POSTER_HEIGHT - 140
    draw.text(((POSTER_WIDTH - t_w) / 2 + 2, text_y + 2), team_text, font=font_teams_fit, fill="black")
    draw.text(((POSTER_WIDTH - t_w) / 2, text_y), team_text, font=font_teams_fit, fill="white")

    # ৫. ম্যাচের ধরন (T20, MATCH ইত্যাদি)
    if match_type:
        m_text = match_type.upper()
        bbox_m = draw.textbbox((0, 0), m_text, font=font_match)
        m_w = bbox_m[2] - bbox_m[0]
        draw.text(((POSTER_WIDTH - m_w) / 2, text_y + 70), m_text, font=font_match, fill="#FFD700")

    output_path = os.path.join(OUTPUT_DIR, output_filename)
    canvas.convert("RGB").save(output_path, quality=90) # কোয়ালিটি একটু কমানো হলো
    print(f"Poster saved at {output_path}\n")
    return output_path
