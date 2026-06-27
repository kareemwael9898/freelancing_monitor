import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import re

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
                "days": "غير حدد",
                "posted_time": posted_time,
                "site_name": "خمسات",
                "site_key": "khamsat"
            })
        except Exception as row_err:
            print(f"Error parsing Khamsat request row: {row_err}")
    return projects

projects = get_khamsat_requests()
print(f"Parsed {len(projects)} projects from Khamsat.")
if projects:
    print("Example project:")
    print(projects[-1])
