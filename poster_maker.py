import json
import os
import re
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

POSTER_WIDTH = 1500
POSTER_HEIGHT = 750
FONT_BOLD_PATH = "assets/fonts/Oswald-Bold.ttf"
FONT_REGULAR_PATH = "assets/fonts/Oswald-Regular.ttf"
OUTPUT_DIR = "posters"
LOGO_BASE_DIR = "assets/Logo"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# যে শব্দগুলো বাদ দিয়ে দলের আসল নাম খোঁজা হবে
IGNORE_WORDS = ["women", "w", "fc", "afc", "cf", "sc", "club", "u19", "u21", "u23", "vs", "match", "round", "of", "16", "day", "1", "practice"]

def clean_name(name):
    """নাম থেকে অপ্রয়োজনীয় শব্দ বাদ দেয়"""
    name = name.lower()
    for word in IGNORE_WORDS:
        name = re.sub(r'\b' + re.escape(word) + r'\b', '', name)
    # স্পেস এবং ড্যাশ পরিষ্কার করা
    return re.sub(r'[^a-z0-9]', '', name).strip()

def find_logo_path(team_name):
    team_clean = clean_name(team_name)
    if not team_clean: return None
    
    best_match = None
    
    # পুরো ফোল্ডারে খোঁজা
    for root, dirs, files in os.walk(LOGO_BASE_DIR):
        for file in files:
            if file.lower().endswith(".png"):
                file_name_clean = clean_name(file.lower().replace(".png", ""))
                
                # যদি নাম হুবহু মিলে যায় বা একটার ভেতর আরেকটা থাকে
                if team_clean == file_name_clean or team_clean in file_name_clean or file_name_clean in team_clean:
                    return os.path.join(root, file)
                
                # আংশিক মিল থাকলে সেভ করে রাখা
                if team_clean[:4] == file_name_clean[:4]:
                    best_match = os.path.join(root, file)
                    
    return best_match

def get_logo(team_name):
    path = find_logo_path(team_name)
    if path and os.path.exists(path):
        return Image.open(path).convert("RGBA")
    
    # ডিফল্ট প্লেসহোল্ডার
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
        canvas = enhancer.enhance(0.5) # ৫০% অফাসিটি
    else:
        canvas = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (20, 20, 30, 255))

    draw = ImageDraw.Draw(canvas)

    try:
        font_series = ImageFont.truetype(FONT_BOLD_PATH, 40)
        font_match = ImageFont.truetype(FONT_BOLD_PATH, 35)
        font_v = ImageFont.truetype(FONT_BOLD_PATH, 80)
    except:
        font_series = font_match = font_v = ImageFont.load_default()

    # সিরিজের নাম
    series_text = series_name.upper()
    font_series_fit = get_font_size_to_fit(series_text, FONT_BOLD_PATH, 1200, 45)
    bbox = draw.textbbox((0, 0), series_text, font=font_series_fit)
    text_w = bbox[2] - bbox[0]
    draw.text(((POSTER_WIDTH - text_w) / 2 + 2, 42), series_text, font=font_series_fit, fill="black")
    draw.text(((POSTER_WIDTH - text_w) / 2, 40), series_text, font=font_series_fit, fill="white")

    # লোগো বসানো
    logo_size = 260
    logo1 = get_logo(team1).resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    logo2 = get_logo(team2).resize((logo_size, logo_size), Image.Resampling.LANCZOS)
    
    canvas.paste(logo1, (POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 150), logo1)
    canvas.paste(logo2, (3*POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 150), logo2)

    draw = ImageDraw.Draw(canvas)

    # মাঝখানে "V"
    bbox_v = draw.textbbox((0, 0), "V", font=font_v)
    v_w = bbox_v[2] - bbox_v[0]
    draw.text(((POSTER_WIDTH - v_w) / 2, POSTER_HEIGHT//2 - 100), "V", font=font_v, fill="white")

    # দলের নাম
    team_text = f"{team1.upper()} vs {team2.upper()}"
    font_teams_fit = get_font_size_to_fit(team_text, FONT_BOLD_PATH, 1400, 75)
    bbox_t = draw.textbbox((0, 0), team_text, font=font_teams_fit)
    t_w = bbox_t[2] - bbox_t[0]
    
    text_y = POSTER_HEIGHT - 180
    draw.text(((POSTER_WIDTH - t_w) / 2 + 2, text_y + 2), team_text, font=font_teams_fit, fill="black")
    draw.text(((POSTER_WIDTH - t_w) / 2, text_y), team_text, font=font_teams_fit, fill="white")

    # ম্যাচের ধরন
    if match_type:
        m_text = match_type.upper()
        bbox_m = draw.textbbox((0, 0), m_text, font=font_match)
        m_w = bbox_m[2] - bbox_m[0]
        draw.text(((POSTER_WIDTH - m_w) / 2, text_y + 90), m_text, font=font_match, fill="#FFD700")

    output_path = os.path.join(OUTPUT_DIR, output_filename)
    canvas.convert("RGB").save(output_path, quality=95) 
    return output_path
