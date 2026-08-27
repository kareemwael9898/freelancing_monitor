const fs = require('fs');
const path = require('path');

// Configurable keywords
const KEYWORDS = [
    // English keywords
    'app', 'flutter', 'mobile', 'android', 'ios', 'swift', 'kotlin',
    'native', 'desktop', 'web', 'application', 'applications', 'software',
    'mobile application', 'mobile app', 'mobile development',

    // --- IoT / Embedded / Hardware ---
    'iot', 'embedded',
    'arduino', 'esp',
    'microcontroller', 'sensor', 'sensors', 'smart home',
    'automation', 'mqtt', 'bluetooth',

    // --- App Store / Publishing ---
    'google play', 'play store', 'app store', 'testflight',
    'apk', 'aab', 'ipa', 'publish', 'release',

    // --- General Dev ---
    'api', 'firebase', 'supabase', 'laravel',

    // --- Arabic: Flutter / Mobile ---
    'فلاتر', 'دارت', 'تطبيق', 'تطبيقات', 'تطبيق موبايل',
    'تطبيق جوال', 'تطبيق هاتف', 'تطبيق اندرويد', 'تطبيق ايفون',
    'اندرويد', 'أندرويد', 'ايفون', 'أيفون', 'آيفون',
    'موبايل', 'جوال', 'هاتف', 'هواتف', 'هاتف ذكي',
    'تطوير تطبيقات', 'مطور تطبيقات', 'مبرمج تطبيقات',
    'برنامج', 'برامج', 'برمجة', 'نظام', 'أنظمة',

    // --- Arabic: IoT / Embedded ---
    'اردوينو', 'أردوينو',
    'حساسات', 'مستشعرات', 'منزل ذكي', 'ذكي',
    'نظام ذكي', 'أنظمة ذكية', 'أتمتة', 'تحكم عن بعد',

    // --- Arabic: General Dev ---
    'واجهة مستخدم', 'تجربة مستخدم',
    'متجر الكتروني', 'متجر إلكتروني',
    'لوحة تحكم', 'داشبورد', 'موقع'
];

const EXCLUDE_KEYWORDS = [
    // --- Website builders (not app dev) ---
    'wordpress', 'elementor', 'shopify', 'woocommerce',
    'ووردبريس', 'وورد بريس', 'شوبيفاي', 'ووكومرس', 'وردبريس', 'ورد بريس',
    'notion', 'نوشن', 'canva', 'كانفا', ' سلة', 'salla', 'منصة زد', 'odoo', 'أودو',

    // --- SEO / digital marketing ---
    'seo', 'سيو', 'SSL',

    // --- Generic dev ---
    'php', 'react', 'typescript', 'devops', 'next.js', 'power bi',

    'تقييمات', 'ديسكورد', 'discord', 'كواي'
];

// Exclude if comes together
const EXCLUDE_IF_COMES_TOGETHER = [
    ['بوت', 'حجز']
];

const STATE_FILE = 'state.json';
const MAX_STATE_IDS = 5000; // Prevent state.json from growing infinitely

function loadState() {
    if (fs.existsSync(STATE_FILE)) {
        try {
            const rawData = fs.readFileSync(STATE_FILE, 'utf-8');
            const data = JSON.parse(rawData);
            const rawIds = Array.isArray(data.processed_ids) ? data.processed_ids : [];
            // Migrate older pure numeric IDs to nafezly_ prefix
            const migratedIds = [];
            for (const pid of rawIds) {
                const pidStr = String(pid);
                if (/^\d+$/.test(pidStr)) {
                    migratedIds.push(`nafezly_${pidStr}`);
                } else {
                    migratedIds.push(pidStr);
                }
            }
            return migratedIds;
        } catch (e) {
            console.log(`Error loading state.json: ${e.message}. Starting fresh.`);
        }
    }
    return [];
}

