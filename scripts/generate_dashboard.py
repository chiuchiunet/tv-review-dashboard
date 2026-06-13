#!/usr/bin/env python3
"""
創作室 Dashboard Generator
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
    
    Args:
        content_type: "tv" for TV reviews, "kpop" for K-Pop posts
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
        
        # Frontmatter extraction
        lines = content.split('\n')
        title = filename.replace('.md', '').replace('2026-03-19-', '')
        platform = 'TVB' if content_type == "tv" else 'K-Pop'
        tags = []
        
        for line in lines[:15]:  # Check first 15 lines for frontmatter
            if line.startswith('title:'):
                title = line.split('title:')[1].strip().strip('"').strip("'")
            elif line.startswith('platform:'):
                platform = line.split('platform:')[1].strip()
            elif line.startswith('artist:'):
                # For K-Pop posts, use artist as secondary info
                platform = line.split('artist:')[1].strip()
            elif line.startswith('tags:'):
                tags_str = line.split('tags:')[1].strip()
                tags = re.findall(r'\[([^\]]+)\]', tags_str)
        
        # Find ## 文章 section or first major content section
        article_match = re.search(r'##\s*文章\s*\n+(.+?)(?=^##\s|\Z)', content, re.MULTILINE | re.DOTALL)
        
        if article_match:
            article = article_match.group(1).strip()
        else:
            # Fallback: skip frontmatter and headers
            article = content
            if article.startswith('---'):
                parts = article.split('---', 2)
                if len(parts) >= 3:
                    article = parts[2]
            article = re.sub(r'^# .+\n', '', article, flags=re.MULTILINE)
            article = re.sub(r'^## .+\n', '', article, flags=re.MULTILINE)
            article = article.strip()
        
        # Clean article - convert markdown to HTML-ish
        article = article.replace('\n\n', '</p><p>')
        article = f'<p>{article}</p>'
        article = re.sub(r'### (.+)', r'<h4>\1</h4>', article)
        article = re.sub(r'## (.+)', r'<h3>\1</h3>', article)
        
        # Preview - first 120 chars
        preview_text = re.sub('<[^>]+>', '', article)
        preview = preview_text[:120] + '...' if len(preview_text) > 120 else preview_text
        
        # Extract date from filename or frontmatter
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
    """Escape text for JavaScript string"""
    if not text:
        return ""
    return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')

def escape_js_template(text):
    """Escape text for JavaScript template literal"""
    if not text:
        return ""
    return text.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')

def generate_article_js(review, idx, offset):
    """Generate article object for JS"""
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
    """Generate the full HTML dashboard"""
    
    # Separate TV and KPop counts
    tv_articles = [a for a in all_articles if a['content_type'] == 'tv']
    kpop_articles = [a for a in all_articles if a['content_type'] == 'kpop']
    
    # Generate article JS - need unique IDs across both
    articles_js_parts = []
    for idx, article in enumerate(all_articles):
        articles_js_parts.append(generate_article_js(article, idx, 0))
    articles_js = ',\n            '.join(articles_js_parts)
    
    # Get unique platforms for filter buttons
    tv_platforms = sorted(list(set([a['platform'] for a in tv_articles])))
    kpop_platforms = sorted(list(set([a['platform'] for a in kpop_articles])))
    
    # Platform filter buttons HTML
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
            --sidebar-bg: #18181B;
            --sidebar-text: #FAFAF8;
            --sidebar-text-muted: #A1A1AA;
            --main-bg-light: #FAFAF8;
            --main-text-light: #18181B;
            --main-text-muted-light: #71717A;
            --main-bg-dark: #18181B;
            --main-text-dark: #FAFAF8;
            --main-text-muted-dark: #A1A1AA;
            --accent-tv: #DC2626;
            --accent-kpop: #8B5CF6;
            --accent-hover: #B91C1C;
            --bg-main: var(--main-bg-light);
            --text-main: var(--main-text-light);
            --text-muted: var(--main-text-muted-light);
            --font-heading: 'Noto Serif HK', serif;
            --font-body: 'Noto Sans HK', sans-serif;
        }}
        
        [data-theme="dark"] {{
            --bg-main: var(--main-bg-dark);
            --text-main: var(--main-text-dark);
            --text-muted: var(--main-text-muted-dark);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: var(--font-body);
            background: var(--bg-main);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            transition: background 0.3s, color 0.3s;
        }}
        
        .sidebar {{
            width: 280px;
            background: var(--sidebar-bg);
            padding: 24px;
            display: flex;
            flex-direction: column;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
        }}
        
        .sidebar h1 {{
            font-family: var(--font-heading);
            color: var(--sidebar-text);
            font-size: 1.5rem;
            margin-bottom: 8px;
        }}
        
        .sidebar .subtitle {{
            color: var(--sidebar-text-muted);
            font-size: 0.875rem;
            margin-bottom: 32px;
        }}
        
        .content-type-filter {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
        }}
        
        .type-btn {{
            flex: 1;
            padding: 12px 8px;
            border: 2px solid var(--sidebar-text-muted);
            background: transparent;
            color: var(--sidebar-text-muted);
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            transition: all 0.2s;
        }}
        
        .type-btn:hover {{
            border-color: var(--sidebar-text);
            color: var(--sidebar-text);
        }}
        
        .type-btn.active.tv {{
            background: var(--accent-tv);
            border-color: var(--accent-tv);
            color: white;
        }}
        
        .type-btn.active.kpop {{
            background: var(--accent-kpop);
            border-color: var(--accent-kpop);
            color: white;
        }}
        
        .platform-filter {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }}
        
        .filter-section-label {{
            color: var(--sidebar-text-muted);
            font-size: 0.75rem;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            border: 1px solid var(--sidebar-text-muted);
            background: transparent;
            color: var(--sidebar-text-muted);
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: all 0.2s;
        }}
        
        .filter-btn:hover, .filter-btn.active {{
            background: var(--accent-tv);
            border-color: var(--accent-tv);
            color: white;
        }}
        
        [data-type="kpop"] .filter-btn:hover, 
        [data-type="kpop"] .filter-btn.active {{
            background: var(--accent-kpop);
            border-color: var(--accent-kpop);
        }}
        
        .stats {{
            margin-top: auto;
            padding-top: 24px;
            border-top: 1px solid #3F3F46;
        }}
        
        .stats-item {{
            display: flex;
            justify-content: space-between;
            color: var(--sidebar-text-muted);
            font-size: 0.875rem;
            margin-bottom: 8px;
        }}
        
        .stats-item .count {{
            font-weight: 600;
            color: var(--sidebar-text);
        }}
        
        .main {{
            margin-left: 280px;
            flex: 1;
            padding: 32px 48px;
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
        }}
        
        .header h2 {{
            font-family: var(--font-heading);
            font-size: 1.75rem;
        }}
        
        .theme-toggle {{
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1.25rem;
            padding: 8px;
        }}
        
        .article-list {{
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}
        
        .article-card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            border-left: 4px solid var(--accent-tv);
        }}
        
        [data-theme="dark"] .article-card {{
            background: #27272A;
            box-shadow: none;
        }}
        
        .article-card.kpop {{
            border-left-color: var(--accent-kpop);
        }}
        
        .article-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .platform {{
            display: inline-block;
            padding: 4px 12px;
            background: var(--accent-tv);
            color: white;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 12px;
            margin-right: 8px;
        }}
        
        .platform.kpop {{
            background: var(--accent-kpop);
        }}
        
        .content-type-badge {{
            display: inline-block;
            padding: 4px 12px;
            background: #E5E5E0;
            color: #666;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        [data-theme="dark"] .content-type-badge {{
            background: #3F3F46;
            color: #A1A1AA;
        }}
        
        .article-card h3 {{
            font-family: var(--font-heading);
            font-size: 1.25rem;
            margin-bottom: 8px;
        }}
        
        .meta {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 12px;
        }}
        
        .preview {{
            color: var(--text-muted);
            font-size: 0.9rem;
            line-height: 1.6;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            overflow-y: auto;
        }}
        
        .modal.active {{
            display: flex;
            align-items: flex-start;
            justify-content: center;
            padding: 48px;
        }}
        
        .modal-content {{
            background: var(--bg-main);
            border-radius: 16px;
            padding: 32px;
            max-width: 800px;
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
            font-family: var(--font-heading);
            font-size: 1.5rem;
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
            font-family: var(--font-heading);
            font-size: 1.25rem;
            margin: 24px 0 12px;
        }}
        
        .modal .content h4 {{
            font-family: var(--font-heading);
            font-size: 1.1rem;
            margin: 20px 0 8px;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 48px;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <aside class="sidebar">
        <h1>🎬 創作室</h1>
        <p class="subtitle">TV評論 · K-Pop內容 · {datetime.now().strftime('%Y-%m-%d')}</p>
        
        <div class="content-type-filter">
            <button class="type-btn tv active" onclick="filterByType('all')">📺 全部</button>
            <button class="type-btn tv" onclick="filterByType('tv')">📺 TV</button>
            <button class="type-btn kpop" onclick="filterByType('kpop')">🎤 K-Pop</button>
        </div>
        
        <div class="platform-filter" id="platformFilter">
            <button class="filter-btn active" onclick="filterByPlatform('all')">全部</button>
            {tv_buttons}
            {kpop_buttons}
        </div>
        
        <div class="stats">
            <div class="stats-item">
                <span>總內容數</span>
                <span class="count" id="totalCount">{len(all_articles)}</span>
            </div>
            <div class="stats-item">
                <span>📺 TV 評論</span>
                <span class="count">{len(tv_articles)}</span>
            </div>
            <div class="stats-item">
                <span>🎤 K-Pop</span>
                <span class="count">{len(kpop_articles)}</span>
            </div>
        </div>
    </aside>
    
    <main class="main" id="mainContent">
        <div class="header">
            <h2 id="pageTitle">全部內容</h2>
            <button class="theme-toggle" onclick="toggleTheme()">🌙</button>
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
        // Theme toggle
        function toggleTheme() {{
            const body = document.body;
            const btn = document.querySelector('.theme-toggle');
            if (body.getAttribute('data-theme') === 'dark') {{
                body.setAttribute('data-theme', 'light');
                btn.textContent = '🌙';
            }} else {{
                body.setAttribute('data-theme', 'dark');
                btn.textContent = '☀️';
            }}
        }}
        
        // Articles data
        const articles = [
            {articles_js}
        ];
        
        let currentType = 'all';
        let currentPlatform = 'all';
        
        // Get platform text for display
        function getPlatformLabel(type, platform) {{
            if (platform === 'all') return type === 'all' ? '全部內容' : (type === 'tv' ? 'TV 評論' : 'K-Pop 內容');
            return platform;
        }}
        
        // Render articles
        function renderArticles(filteredArticles) {{
            const list = document.getElementById('articleList');
            const main = document.getElementById('mainContent');
            
            // Update body attribute for styling
            main.setAttribute('data-type', currentType === 'all' ? 'mixed' : currentType);
            
            if (filteredArticles.length === 0) {{
                list.innerHTML = '<div class="empty-state">暫時未有文章</div>';
                return;
            }}
            
            list.innerHTML = filteredArticles.map(article => {{
                const isKpop = article.content_type === 'kpop';
                const typeLabel = isKpop ? '🎤 K-Pop' : '📺 TV';
                return `
                <div class="article-card ${{isKpop ? 'kpop' : ''}}" onclick="showArticle(${{article.id}})">
                    <span class="content-type-badge">${{typeLabel}}</span>
                    <span class="platform ${{isKpop ? 'kpop' : ''}}">${{article.platform}}</span>
                    <h3>${{article.title}}</h3>
                    <div class="meta">📅 ${{article.date}}</div>
                    <p class="preview">${{article.preview}}</p>
                </div>
            `}}).join('');
        }}
        
        // Filter by content type
        function filterByType(type) {{
            currentType = type;
            currentPlatform = 'all';
            
            // Update type buttons
            document.querySelectorAll('.type-btn').forEach(btn => {{
                btn.classList.remove('active');
                if ((type === 'all' && btn.textContent.includes('全部')) ||
                    (type === 'tv' && btn.textContent.includes('TV')) ||
                    (type === 'kpop' && btn.textContent.includes('K-Pop'))) {{
                    btn.classList.add('active');
                }}
            }});
            
            // Update platform buttons
            updatePlatformFilters();
            
            // Apply filter
            applyFilter();
        }}
        
        // Filter by platform
        function filterByPlatform(platform) {{
            currentPlatform = platform;
            
            // Update platform buttons
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active');
                if ((platform === 'all' && btn.textContent === '全部') ||
                    btn.textContent === platform) {{
                    btn.classList.add('active');
                }}
            }});
            
            applyFilter();
        }}
        
        // Update platform filter buttons based on current type
        function updatePlatformFilters() {{
            const container = document.getElementById('platformFilter');
            const availablePlatforms = [...new Set(articles
                .filter(a => currentType === 'all' || a.content_type === currentType)
                .map(a => a.platform))];
            
            let buttonsHtml = '<button class="filter-btn active" onclick="filterByPlatform(\\'all\\')">全部</button>';
            availablePlatforms.forEach(p => {{
                buttonsHtml += '<button class="filter-btn" onclick="filterByPlatform(\'' + p + '\')">' + p + '<\/button>';
            }});
            container.innerHTML = buttonsHtml;
        }}
        
        // Apply current filters
        function applyFilter() {{
            let filtered = articles;
            
            // Filter by type
            if (currentType !== 'all') {{
                filtered = filtered.filter(a => a.content_type === currentType);
            }}
            
            // Filter by platform
            if (currentPlatform !== 'all') {{
                filtered = filtered.filter(a => a.platform === currentPlatform);
            }}
            
            // Update title
            const title = getPlatformLabel(currentType, currentPlatform);
            document.getElementById('pageTitle').textContent = title;
            
            renderArticles(filtered);
        }}
        
        // Show article modal
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
        
        // Close modal
        function closeModal() {{
            document.getElementById('articleModal').classList.remove('active');
        }}
        
        // Close modal on outside click
        document.getElementById('articleModal').addEventListener('click', (e) => {{
            if (e.target.id === 'articleModal') closeModal();
        }});
        
        // Initial render
        applyFilter();
    </script>
</body>
</html>'''
    
    return html

def main():
    print("🎬 Generating Creation Studio Dashboard...")
    
    # Get TV reviews
    tv_articles = get_reviews(content_type="tv")
    print(f"   📺 Found {len(tv_articles)} TV reviews")
    
    # Get K-Pop posts
    kpop_articles = get_reviews(content_type="kpop")
    print(f"   🎤 Found {len(kpop_articles)} K-Pop posts")
    
    # Combine and sort by date (newest first)
    all_articles = tv_articles + kpop_articles
    all_articles.sort(key=lambda x: x['date'], reverse=True)
    
    # Re-assign sequential IDs after sorting
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
