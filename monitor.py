import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.parse
import time
from bs4 import BeautifulSoup

# Configurable keywords
KEYWORDS = [
    # English keywords
    'app', 'flutter', 'mobile', 'android', 'ios', 'swift', 'kotlin',
    'native', 'desktop', 'web', 'application', 'applications', 'software',
    'mobile application', 'mobile app', 'mobile development',

    # --- IoT / Embedded / Hardware ---
    'iot', 'embedded',
    'arduino', 'esp',
    'microcontroller', 'sensor', 'sensors', 'smart home',
    'automation', 'mqtt', 'bluetooth',

    # --- App Store / Publishing ---
    'google play', 'play store', 'app store', 'testflight',
    'apk', 'aab', 'ipa', 'publish', 'release',

    # --- General Dev ---
    'api', 'firebase', 'supabase', 'laravel',

    # --- Arabic: Flutter / Mobile ---
    'فلاتر', 'دارت', 'تطبيق', 'تطبيقات', 'تطبيق موبايل',
    'تطبيق جوال', 'تطبيق هاتف', 'تطبيق اندرويد', 'تطبيق ايفون',
    'اندرويد', 'أندرويد', 'ايفون', 'أيفون', 'آيفون',
    'موبايل', 'جوال', 'هاتف', 'هواتف', 'هاتف ذكي',
    'تطوير تطبيقات', 'مطور تطبيقات', 'مبرمج تطبيقات',
    'برنامج', 'برامج', 'برمجة', 'نظام', 'أنظمة',

    # --- Arabic: IoT / Embedded ---
    'اردوينو', 'أردوينو',
    'حساسات', 'مستشعرات', 'منزل ذكي', 'ذكي',
    'نظام ذكي', 'أنظمة ذكية', 'أتمتة', 'تحكم عن بعد',

    # --- Arabic: General Dev ---
    'واجهة مستخدم', 'تجربة مستخدم',
    'متجر الكتروني', 'متجر إلكتروني',
    'لوحة تحكم', 'داشبورد', 'موقع'
]

STATE_FILE = 'state.json'
MAX_STATE_IDS = 5000  # Prevent state.json from growing infinitely

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                raw_ids = list(data.get("processed_ids", []))
                # Migrate older pure numeric IDs to nafezly_ prefix
                migrated_ids = []
                for pid in raw_ids:
                    if pid.isdigit():
                        migrated_ids.append(f"nafezly_{pid}")
                    else:
                        migrated_ids.append(pid)
                return migrated_ids
        except Exception as e:
            print(f"Error loading state.json: {e}. Starting fresh.")
    return []

