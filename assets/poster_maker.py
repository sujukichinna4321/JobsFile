import json
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import requests
from io import BytesIO

# --- কনফিগারেশন ---
POSTER_WIDTH = 1500
POSTER_HEIGHT = 750
BG_IMAGE_PATH = "assets/bg_main.png"  # আপনার ব্যাকগ্রাউন্ডের নাম
FONT_BOLD_PATH = "assets/fonts/Oswald-Bold.ttf" # আপনার ফন্টের নাম
FONT_REGULAR_PATH = "assets/fonts/Oswald-Regular.ttf" # আপনার ফন্টের নাম
TEAM_COLORS_FILE = "assets/team_colors.json"
OUTPUT_DIR = "posters"

# নিশ্চিত করা যে আউটপুট ফোল্ডার আছে
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

def download_image(url):
    """URL থেকে ইমেজ ডাউনলোড করে (লোগোর জন্য)"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def get_logo(team_name):
    """লোকাল ফোল্ডার থেকে লোগো খোঁজে, না পেলে None রিটার্ন করে"""
    # ফাইলের নাম স্পেস ছাড়া ছোট হাতের অক্ষরে সেভ করা ভালো (যেমন: sri_lanka.png)
    safe_name = team_name.lower().replace(" ", "_") + ".png"
    path = os.path.join("assets/logos", safe_name)
    if os.path.exists(path):
        return Image.open(path).convert("RGBA")
    return None

def create_poster(team1, team2, series_name, match_type, broadcaster, output_filename):
    print(f"Generating poster for {team1} vs {team2}...")
    
    # ১. বেস ক্যানভাস তৈরি
    canvas = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (0, 0, 0, 255))
    
    # ২. ব্যাকগ্রাউন্ড লোড এবং ৫০% অফাসিটি করা
    if os.path.exists(BG_IMAGE_PATH):
        bg = Image.open(BG_IMAGE_PATH).convert("RGBA")
        bg = bg.resize((POSTER_WIDTH, POSTER_HEIGHT))
        # অফাসিটি কমানো
        alpha = bg.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(0.5) # ৫০% অফাসিটি
        bg.putalpha(alpha)
        canvas.paste(bg, (0, 0), bg)
    else:
        print("Warning: Background image not found. Using black canvas.")

    # ৩. দলের কালার ওভারলে (বাম এবং ডান দিকে)
    colors = load_team_colors()
    c1_hex = colors.get(team1.lower(), "#333333") # ডিফল্ট ধূসর
    c2_hex = colors.get(team2.lower(), "#333333")
    
    c1_rgb = hex_to_rgb(c1_hex)
    c2_rgb = hex_to_rgb(c2_hex)
    
    overlay = Image.new("RGBA", (POSTER_WIDTH, POSTER_HEIGHT), (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    
    # বাম দিকের কালার (টিম ১)
    draw.polygon([(0,0), (POSTER_WIDTH//2, 0), (POSTER_WIDTH//2 - 100, POSTER_HEIGHT), (0, POSTER_HEIGHT)], fill=c1_rgb + (120,))
    # ডান দিকের কালার (টিম ২)
    draw.polygon([(POSTER_WIDTH//2, 0), (POSTER_WIDTH, 0), (POSTER_WIDTH, POSTER_HEIGHT), (POSTER_WIDTH//2 + 100, POSTER_HEIGHT)], fill=c2_rgb + (120,))
    
    canvas = Image.alpha_composite(canvas, overlay)

    # ৪. টেক্সট ও লোগো ড্র করার অবজেক্ট
    draw = ImageDraw.Draw(canvas)
    
    # ফন্ট লোড করা (সাইজ অনুযায়ী)
    try:
        font_series = ImageFont.truetype(FONT_BOLD_PATH, 60)
        font_teams = ImageFont.truetype(FONT_BOLD_PATH, 80)
        font_match = ImageFont.truetype(FONT_REGULAR_PATH, 40)
        font_small = ImageFont.truetype(FONT_REGULAR_PATH, 30)
    except:
        # যদি ফন্ট না পাওয়া যায় তবে ডিফল্ট ব্যবহার করবে
        font_series = font_teams = font_match = font_small = ImageFont.load_default()

    # ৫. টেক্সট বসানো (উপরে সেন্টারে)
    # সিরিজের নাম
    bbox = draw.textbbox((0, 0), series_name, font=font_series)
    text_w = bbox[2] - bbox[0]
    draw.text(((POSTER_WIDTH - text_w) / 2, 50), series_name, font=font_series, fill="white")

    # ৬. লোগো বসানো
    logo1 = get_logo(team1)
    logo2 = get_logo(team2)
    
    logo_size = 250
    # বাম দিকের লোগো
    if logo1:
        logo1 = logo1.resize((logo_size, logo_size))
        canvas.paste(logo1, (POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 100), logo1)
    # ডান দিকের লোগো
    if logo2:
        logo2 = logo2.resize((logo_size, logo_size))
        canvas.paste(logo2, (3*POSTER_WIDTH//4 - logo_size//2, POSTER_HEIGHT//2 - 100), logo2)

    # ৭. মাঝখানে "V" চিহ্ন
    draw = ImageDraw.Draw(canvas) # আবার ড্র অবজেক্ট নিতে হবে লোগো পেস্ট করার পর
    bbox_v = draw.textbbox((0, 0), "V", font=font_teams)
    v_w = bbox_v[2] - bbox_v[0]
    draw.text(((POSTER_WIDTH - v_w) / 2, POSTER_HEIGHT//2 - 90), "V", font=font_teams, fill="white")

    # ৮. দলের নাম (লোগোর নিচে)
    team_text = f"{team1} vs {team2}"
    bbox_t = draw.textbbox((0, 0), team_text, font=font_teams)
    t_w = bbox_t[2] - bbox_t[0]
    draw.text(((POSTER_WIDTH - t_w) / 2, POSTER_HEIGHT//2 + 180), team_text, font=font_teams, fill="white")

    # ৯. ম্যাচের ধরন (নিচের দিকে)
    bbox_m = draw.textbbox((0, 0), match_type, font=font_match)
    m_w = bbox_m[2] - bbox_m[0]
    draw.text(((POSTER_WIDTH - m_w) / 2, POSTER_HEIGHT - 100), match_type, font=font_match, fill="gold")

    # ১০. ব্রডকাস্টার টেক্সট (নিচে ডান কোণায়)
    draw.text((POSTER_WIDTH - 300, POSTER_HEIGHT - 60), f"Watch on {broadcaster}", font=font_small, fill="white")

    # ১১. ফাইনাল ছবি সেভ করা
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    canvas.convert("RGB").save(output_path, quality=90) # PNG বা JPEG
    print(f"Poster saved at {output_path}")
    return output_path

# --- টেস্ট করার জন্য (যখন সরাসরি রান করবেন) ---
if __name__ == "__main__":
    create_poster(
        team1="Pakistan",
        team2="Sri Lanka",
        series_name="Sri Lanka Tour of Pakistan 2026",
        match_type="2ND TEST",
        broadcaster="Willow",
        output_filename="test_pak_vs_sl.jpg"
    )
