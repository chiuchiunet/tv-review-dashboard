#!/usr/bin/env python3
"""
TV Review Dashboard Generator
直接從 md file 讀取評論內容，generate HTML dashboard
"""

import os
import re
from datetime import datetime

TV_REVIEWS_DIR = "/home/ubuntu/.openclaw/workspace-creation/tv-reviews"
OUTPUT_PATH = "/home/ubuntu/.openclaw/workspace-creation/web/index.html"

def get_reviews():
    """從 md files 讀取評論"""
    reviews = []
    files = sorted(os.listdir(TV_REVIEWS_DIR), reverse=True)
    
    for i, filename in enumerate(files, 1):
        if not filename.endswith('.md'):
            continue
            
        filepath = os.path.join(TV_REVIEWS_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frontmatter
        title = ""
        platform = ""
        
        # Parse frontmatter
        lines = content.split('\n')
        in_frontmatter = False
        frontmatter = {}
        body_start = 0
        
        for j, line in enumerate(lines):
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    body_start = j + 1
                continue
            if in_frontmatter and ':' in line:
                key, val = line.split(':', 1)
                frontmatter[key.strip()] = val.strip()
        
        title = frontmatter.get('title', filename.replace('.md', ''))
        platform = frontmatter.get('platform', 'TVB')
        
        # Extract article body (after ## 文章 or first heading)
        body = '\n'.join(lines[body_start:])
        
        # Find article section
        article_match = re.search(r'##\s*文章\s*\n+(.+?)(?=##|\Z)', body, re.DOTALL)
        if article_match:
            article = article_match.group(1).strip()
        else:
            # If no ## 文章, use whole body minus headers
            article = re.sub(r'^#.+\n', '', body, flags=re.MULTILINE).strip()
        
        # Clean article - convert markdown to HTML-ish
        article = article.replace('\n\n', '</p><p>')
        article = f'<p>{article}</p>'
        article = re.sub(r'### (.+)', r'<h4>\1</h4>', article)
        article = re.sub(r'## (.+)', r'<h3>\1</h3>', article)
        
        # Preview - first 120 chars
        preview_text = re.sub('<[^>]+>', '', article)  # strip HTML
        preview = preview_text[:120] + '...' if len(preview_text) > 120 else preview_text
        
        # Extract date from filename
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', filename)
        date = date_match.group(1) if date_match else '2026-03-19'
        
        reviews.append({
            'id': i,
            'title': title,
            'platform': platform,
            'date': date,
            'focus': frontmatter.get('tags', ''),
            'preview': preview,
            'article': article
        })
    
    return reviews

def escape_js(text):
    """Escape text for JavaScript string"""
    return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '')

def generate_article_html(review):
    """Generate article object for JS"""
    return f"""{{
                id: {review['id']},
                title: "{escape_js(review['title'])}",
                platform: "{escape_js(review['platform'])}",
                date: "{review['date']}",
                focus: "{escape_js(review['focus'])}",
                preview: "{escape_js(review['preview'])}",
                content: `{review['article']} `
            }}"""

def generate_html(articles):
    articles_js = ',\n            '.join([generate_article_html(a) for a in articles])
    
    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TV 評論創作室</title>
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
            --accent: #DC2626;
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
        
        .platform-filter {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 24px;
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
            background: var(--accent);
            border-color: var(--accent);
            color: white;
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
        }}
        
        [data-theme="dark"] .article-card {{
            background: #27272A;
            box-shadow: none;
        }}
        
        .article-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .platform {{
            display: inline-block;
            padding: 4px 12px;
            background: var(--accent);
            color: white;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 12px;
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
        <h1>📺 TV 評論創作室</h1>
        <p class="subtitle">電視劇評分析 · {datetime.now().strftime('%Y-%m-%d')}</p>
        
        <div class="platform-filter">
            <button class="filter-btn active" onclick="filterByPlatform('all')">全部</button>
            <button class="filter-btn" onclick="filterByPlatform('TVB')">TVB</button>
            <button class="filter-btn" onclick="filterByPlatform('ViuTV')">ViuTV</button>
        </div>
        
        <div class="stats">
            <div class="stats-item">
                <span>總評論數</span>
                <span id="totalCount">{len(articles)}</span>
            </div>
            <div class="stats-item">
                <span>TVB</span>
                <span id="tvbCount">{len([a for a in articles if a['platform'] == 'TVB'])}</span>
            </div>
            <div class="stats-item">
                <span>ViuTV</span>
                <span id="viutvCount">{len([a for a in articles if a['platform'] == 'ViuTV'])}</span>
            </div>
        </div>
    </aside>
    
    <main class="main">
        <div class="header">
            <h2>全部評論</h2>
            <button class="theme-toggle" onclick="toggleTheme()">🌙</button>
        </div>
        
        <div class="article-list" id="articleList"></div>
    </main>
    
    <div class="modal" id="articleModal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">×</button>
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
        
        // Render articles
        function renderArticles(filteredArticles) {{
            const list = document.getElementById('articleList');
            
            if (filteredArticles.length === 0) {{
                list.innerHTML = '<div class="empty-state">暫時未有文章</div>';
                return;
            }}
            
            list.innerHTML = filteredArticles.map(article => `
                <div class="article-card" onclick="showArticle(${{article.id}})">
                    <span class="platform">${{article.platform}}</span>
                    <h3>${{article.title}}</h3>
                    <div class="meta">📅 ${{article.date}}</div>
                    <p class="preview">${{article.preview}}</p>
                </div>
            `).join('');
        }}
        
        // Filter by platform
        function filterByPlatform(platform) {{
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active');
                if (btn.textContent.includes(platform) || (platform === 'all' && btn.textContent === '全部')) {{
                    btn.classList.add('active');
                }}
            }});
            
            if (platform === 'all') {{
                renderArticles(articles);
            }} else {{
                renderArticles(articles.filter(a => a.platform === platform));
            }}
        }}
        
        // Show article modal
        function showArticle(id) {{
            const article = articles.find(a => a.id === id);
            if (!article) return;
            
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
        renderArticles(articles);
    </script>
</body>
</html>'''
    
    return html

def main():
    print("📺 Generating TV Review Dashboard...")
    articles = get_reviews()
    print(f"   Found {len(articles)} reviews")
    
    html = generate_html(articles)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"   ✅ Written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