def save_state(processed_ids):
    # Keep only the last MAX_STATE_IDS to keep the file size small
    id_list = processed_ids[-MAX_STATE_IDS:]
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({"processed_ids": id_list}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving state.json: {e}")

def escape_html(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def matches_keywords(title, desc):
    combined_text = (title + " " + desc).lower()
    for kw in KEYWORDS:
        # Match whole word boundary for English, or substring for Arabic
        if re.search(r'\b' + re.escape(kw.lower()) + r'\b', combined_text) if kw.isascii() else (kw.lower() in combined_text):
            return True, kw
    return False, None

def extract_meta_by_icon(box, icon_class):
    icon = box.find('span', class_=re.compile(icon_class)) or box.find('i', class_=re.compile(icon_class))
    if not icon:
        return ""
    parent_span = icon.find_parent('span')
    if parent_span:
        # Strip all tags inside to get only clean text
        text = parent_span.get_text(strip=True)
        # Clean up double spaces
        return re.sub(r'\s+', ' ', text)
    return ""

def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": "false"
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if not res_data.get("ok"):
                print(f"Failed to send Telegram message: {res_data}")
                return False
            print("Telegram message sent successfully.")
            return True
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

def get_nafezly_projects():
    url = "https://nafezly.com/projects"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read()
    except Exception as e:
        print(f"Error fetching Nafezly page: {e}")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    project_boxes = soup.find_all(class_='project-box')
    projects = []
    for box in reversed(project_boxes):
        try:
            link_tag = box.find('a', href=re.compile(r'https://nafezly.com/project/\d+'))
            if not link_tag:
                continue
                
            href = link_tag['href']
            title = link_tag.get_text(strip=True)
            
            id_match = re.search(r'/project/(\d+)', href)
            if not id_match:
                continue
            project_id = f"nafezly_{id_match.group(1)}"

            desc_tag = box.find('h3')
            desc = desc_tag.get_text(strip=True) if desc_tag else ""

            budget = extract_meta_by_icon(box, 'fa-usd-circle')
            days = extract_meta_by_icon(box, 'fa-business-time')
            posted_time = extract_meta_by_icon(box, 'fa-clock')

            projects.append({
                "id": project_id,
                "title": title,
                "link": href,
                "desc": desc,
                "budget": budget,
                "days": days,
                "posted_time": posted_time,
                "site_name": "نفذلي",
                "site_key": "nafezly"
            })
        except Exception as box_err:
            print(f"Error parsing Nafezly project box: {box_err}")
    return projects

def get_mostaql_projects():
    url = "https://mostaql.com/projects?category=development&sort=latest"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read()
    except Exception as e:
        print(f"Error fetching Mostaql page: {e}")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.select('tr.project-row')
    projects = []
    for row in reversed(rows):
        try:
            title_el = row.select_one('h2.mrg--bt-reset a') or row.select_one('h2 a')
            if not title_el:
                continue
            href = title_el.get('href', '')
            if not href:
                continue
            href = urllib.parse.urljoin("https://mostaql.com", href)
            title = title_el.get_text(strip=True)
            
            id_match = re.search(r'/project/(\d+)', href)
            if not id_match:
                continue
            project_id = f"mostaql_{id_match.group(1)}"
            
            desc_el = row.select_one('a.details-url')
            desc = desc_el.get_text(strip=True) if desc_el else ""
            
            posted_time_el = row.select_one('time')
            posted_time = posted_time_el.get_text(strip=True) if posted_time_el else ""
            posted_time = re.sub(r'\s+', ' ', posted_time)
            
            projects.append({
                "id": project_id,
                "title": title,
                "link": href,
                "desc": desc,
                "budget": "غير معلن في القائمة",
                "days": "غير محدد",
                "posted_time": posted_time,
                "site_name": "مستقل",
                "site_key": "mostaql"
            })
        except Exception as row_err:
            print(f"Error parsing Mostaql project row: {row_err}")
    return projects

def get_kafiil_projects():
    url = "https://kafiil.com/projects"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read()
    except Exception as e:
        print(f"Error fetching Kafiil page: {e}")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    project_boxes = soup.find_all(class_='project-box')
    projects = []
    for box in reversed(project_boxes):
        try:
            link_tag = box.select_one('a.name')
            if not link_tag:
                continue
            
            href = link_tag.get('href', '')
            if not href:
                continue
            href = urllib.parse.urljoin("https://kafiil.com", href)
            
            import copy
            link_tag_copy = copy.copy(link_tag)
            tag_el = link_tag_copy.find('span', class_='tag')
            if tag_el:
                tag_el.extract()
            title = link_tag_copy.get_text(strip=True)
            
            id_match = re.search(r'/project/(\d+)', href)
            if not id_match:
                continue
            project_id = f"kafiil_{id_match.group(1)}"
            
            desc_el = box.select_one('.info-content')
            desc = desc_el.get_text(strip=True) if desc_el else ""
            
            price_el = box.select_one('.price')
            budget = price_el.get_text(strip=True) if price_el else ""
            
            clock_icon = box.find('i', class_=re.compile(r'fa-clock'))
            posted_time = clock_icon.parent.get_text(strip=True) if clock_icon else ""
            posted_time = re.sub(r'\s+', ' ', posted_time)
            
            projects.append({
                "id": project_id,
                "title": title,
                "link": href,
                "desc": desc,
                "budget": budget,
                "days": "غير محدد",
                "posted_time": posted_time,
                "site_name": "كفيل",
                "site_key": "kafiil"
            })
        except Exception as box_err:
            print(f"Error parsing Kafiil project box: {box_err}")
    return projects

def get_khamsat_requests():
    url = "https://khamsat.com/community/requests"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read()
    except Exception as e:
        print(f"Error fetching Khamsat page: {e}")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr', class_='forum_post')
    projects = []
    for row in reversed(rows):
        try:
            link_tag = row.find('h3', class_='details-head').find('a')
            if not link_tag:
                continue
            
            href = link_tag.get('href', '')
            if not href:
                continue
            href = urllib.parse.urljoin("https://khamsat.com", href)
            title = link_tag.get_text(strip=True)
            
            # Extract ID
            match = re.search(r'/community/requests/(\d+)', href)
            if not match:
                continue
            project_id = f"khamsat_{match.group(1)}"
            
            span_time = row.find('span', dir='ltr')
            posted_time = span_time.get_text(strip=True) if span_time else ""
            posted_time = re.sub(r'\s+', ' ', posted_time)
            
            projects.append({
                "id": project_id,
                "title": title,
                "link": href,
                "desc": "",
                "budget": "تبدأ من $5",
                "days": "غير محدد",
                "posted_time": posted_time,
                "site_name": "خمسات",
                "site_key": "khamsat"
            })
        except Exception as row_err:
            print(f"Error parsing Khamsat request row: {row_err}")
    return projects

def main():
    parser = argparse.ArgumentParser(description="Freelance Projects Monitor")
    parser.bin = "monitor"
    parser.add_argument("--dry-run", action="store_true", help="Print matches to console instead of sending to Telegram")
    args = parser.parse_args()

    # Load credentials if not dry run
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not args.dry_run and (not bot_token or not chat_id):
        print("Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables are missing.")
        print("Forcing --dry-run mode.")
        args.dry_run = True

    # 1. Fetch projects from all sources
    start = time.time()
    nafezly_projects = get_nafezly_projects()
    nafezly_time = time.time() - start

    start = time.time()
    mostaql_projects = get_mostaql_projects()
    mostaql_time = time.time() - start

    start = time.time()
    kafiil_projects = get_kafiil_projects()
    kafiil_time = time.time() - start

    start = time.time()
    khamsat_requests = get_khamsat_requests()
    khamsat_time = time.time() - start
    
    print(f"Found {len(nafezly_projects)} projects on Nafezly in {nafezly_time:.2f} seconds.")
    print(f"Found {len(mostaql_projects)} projects on Mostaql in {mostaql_time:.2f} seconds.")
    print(f"Found {len(kafiil_projects)} projects on Kafiil in {kafiil_time:.2f} seconds.")
    print(f"Found {len(khamsat_requests)} projects on Khamsat in {khamsat_time:.2f} seconds.")

    all_projects = nafezly_projects + mostaql_projects + kafiil_projects + khamsat_requests

    processed_ids = load_state()
    processed_set = set(processed_ids)
    is_initial_run = len(processed_ids) == 0
    if is_initial_run:
        print("Initial run detected. Seeding database with current project IDs.")

    new_matches = []
    
    for project in all_projects:
        project_id = project["id"]
        
        # Skip if already processed
        if project_id in processed_set:
            continue

        # Mark as processed
        processed_ids.append(project_id)
        processed_set.add(project_id)

        # Check keyword match
        matches, keyword = matches_keywords(project["title"], project["desc"])
        if not matches:
            continue

        project["matched_keyword"] = keyword
        new_matches.append(project)

    # 2. Handle matches
    if new_matches:
        print(f"Found {len(new_matches)} new matching projects.")
        
        for project in new_matches:
            # Format message
            site_tag = f"على {project['site_name']}"
            msg = (
                f"🔔 <b>مشروع جديد {site_tag}!</b>\n\n"
                f"<b>العنوان:</b> {escape_html(project['title'])}\n"
                f"<b>الميزانية:</b> {escape_html(project['budget'])}\n"
                f"<b>المدة:</b> {escape_html(project['days'])}\n"
                f"<b>نشر:</b> {escape_html(project['posted_time'])}\n\n"
                f"<b>الوصف:</b>\n{escape_html(project['desc'])}\n\n"
                f"📎 <a href=\"{project['link']}\">رابط المشروع على {project['site_name']}</a>\n\n"
                f"<i>الكلمة المفتاحية:</i> #{project['matched_keyword']}"
            )
            
            if args.dry_run:
                print("\n==========================================")
                print("DRY RUN MESSAGE:")
                print(msg)
                print("==========================================\n")
            else:
                send_telegram_message(bot_token, chat_id, msg)
    else:
        print("No new matching projects found.")

    # 3. Save updated state
    save_state(processed_ids)

if __name__ == "__main__":
    main()
