#!/usr/bin/env python3
"""
創作室 Dashboard Generator — Full Width (No Sidebar)
支援 TV 評論 + K-Pop 內容 dual-source
"""

import os
import re
from datetime import datetime

TV_REVIEWS_DIR = "/home/ubuntu/.openclaw/workspace-creation/tv-reviews"
KPOP_POSTS_DIR = "/home/ubuntu/.openclaw/workspace-kpop/posts"
OUTPUT_PATH = "/home/ubuntu/.openclaw/workspace-creation/web/index.html"

def get_reviews(content_type="tv"):
    """從 md files 讀取內容
    """
    dir_path = TV_REVIEWS_DIR if content_type == "tv" else KPOP_POSTS_DIR

    if not os.path.exists(dir_path):
        print(f"   ⚠️ Directory not found: {dir_path}")
        return []

    reviews = []
    files = sorted(os.listdir(dir_path), reverse=True)

    for i, filename in enumerate(files, 1):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(dir_path, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        title = filename.replace('.md', '').replace('2026-03-19-', '')
        platform = 'TVB' if content_type == "tv" else 'K-Pop'
        tags = []

        for line in lines[:15]:
            if line.startswith('title:'):
                title = line.split('title:')[1].strip().strip('"').strip("'")
            elif line.startswith('platform:'):
                platform = line.split('platform:')[1].strip()
            elif line.startswith('artist:'):
                platform = line.split('artist:')[1].strip()
            elif line.startswith('tags:'):
                tags_str = line.split('tags:')[1].strip()
                tags = re.findall(r'\[([^\]]+)\]', tags_str)

        article_match = re.search(r'##\s*文章\s*\n+(.+?)(?=^##\s|\Z)', content, re.MULTILINE | re.DOTALL)

        if article_match:
            article = article_match.group(1).strip()
        else:
            article = content
            if article.startswith('---'):
                parts = article.split('---', 2)
                if len(parts) >= 3:
                    article = parts[2]
            article = re.sub(r'^# .+\n', '', article, flags=re.MULTILINE)
            article = re.sub(r'^## .+\n', '', article, flags=re.MULTILINE)
            article = article.strip()

        article = article.replace('\n\n', '</p><p>')
        article = f'<p>{article}</p>'
        article = re.sub(r'### (.+)', r'<h4>\1</h4>', article)
        article = re.sub(r'## (.+)', r'<h3>\1</h3>', article)

        preview_text = re.sub('<[^>]+>', '', article)
        preview = preview_text[:120] + '...' if len(preview_text) > 120 else preview_text

        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', filename)
        for line in lines[:10]:
            if line.startswith('date:'):
                date_match = re.match(r'(\d{4}-\d{2}-\d{2})', line)
                break
        date = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')

        reviews.append({
            'id': i,
            'title': title,
            'platform': platform,
            'content_type': content_type,
            'date': date,
            'tags': tags,
            'preview': preview,
            'article': article
        })

    return reviews

def escape_js(text):
    if not text:
        return ""
    return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')

def escape_js_template(text):
    if not text:
        return ""
    return text.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')

def generate_article_js(review, idx, offset):
    return f"""{{
                id: {idx + offset},
                title: "{escape_js(review['title'])}",
                platform: "{escape_js(review['platform'])}",
                content_type: "{review['content_type']}",
                date: "{review['date']}",
                tags: {review['tags']},
                preview: "{escape_js(review['preview'])}",
                content: `{escape_js_template(review['article'])} `
            }}"""

def generate_html(all_articles):
    tv_articles = [a for a in all_articles if a['content_type'] == 'tv']
    kpop_articles = [a for a in all_articles if a['content_type'] == 'kpop']

    articles_js_parts = []
    for idx, article in enumerate(all_articles):
        articles_js_parts.append(generate_article_js(article, idx, 0))
    articles_js = ',\n            '.join(articles_js_parts)

    tv_platforms = sorted(list(set([a['platform'] for a in tv_articles])))
    kpop_platforms = sorted(list(set([a['platform'] for a in kpop_articles])))

    tv_buttons = ''.join([f'<button class="filter-btn" onclick="filterByPlatform(\'tv\', \'{p}\')">{p}</button>' for p in tv_platforms])
    kpop_buttons = ''.join([f'<button class="filter-btn" onclick="filterByPlatform(\'kpop\', \'{p}\')">{p}</button>' for p in kpop_platforms])

    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎬 創作室 Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+HK:wght@300;400;500;600;700&family=Noto+Serif+HK:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #FAFAF8;
            --text: #18181B;
            --text-muted: #71717A;
            --accent-tv: #DC2626;
            --accent-kpop: #8B5CF6;
            --card-bg: #FFFFFF;
            --border: #E4E4E7;
            --topbar-bg: #18181B;
            --topbar-text: #FAFAF8;
            --topbar-muted: #A1A1AA;
        }}

        [data-theme="dark"] {{
            --bg: #18181B;
            --text: #FAFAF8;
            --text-muted: #A1A1AA;
            --card-bg: #27272A;
            --border: #3F3F46;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Noto Sans HK', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }}

        /* TOP BAR */
        .topbar {{
            background: var(--topbar-bg);
            color: var(--topbar-text);
            padding: 0 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
            height: 64px;
        }}

        .topbar-left {{
            display: flex;
            align-items: center;
            gap: 32px;
        }}

        .topbar h1 {{
            font-family: 'Noto Serif HK', serif;
            font-size: 1.25rem;
            font-weight: 600;
        }}

        .topbar-nav {{
            display: flex;
            gap: 8px;
        }}

        .nav-btn {{
            padding: 6px 16px;
            border: 1px solid var(--topbar-muted);
            background: transparent;
            color: var(--topbar-muted);
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: all 0.2s;
        }}

        .nav-btn:hover {{
            border-color: var(--topbar-text);
            color: var(--topbar-text);
        }}

        .nav-btn.active.all {{
            background: #FAFAF8;
            border-color: #FAFAF8;
            color: #18181B;
        }}

        .nav-btn.active.tv {{
            background: var(--accent-tv);
            border-color: var(--accent-tv);
            color: white;
        }}

        .nav-btn.active.kpop {{
            background: var(--accent-kpop);
            border-color: var(--accent-kpop);
            color: white;
        }}

        .topbar-right {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}

        .stats-chip {{
            font-size: 0.8rem;
            color: var(--topbar-muted);
        }}

        .stats-chip span {{
            color: var(--topbar-text);
            font-weight: 600;
        }}

        .theme-btn {{
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1.1rem;
            padding: 4px;
        }}

        /* MAIN CONTENT */
        .main {{
            max-width: 960px;
            margin: 0 auto;
            padding: 32px;
        }}

        .page-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}

        .page-title {{
            font-family: 'Noto Serif HK', serif;
            font-size: 1.5rem;
        }}

        .platform-filter {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            padding: 6px 14px;
            border: 1px solid var(--border);
            background: transparent;
            color: var(--text-muted);
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s;
        }}

        .filter-btn:hover, .filter-btn.active.tv {{
            background: var(--accent-tv);
            border-color: var(--accent-tv);
            color: white;
        }}

        .filter-btn.active.kpop {{
            background: var(--accent-kpop);
            border-color: var(--accent-kpop);
            color: white;
        }}

        /* ARTICLE CARDS */
        .article-list {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .article-card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px 24px;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            border-left: 4px solid var(--accent-tv);
        }}

        .article-card.kpop {{
            border-left-color: var(--accent-kpop);
        }}

        .article-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        [data-theme="dark"] .article-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}

        .article-card-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}

        .content-type-badge {{
            display: inline-block;
            padding: 3px 10px;
            background: #E5E5E0;
            color: #666;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        [data-theme="dark"] .content-type-badge {{
            background: #3F3F46;
            color: #A1A1AA;
        }}

        .platform {{
            display: inline-block;
            padding: 3px 10px;
            background: var(--accent-tv);
            color: white;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
        }}

        .platform.kpop {{
            background: var(--accent-kpop);
        }}

        .article-card h3 {{
            font-family: 'Noto Serif HK', serif;
            font-size: 1.1rem;
            margin-bottom: 6px;
        }}

        .meta {{
            color: var(--text-muted);
            font-size: 0.8rem;
            margin-bottom: 8px;
        }}

        .preview {{
            color: var(--text-muted);
            font-size: 0.875rem;
            line-height: 1.6;
        }}

        .tags {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-top: 10px;
        }}

        .tag {{
            padding: 2px 8px;
            background: var(--border);
            color: var(--text-muted);
            border-radius: 4px;
            font-size: 0.7rem;
        }}

        /* MODAL */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 200;
            overflow-y: auto;
        }}

        .modal.active {{
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding: 48px;
        }}

        .modal-content {{
            background: var(--bg);
            border-radius: 16px;
            padding: 32px;
            max-width: 760px;
            width: 100%;
            position: relative;
        }}

        .modal-close {{
            position: absolute;
            top: 16px;
            right: 16px;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-muted);
        }}

        .modal h2 {{
            font-family: 'Noto Serif HK', serif;
            font-size: 1.4rem;
            margin-bottom: 8px;
        }}

        .modal .meta {{
            margin-bottom: 24px;
        }}

        .modal .content {{
            line-height: 1.8;
            font-size: 1rem;
        }}

        .modal .content h3 {{
            font-family: 'Noto Serif HK', serif;
            font-size: 1.2rem;
            margin: 24px 0 12px;
        }}

        .modal .content h4 {{
            font-family: 'Noto Serif HK', serif;
            font-size: 1.05rem;
            margin: 20px 0 8px;
        }}

        .empty-state {{
            text-align: center;
            padding: 64px;
            color: var(--text-muted);
        }}

        @media (max-width: 768px) {{
            .topbar {{ padding: 0 16px; }}
            .topbar-left {{ gap: 12px; }}
            .stats-chip {{ display: none; }}
            .main {{ padding: 16px; }}
            .page-header {{ flex-direction: column; align-items: flex-start; gap: 12px; }}
        }}
    </style>
