import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

# Configurable keywords
KEYWORDS = [ 
    # English keywords
    'app', 'flutter', 'mobile', 'android', 'ios', 'swift', 'kotlin', 
    'native',  'desktop',  'web' , 'application', 'applications', 'software',  
    'mobile application', 'mobile app', 'mobile development',
    # Arabic keywords
    'فلاتر', 'تطبيق', 'تطبيقات', 'اندرويد', 'أندرويد', 'ايفون', 'أيفون', 
    'موبايل', 'جوال', 'هاتف', 'هواتف', 'تطوير تطبيقات', 'تطوير تطبيقات', 'برنامج','برامج' , 'برمجة' , 'نظام' , 'أنظمة' , 'نظام ذكي' , 'أنظمة ذكية'
]

STATE_FILE = 'state.json'
MAX_STATE_IDS = 1000  # Prevent state.json from growing infinitely

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return list(data.get("processed_ids", []))
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

def main():
    parser = argparse.ArgumentParser(description="Nafezly Freelance Projects Monitor")
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

    # 1. Fetch Nafezly projects page
    url = "https://nafezly.com/projects"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read()
    except Exception as e:
        print(f"Error fetching Nafezly page: {e}")
        sys.exit(1)

    # 2. Parse HTML
    soup = BeautifulSoup(html, 'html.parser')
    project_boxes = soup.find_all(class_='project-box')
    print(f"Found {len(project_boxes)} projects on page.")

    if not project_boxes:
        print("No project boxes found. The page structure might have changed.")
        sys.exit(1)

    processed_ids = load_state()
    processed_set = set(processed_ids)
    is_initial_run = len(processed_ids) == 0
    if is_initial_run:
        print("Initial run detected. Seeding database with current project IDs.")

    new_matches = []
    
    # Process from bottom to top (oldest on page to newest) so notifications are in chronological order
    for box in reversed(project_boxes):
        try:
            # Extract Link, Title, and ID
            link_tag = box.find('a', href=re.compile(r'https://nafezly.com/project/\d+'))
            if not link_tag:
                continue
                
            href = link_tag['href']
            title = link_tag.get_text(strip=True)
            
            # Extract Project ID
            id_match = re.search(r'/project/(\d+)', href)
            if not id_match:
                continue
            project_id = id_match.group(1)

            # Skip if already processed
            if project_id in processed_set:
                continue

            # Mark as processed
            processed_ids.append(project_id)
            processed_set.add(project_id)

            # Extract Description
            desc_tag = box.find('h3')
            desc = desc_tag.get_text(strip=True) if desc_tag else ""

            # Check keyword match
            matches, keyword = matches_keywords(title, desc)
            if not matches:
                continue

            # Extract metadata (Budget, Days, Posted Time)
            # Budget icon: fa-usd-circle
            budget = extract_meta_by_icon(box, 'fa-usd-circle')
            # Days icon: fa-business-time
            days = extract_meta_by_icon(box, 'fa-business-time')
            # Posted time icon: fa-clock
            posted_time = extract_meta_by_icon(box, 'fa-clock')

            project_info = {
                "id": project_id,
                "title": title,
                "link": href,
                "desc": desc,
                "budget": budget,
                "days": days,
                "posted_time": posted_time,
                "matched_keyword": keyword
            }
            new_matches.append(project_info)

        except Exception as box_err:
            print(f"Error parsing project box: {box_err}")
            continue

    # 3. Handle matches
    if new_matches:
        print(f"Found {len(new_matches)} new matching projects.")
        
        # If it's the initial run, the user might get spammed with up to 20 notifications.
        # We will notify them, but let's log how many we found.
        for project in new_matches:
            # Format message
            msg = (
                f"🔔 <b>مشروع جديد مطابق!</b>\n\n"
                f"<b>العنوان:</b> {escape_html(project['title'])}\n"
                f"<b>الميزانية:</b> {escape_html(project['budget'])}\n"
                f"<b>المدة:</b> {escape_html(project['days'])}\n"
                f"<b>نشر:</b> {escape_html(project['posted_time'])}\n\n"
                f"<b>الوصف:</b>\n{escape_html(project['desc'])}\n\n"
                f"📎 <a href=\"{project['link']}\">رابط المشروع على نفذلي</a>\n\n"
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

    # 4. Save updated state
    save_state(processed_ids)

if __name__ == "__main__":
    main()