function saveState(processedIds) {
    // Keep only the last MAX_STATE_IDS to keep the file size small
    const idList = processedIds.slice(-MAX_STATE_IDS);
    try {
        fs.writeFileSync(STATE_FILE, JSON.stringify({ processed_ids: idList }, null, 2), 'utf-8');
    } catch (e) {
        console.log(`Error saving state.json: ${e.message}`);
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function stripHtml(html) {
    if (!html) return "";
    return html
        .replace(/<script\b[^<]*>(?:[\s\S]*?<\/script>)/gi, '')
        .replace(/<style\b[^<]*>(?:[\s\S]*?<\/style>)/gi, '')
        .replace(/<[^>]+>/g, ' ')
        .replace(/&nbsp;/gi, ' ')
        .replace(/&amp;/gi, '&')
        .replace(/&lt;/gi, '<')
        .replace(/&gt;/gi, '>')
        .replace(/&quot;/gi, '"')
        .replace(/&#39;/gi, "'")
        .replace(/\s+/g, ' ')
        .trim();
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function isAscii(str) {
    return /^[\x00-\x7F]*$/.test(str);
}

function checkKeywordInText(kw, combinedText) {
    const kwLower = kw.toLowerCase();
    if (isAscii(kwLower)) {
        const regex = new RegExp('\\b' + escapeRegExp(kwLower) + '\\b', 'i');
        return regex.test(combinedText);
    } else {
        return combinedText.includes(kwLower);
    }
}

function matchesKeywords(title, desc) {
    const combinedText = (title + " " + desc).toLowerCase();

    for (const kw of EXCLUDE_KEYWORDS) {
        if (checkKeywordInText(kw, combinedText)) {
            return [false, null];
        }
    }

    for (const [kw1, kw2] of EXCLUDE_IF_COMES_TOGETHER) {
        if (checkKeywordInText(kw1, combinedText) && checkKeywordInText(kw2, combinedText)) {
            return [false, null];
        }
    }

    for (const kw of KEYWORDS) {
        if (checkKeywordInText(kw, combinedText)) {
            return [true, kw];
        }
    }

    return [false, null];
}

function extractMetaByIcon(boxHtml, iconClass) {
    const iconIdx = boxHtml.search(new RegExp(`class=["'][^"']*${escapeRegExp(iconClass)}`, 'i'));
    if (iconIdx === -1) return "";

    const before = boxHtml.substring(0, iconIdx);
    const after = boxHtml.substring(iconIdx);

    const lastSpanOpen = before.lastIndexOf('<span');
    if (lastSpanOpen === -1) return "";

    const spanClose = after.indexOf('</span>');
    if (spanClose === -1) return "";

    const fullSpanHtml = boxHtml.substring(lastSpanOpen, iconIdx + spanClose + 7);
    return stripHtml(fullSpanHtml);
}

async function sendTelegramMessage(token, chatId, message) {
    const url = `https://api.telegram.org/bot${token}/sendMessage`;
    const params = new URLSearchParams({
        chat_id: chatId,
        text: message,
        parse_mode: 'HTML',
        disable_web_page_preview: 'false'
    });

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: params.toString()
        });

        const resData = await response.json();
        if (!resData.ok) {
            console.log(`Failed to send Telegram message:`, resData);
            return false;
        }
        console.log("Telegram message sent successfully.");
        return true;
    } catch (e) {
        console.log(`Error sending Telegram message: ${e.message}`);
        return false;
    }
}

async function fetchPage(url, extraHeaders = {}) {
    const defaultHeaders = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    };
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
        const response = await fetch(url, {
            headers: { ...defaultHeaders, ...extraHeaders },
            signal: controller.signal
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} ${response.statusText}`);
        }
        return await response.text();
    } finally {
        clearTimeout(timeout);
    }
}

async function getNafezlyProjects() {
    const url = "https://nafezly.com/projects";
    let html;
    try {
        html = await fetchPage(url);
    } catch (e) {
        console.log(`Error fetching Nafezly page: ${e.message}`);
        return [];
    }

    const rawBoxes = html.split(/class=["'][^"']*project-box[^"']*["']/i).slice(1);
    const projects = [];

    for (let i = rawBoxes.length - 1; i >= 0; i--) {
        const box = rawBoxes[i];
        try {
            const linkMatch = box.match(/<a\b[^>]*href=["']([^"']*\/project\/(\d+)[^"']*)["'][^>]*>([\s\S]*?)<\/a>/i);
            if (!linkMatch) continue;

            const href = linkMatch[1];
            const projectNum = linkMatch[2];
            const projectId = `nafezly_${projectNum}`;
            const title = stripHtml(linkMatch[3]);

            const descMatch = box.match(/<h3\b[^>]*>([\s\S]*?)<\/h3>/i);
            const desc = descMatch ? stripHtml(descMatch[1]) : "";

            const budget = extractMetaByIcon(box, 'fa-usd-circle');
            const days = extractMetaByIcon(box, 'fa-business-time');
            const posted_time = extractMetaByIcon(box, 'fa-clock');

            projects.push({
                id: projectId,
                title: title,
                link: href,
                desc: desc,
                budget: budget,
                days: days,
                posted_time: posted_time,
                site_name: "نفذلي",
                site_key: "nafezly"
            });
        } catch (boxErr) {
            console.log(`Error parsing Nafezly project box: ${boxErr.message}`);
        }
    }
    return projects;
}

async function getMostaqlProjects() {
    const url = "https://mostaql.com/projects?category=development&sort=latest";
    let html;
    try {
        html = await fetchPage(url);
    } catch (e) {
        console.log(`Error fetching Mostaql page: ${e.message}`);
        return [];
    }

    const rawRows = html.split(/<tr\b[^>]*class=["'][^"']*project-row[^"']*["']/i).slice(1);
    const projects = [];

    for (let i = rawRows.length - 1; i >= 0; i--) {
        const row = rawRows[i];
        try {
            const h2Match = row.match(/<h2\b[^>]*>([\s\S]*?)<\/h2>/i);
            if (!h2Match) continue;

            const linkMatch = h2Match[1].match(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i);
            if (!linkMatch) continue;

            let href = linkMatch[1];
            if (!href.startsWith('http')) {
                href = new URL(href, "https://mostaql.com").href;
            }
            const title = stripHtml(linkMatch[2]);

            const idMatch = href.match(/\/project\/(\d+)/);
            if (!idMatch) continue;
            const projectId = `mostaql_${idMatch[1]}`;

            const descMatch = row.match(/<a\b[^>]*class=["'][^"']*details-url[^"']*["'][^>]*>([\s\S]*?)<\/a>/i);
            const desc = descMatch ? stripHtml(descMatch[1]) : "";

            const timeMatch = row.match(/<time\b[^>]*>([\s\S]*?)<\/time>/i);
            const posted_time = timeMatch ? stripHtml(timeMatch[1]) : "";

            projects.push({
                id: projectId,
                title: title,
                link: href,
                desc: desc,
                budget: "غير معلن في القائمة",
                days: "غير محدد",
                posted_time: posted_time,
                site_name: "مستقل",
                site_key: "mostaql"
            });
        } catch (rowErr) {
            console.log(`Error parsing Mostaql project row: ${rowErr.message}`);
        }
    }
    return projects;
}

async function getKafiilProjects() {
    const url = "https://kafiil.com/projects";
    let html;
    try {
        html = await fetchPage(url);
    } catch (e) {
        console.log(`Error fetching Kafiil page: ${e.message}`);
        return [];
    }

    const rawBoxes = html.split(/class=["'][^"']*project-box[^"']*["']/i).slice(1);
    const projects = [];

    for (let i = rawBoxes.length - 1; i >= 0; i--) {
        const box = rawBoxes[i];
        try {
            const linkMatch = box.match(/<a\b[^>]*class=["'][^"']*\bname\b[^"']*["'][^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i) ||
                              box.match(/<a\b[^>]*href=["']([^"']+)["'][^>]*class=["'][^"']*\bname\b[^"']*["'][^>]*>([\s\S]*?)<\/a>/i);
            if (!linkMatch) continue;

            let href = linkMatch[1];
            if (!href.startsWith('http')) {
                href = new URL(href, "https://kafiil.com").href;
            }

            let titleInner = linkMatch[2].replace(/<span\b[^>]*class=["'][^"']*\btag\b[^"']*["'][^>]*>[\s\S]*?<\/span>/gi, '');
            const title = stripHtml(titleInner);

            const idMatch = href.match(/\/project\/(\d+)/);
            if (!idMatch) continue;
            const projectId = `kafiil_${idMatch[1]}`;

            const descMatch = box.match(/class=["'][^"']*\binfo-content\b[^"']*["'][^>]*>([\s\S]*?)<\/(?:div|p|span)>/i) ||
                              box.match(/<div\b[^>]*class=["'][^"']*\binfo-content\b[^"']*["'][^>]*>([\s\S]*?)<\/div>/i);
            const desc = descMatch ? stripHtml(descMatch[1]) : "";

            const priceMatch = box.match(/class=["'][^"']*\bprice\b[^"']*["'][^>]*>([\s\S]*?)<\/(?:div|span|p)>/i) ||
                               box.match(/<div\b[^>]*class=["'][^"']*\bprice\b[^"']*["'][^>]*>([\s\S]*?)<\/div>/i);
            const budget = priceMatch ? stripHtml(priceMatch[1]) : "";

            const posted_time = extractMetaByIcon(box, 'fa-clock');

            projects.push({
                id: projectId,
                title: title,
                link: href,
                desc: desc,
                budget: budget,
                days: "غير محدد",
                posted_time: posted_time,
                site_name: "كفيل",
                site_key: "kafiil"
            });
        } catch (boxErr) {
            console.log(`Error parsing Kafiil project box: ${boxErr.message}`);
        }
    }
    return projects;
}

async function getKhamsatRequests() {
    const url = "https://khamsat.com/community/requests";
    const extraHeaders = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
    };
    let html;
    try {
        html = await fetchPage(url, extraHeaders);
    } catch (e) {
        console.log(`Error fetching Khamsat page: ${e.message}`);
        return [];
    }

    const rawRows = html.split(/<tr\b[^>]*class=["'][^"']*\bforum_post\b[^"']*["']/i).slice(1);
    const projects = [];

    for (let i = rawRows.length - 1; i >= 0; i--) {
        const row = rawRows[i];
        try {
            const headMatch = row.match(/<h3\b[^>]*class=["'][^"']*\bdetails-head\b[^"']*["'][^>]*>([\s\S]*?)<\/h3>/i);
            if (!headMatch) continue;

            const linkMatch = headMatch[1].match(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i);
            if (!linkMatch) continue;

            let href = linkMatch[1];
            if (!href.startsWith('http')) {
                href = new URL(href, "https://khamsat.com").href;
            }
            const title = stripHtml(linkMatch[2]);

            const match = href.match(/\/community\/requests\/(\d+)/);
            if (!match) continue;
            const projectId = `khamsat_${match[1]}`;

            const timeMatch = row.match(/<span\b[^>]*dir=["']ltr["'][^>]*>([\s\S]*?)<\/span>/i);
            const posted_time = timeMatch ? stripHtml(timeMatch[1]) : "";

            projects.push({
                id: projectId,
                title: title,
                link: href,
                desc: "",
                budget: "تبدأ من $5",
                days: "غير محدد",
                posted_time: posted_time,
                site_name: "خمسات",
                site_key: "khamsat"
            });
        } catch (rowErr) {
            console.log(`Error parsing Khamsat request row: ${rowErr.message}`);
        }
    }
    return projects;
}

async function main() {
    const isDryRunArg = process.argv.includes('--dry-run');
    let dryRun = isDryRunArg;

    const botToken = process.env.TELEGRAM_BOT_TOKEN;
    const chatId = process.env.TELEGRAM_CHAT_ID;

    if (!dryRun && (!botToken || !chatId)) {
        console.log("Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables are missing.");
        console.log("Forcing --dry-run mode.");
        dryRun = true;
    }

    // 1. Fetch projects from all sources
    let start = Date.now();
    const nafezlyProjects = await getNafezlyProjects();
    const nafezlyTime = (Date.now() - start) / 1000;

    start = Date.now();
    const mostaqlProjects = await getMostaqlProjects();
    const mostaqlTime = (Date.now() - start) / 1000;

    start = Date.now();
    const kafiilProjects = await getKafiilProjects();
    const kafiilTime = (Date.now() - start) / 1000;

    start = Date.now();
    const khamsatRequests = await getKhamsatRequests();
    const khamsatTime = (Date.now() - start) / 1000;

    console.log(`Found ${nafezlyProjects.length} projects on Nafezly in ${nafezlyTime.toFixed(2)} seconds.`);
    console.log(`Found ${mostaqlProjects.length} projects on Mostaql in ${mostaqlTime.toFixed(2)} seconds.`);
    console.log(`Found ${kafiilProjects.length} projects on Kafiil in ${kafiilTime.toFixed(2)} seconds.`);
    console.log(`Found ${khamsatRequests.length} projects on Khamsat in ${khamsatTime.toFixed(2)} seconds.`);

    const allProjects = [...nafezlyProjects, ...mostaqlProjects, ...kafiilProjects, ...khamsatRequests];

    const processedIds = loadState();
    const processedSet = new Set(processedIds);
    const isInitialRun = processedIds.length === 0;

    if (isInitialRun) {
        console.log("Initial run detected. Seeding database with current project IDs.");
    }

    const newMatches = [];

    for (const project of allProjects) {
        const projectId = project.id;

        // Skip if already processed
        if (processedSet.has(projectId)) {
            continue;
        }

        // Mark as processed
        processedIds.push(projectId);
        processedSet.add(projectId);

        // Check keyword match
        const [matches, keyword] = matchesKeywords(project.title, project.desc);
        if (!matches) {
            continue;
        }

        project.matched_keyword = keyword;
        newMatches.push(project);
    }

    // 2. Handle matches
    if (newMatches.length > 0) {
        console.log(`Found ${newMatches.length} new matching projects.`);

        for (const project of newMatches) {
            const siteTag = `على ${project.site_name}`;
            const msg = (
                `🔔 <b>مشروع جديد ${siteTag}!</b>\n\n` +
                `<b>العنوان:</b> ${escapeHtml(project.title)}\n` +
                `<b>الميزانية:</b> ${escapeHtml(project.budget)}\n` +
                `<b>المدة:</b> ${escapeHtml(project.days)}\n` +
                `<b>نشر:</b> ${escapeHtml(project.posted_time)}\n\n` +
                `<b>الوصف:</b>\n${escapeHtml(project.desc)}\n\n` +
                `📎 <a href="${project.link}">رابط المشروع على ${project.site_name}</a>\n\n` +
                `<i>الكلمة المفتاحية:</i> #${project.matched_keyword}`
            );

            if (dryRun) {
                console.log("\n==========================================");
                console.log("DRY RUN MESSAGE:");
                console.log(msg);
                console.log("==========================================\n");
            } else {
                await sendTelegramMessage(botToken, chatId, msg);
            }
        }
    } else {
        console.log("No new matching projects found.");
    }

    // 3. Save updated state
    saveState(processedIds);
}

if (require.main === module) {
    main().catch(err => {
        console.error(`Fatal error in main: ${err}`);
    });
}