</head>
<body>
    <header class="topbar">
        <div class="topbar-left">
            <h1>🎬 創作室</h1>
            <nav class="topbar-nav">
                <button class="nav-btn active all" onclick="filterByType('all')">📺 全部</button>
                <button class="nav-btn tv" onclick="filterByType('tv')">📺 TV</button>
                <button class="nav-btn kpop" onclick="filterByType('kpop')">🎤 K-Pop</button>
            </nav>
        </div>
        <div class="topbar-right">
            <span class="stats-chip">共 <span id="totalCount">{len(all_articles)}</span> 篇</span>
            <button class="theme-btn" onclick="toggleTheme()">🌙</button>
        </div>
    </header>

    <main class="main">
        <div class="page-header">
            <h2 class="page-title" id="pageTitle">全部內容</h2>
            <div class="platform-filter" id="platformFilter">
                <button class="filter-btn active" onclick="filterByPlatform('all')">全部</button>
                {tv_buttons}
                {kpop_buttons}
            </div>
        </div>
        <div class="article-list" id="articleList"></div>
    </main>

    <div class="modal" id="articleModal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">×</button>
            <span class="platform" id="modalPlatform"></span>
            <h2 id="modalTitle"></h2>
            <div class="meta" id="modalMeta"></div>
            <div class="content" id="modalContent"></div>
        </div>
    </div>

    <script>
        function toggleTheme() {{
            const body = document.body;
            const btn = document.querySelector('.theme-btn');
            if (body.getAttribute('data-theme') === 'dark') {{
                body.setAttribute('data-theme', 'light');
                btn.textContent = '🌙';
            }} else {{
                body.setAttribute('data-theme', 'dark');
                btn.textContent = '☀️';
            }}
        }}

        const articles = [
            {articles_js}
        ];

        let currentType = 'all';
        let currentPlatform = 'all';

        function getPlatformLabel(type, platform) {{
            if (platform === 'all') return type === 'all' ? '全部內容' : (type === 'tv' ? 'TV 評論' : 'K-Pop 內容');
            return platform;
        }}

        function renderArticles(filteredArticles) {{
            const list = document.getElementById('articleList');
            const typeLabel = currentType === 'all' ? 'mixed' : currentType;

            if (filteredArticles.length === 0) {{
                list.innerHTML = '<div class="empty-state">暫時未有文章</div>';
                return;
            }}

            list.innerHTML = filteredArticles.map(article => {{
                const isKpop = article.content_type === 'kpop';
                const badgeLabel = isKpop ? '🎤 K-Pop' : '📺 TV';
                const tagsHtml = article.tags.length > 0
                    ? `<div class="tags">${{article.tags.map(t => `<span class="tag">${{t}}</span>`).join('')}}</div>`
                    : '';
                return `
                <div class="article-card ${{isKpop ? 'kpop' : ''}}" onclick="showArticle(${{article.id}})">
                    <div class="article-card-header">
                        <span class="content-type-badge">${{badgeLabel}}</span>
                        <span class="platform ${{isKpop ? 'kpop' : ''}}">${{article.platform}}</span>
                    </div>
                    <h3>${{article.title}}</h3>
                    <div class="meta">📅 ${{article.date}}</div>
                    <p class="preview">${{article.preview}}</p>
                    ${{tagsHtml}}
                </div>
            `}}).join('');
        }}

        function filterByType(type) {{
            currentType = type;
            currentPlatform = 'all';

            document.querySelectorAll('.nav-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            document.querySelectorAll('.nav-btn').forEach(btn => {{
                if ((type === 'all' && btn.textContent.includes('全部')) ||
                    (type === 'tv' && btn.textContent.includes('TV')) ||
                    (type === 'kpop' && btn.textContent.includes('K-Pop'))) {{
                    btn.classList.add('active');
                    btn.classList.add(type === 'all' ? 'all' : type);
                }}
            }});

            updatePlatformFilters();
            applyFilter();
        }}

        function filterByPlatform(platform) {{
            currentPlatform = platform;
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active');
                if ((platform === 'all' && btn.textContent === '全部') ||
                    btn.textContent === platform) {{
                    btn.classList.add('active');
                }}
            }});
            applyFilter();
        }}

        function updatePlatformFilters() {{
            const container = document.getElementById('platformFilter');
            const availablePlatforms = [...new Set(articles
                .filter(a => currentType === 'all' || a.content_type === currentType)
                .map(a => a.platform))];

            let buttonsHtml = '<button class="filter-btn active" onclick="filterByPlatform(\\'all\\')">全部</button>';
            availablePlatforms.forEach(p => {{
                const isKpop = articles.some(a => a.platform === p && a.content_type === 'kpop');
                const extraClass = isKpop ? 'kpop' : 'tv';
                buttonsHtml += `<button class="filter-btn ${{currentPlatform === p ? 'active ' + extraClass : ''}}" onclick="filterByPlatform('${{p}}')">${{p}}</button>`;
            }});
            container.innerHTML = buttonsHtml;
        }}

        function applyFilter() {{
            let filtered = articles;
            if (currentType !== 'all') {{
                filtered = filtered.filter(a => a.content_type === currentType);
            }}
            if (currentPlatform !== 'all') {{
                filtered = filtered.filter(a => a.platform === currentPlatform);
            }}
            const title = getPlatformLabel(currentType, currentPlatform);
            document.getElementById('pageTitle').textContent = title;
            document.getElementById('totalCount').textContent = filtered.length;
            renderArticles(filtered);
        }}

        function showArticle(id) {{
            const article = articles.find(a => a.id === id);
            if (!article) return;

            const platformEl = document.getElementById('modalPlatform');
            platformEl.textContent = article.platform;
            platformEl.className = 'platform' + (article.content_type === 'kpop' ? ' kpop' : '');

            document.getElementById('modalTitle').textContent = article.title;
            document.getElementById('modalMeta').textContent = `${{article.platform}} | 📅 ${{article.date}}`;
            document.getElementById('modalContent').innerHTML = article.content;
            document.getElementById('articleModal').classList.add('active');
        }}

        function closeModal() {{
            document.getElementById('articleModal').classList.remove('active');
        }}

        document.getElementById('articleModal').addEventListener('click', (e) => {{
            if (e.target.id === 'articleModal') closeModal();
        }});

        applyFilter();
    </script>
</body>
</html>'''

    return html

def main():
    print("🎬 Generating Creation Studio Dashboard (Full Width)...")

    tv_articles = get_reviews(content_type="tv")
    print(f"   📺 Found {len(tv_articles)} TV reviews")

    kpop_articles = get_reviews(content_type="kpop")
    print(f"   🎤 Found {len(kpop_articles)} K-Pop posts")

    all_articles = tv_articles + kpop_articles
    all_articles.sort(key=lambda x: x['date'], reverse=True)

    for idx, article in enumerate(all_articles):
        article['id'] = idx + 1

    print(f"   ✅ Total: {len(all_articles)} items")

    for a in all_articles:
        type_icon = "🎤" if a['content_type'] == 'kpop' else "📺"
        print(f"   {type_icon} {a['date']} - {a['title'][:50]}")

    html = generate_html(all_articles)

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"   ✅ Written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
