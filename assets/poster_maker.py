import urllib.parse

def search_logo_from_api(team_name, sport="Soccer"):
    """
    TheSportsDB API থেকে দলের লোগো URL অনুসন্ধান করুন
    sport প্যারামিটার: Soccer (ফুটবল), Cricket (ক্রিকেট) ইত্যাদি
    """
    try:
        # API এন্ডপয়েন্ট: দলের নাম দিয়ে অনুসন্ধান করুন
        url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={urllib.parse.quote(team_name)}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get("teams"):
            # প্রথম মিলে যাওয়া ফলাফল নিন (প্রয়োজনে sport অনুযায়ী ফিল্টার করুন)
            for team in data["teams"]:
                # যদি sport মেলে, অথবা sport নির্দিষ্ট না করা হয়
                if team.get("strSport", "").lower() == sport.lower() or sport is None:
                    logo_url = team.get("strTeamBadge") or team.get("strTeamLogo")
                    if logo_url:
                        return logo_url
    except Exception as e:
        print(f"API search failed for {team_name}: {e}")
    return None

def download_logo(logo_url, save_path):
    """URL থেকে লোগো ডাউনলোড করে নির্দিষ্ট পাথে সংরক্ষণ করুন"""
    try:
        response = requests.get(logo_url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        img.save(save_path, "PNG")
        print(f"Logo saved: {save_path}")
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def get_logo(team_name, sport="Soccer"):
    """
    প্রথমে স্থানীয় লোগো খুঁজুন, না পেলে API থেকে ডাউনলোড করুন
    sport: Soccer অথবা Cricket
    """
    # ফাইলের নাম নিয়ম: ছোট হাতের অক্ষর, স্পেস _ দিয়ে প্রতিস্থাপন
    safe_name = team_name.lower().replace(" ", "_") + ".png"
    local_path = os.path.join("assets/logos", safe_name)
    
    # ১. স্থানীয় ফাইল থাকলে সরাসরি ব্যবহার করুন
    if os.path.exists(local_path):
        return Image.open(local_path).convert("RGBA")
    
    # ২. না থাকলে API থেকে অনুসন্ধান করুন
    print(f"Logo not found locally, searching API for: {team_name}")
    logo_url = search_logo_from_api(team_name, sport)
    
    if logo_url:
        # ডাউনলোড করে স্থানীয়ভাবে সংরক্ষণ করুন
        if download_logo(logo_url, local_path):
            return Image.open(local_path).convert("RGBA")
    
    # ৩. এখনও না পেলে None রিটার্ন করুন (পোস্টার খালি লোগো দেখাবে)
    print(f"No logo available for {team_name}")
    return None
