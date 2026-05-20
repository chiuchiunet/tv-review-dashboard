#!/usr/bin/env python3
"""
Static Dashboard Generator - 不需要 JavaScript，直接 HTML render曬
"""

import os
import re
import html as html_module
from datetime import datetime

TV_REVIEWS_DIR = "/home/ubuntu/.openclaw/workspace-creation/tv-reviews"
KPOP_POSTS_DIR = "/home/ubuntu/.openclaw/workspace-kpop/posts"
OUTPUT_PATH = "/home/ubuntu/.openclaw/workspace-creation/web/index.html"

def clean_markdown(text):
    """Convert markdown to HTML properly"""
    lines = text.split('\n')
    result = []
    in_table = False
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        
        # Tables
        if '|' in stripped and re.match(r'^\|?[\s\-:|]+\|', stripped):
            if not in_table:
                # Table header row
                cells = [c.strip() for c in stripped.split('|') if c.strip() and c.strip() != '-']
                if cells:
                    result.append('<table class="md-table"><tr>' + ''.join([f'<th>{c}</th>' for c in cells]) + '</tr>')
                    in_table = True
            else:
                # Table data row
                cells = [c.strip() for c in stripped.split('|') if c.strip()]
                if cells:
                    result.append('<tr>' + ''.join([f'<td>{c}</td>' for c in cells]) + '</tr>')
            continue
        else:
            if in_table:
                result.append('</table>')
                in_table = False
        
        # List items
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                result.append('<ul>')
                in_list = True
            item_text = stripped[2:]
            result.append(f'<li>{item_text}</li>')
            continue
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
        
        # Headers
        if stripped.startswith('### '):
            result.append(f'<h4>{stripped[4:]}</h4>')
        elif stripped.startswith('## '):
            result.append(f'<h3>{stripped[3:]}</h3>')
        elif stripped.startswith('# '):
            result.append(f'<h2>{stripped[2:]}</h2>')
        else:
            result.append(line)
    
    if in_table:
        result.append('</table>')
    if in_list:
        result.append('</ul>')
    
    text = '\n'.join(result)
    
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    
    # Line breaks
    text = re.sub(r'\n\n+', '</p><p>', text)
    text = re.sub(r'\n', '<br>', text)
    
    # Code
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    return f'<div class="article">{text}</div>'

def get_reviews(content_type="tv"):
    dir_path = TV_REVIEWS_DIR if content_type == "tv" else KPOP_POSTS_DIR
    
    if not os.path.exists(dir_path):
        return []
    
    reviews = []
    files = sorted(os.listdir(dir_path), reverse=True)
    
    for filename in files:
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
        
        # Extract article content
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
        
        # Clean markdown
        article = clean_markdown(article)
        
        # Preview
        preview_text = re.sub('<[^>]+>', '', article)
        preview = preview_text[:120] + '...' if len(preview_text) > 120 else preview_text
        
        reviews.append({
            'title': title,
            'platform': platform,
            'content_type': content_type,
            'date': filename[:10],
            'tags': tags,
            'preview': preview,
            'article': article
        })
    
    return reviews

def generate_static_html(all_articles):
    # Sort by date - newest first
    all_articles = sorted(all_articles, key=lambda x: x['date'], reverse=True)
    
    tv_articles = [a for a in all_articles if a['content_type'] == 'tv']
    kpop_articles = [a for a in all_articles if a['content_type'] == 'kpop']
    
    cards_html = ''
    for article in all_articles:
        is_kpop = article['content_type'] == 'kpop'
        type_label = '🎤 K-Pop' if is_kpop else '📺 TV'
        tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in article['tags']])
        
        cards_html += f'''
        <details class="article-card {'kpop' if is_kpop else ''}">
            <summary>
                <span class="type-badge">{type_label}</span>
                <span class="platform">{article['platform']}</span>
                <h3>{article['title']}</h3>
                <div class="meta">📅 {article['date']}</div>
                <p class="preview">{article['preview']}</p>
            </summary>
            <div class="article-content">
                {article['article']}
                <div class="tags">{tags_html}</div>
            </div>
        </details>
        '''
    
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
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Noto Sans HK', sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 16px;
            max-width: 800px;
            margin: 0 auto;
        }}
        
        h1 {{
            font-family: 'Noto Serif HK', serif;
            font-size: 1.8rem;
            margin-bottom: 8px;
        }}
        
        .subtitle {{
            color: var(--text-muted);
            margin-bottom: 24px;
        }}
        
        .stats {{
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
            padding: 16px;
            background: #f4f4f5;
            border-radius: 8px;
        }}
        
        .stat {{
            font-size: 0.9rem;
        }}
        
        .stat strong {{
            display: block;
            font-size: 1.5rem;
        }}
        
        .article-card {{
            background: white;
            border: 1px solid #e4e4e7;
            border-radius: 12px;
            margin-bottom: 16px;
            overflow: hidden;
        }}
        
        .article-card.kpop {{
            border-left: 4px solid var(--accent-kpop);
        }}
        
        summary {{
            padding: 16px;
            cursor: pointer;
            list-style: none;
        }}
        
        summary::-webkit-details-marker {{
            display: none;
        }}
        
        summary:after {{
            content: '▼';
            float: right;
            transition: transform 0.2s;
        }}
        
        details[open] summary:after {{
            transform: rotate(180deg);
        }}
        
        .type-badge {{
            display: inline-block;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 4px;
            background: var(--accent-tv);
            color: white;
            margin-right: 8px;
        }}
        
        .kpop .type-badge {{
            background: var(--accent-kpop);
        }}
        
        .platform {{
            display: inline-block;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 4px;
            background: #f4f4f5;
            color: var(--text-muted);
            margin-left: 8px;
        }}
        
        .article-card h3 {{
            font-family: 'Noto Serif HK', serif;
            font-size: 1.1rem;
            margin: 12px 0 8px;
        }}
        
        .meta {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        
        .preview {{
            font-size: 0.9rem;
            color: var(--text-muted);
            line-height: 1.5;
        }}
        
        .article-content {{
            padding: 16px;
            border-top: 1px solid #e4e4e7;
            background: #fafafa;
            line-height: 1.7;
        }}
        
        .article-content .article {{
            margin-bottom: 12px;
        }}
        
        .article-content h2, .article-content h3, .article-content h4 {{
            margin: 16px 0 8px;
            font-family: 'Noto Serif HK', serif;
        }}
        
        .article-content ul {{
            margin: 8px 0;
            padding-left: 20px;
        }}
        
        .article-content li {{
            margin-bottom: 4px;
        }}
        
        .article-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
        }}
        
        .article-content th, .article-content td {{
            border: 1px solid #e4e4e7;
            padding: 8px;
            text-align: left;
        }}
        
        .article-content th {{
            background: #f4f4f5;
        }}
        
        .tags {{
            margin-top: 16px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        
        .tag {{
            font-size: 0.75rem;
            padding: 4px 8px;
            background: #e4e4e7;
            border-radius: 4px;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <h1>🎬 創作室 Dashboard</h1>
    <p class="subtitle">TV評論 · K-Pop內容 · {datetime.now().strftime('%Y-%m-%d')}</p>
    
    <div class="stats">
        <div class="stat">📺 TV評論 <strong>{len(tv_articles)}</strong></div>
        <div class="stat">🎤 K-Pop <strong>{len(kpop_articles)}</strong></div>
    </div>
    
    {cards_html}
</body>
</html>'''
    
    return html

def main():
    print("🎬 Generating Static Dashboard (no JS needed)...")
    
    tv_reviews = get_reviews('tv')
    kpop_reviews = get_reviews('kpop')
    all_articles = tv_reviews + kpop_reviews
    
    print(f"   📺 Found {len(tv_reviews)} TV reviews")
    print(f"   🎤 Found {len(kpop_reviews)} K-Pop posts")
    
    html = generate_static_html(all_articles)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Written to {OUTPUT_PATH}")
    print(f"   📺 {datetime.now().strftime('%Y-%m-%d')} - Latest: {all_articles[0]['title']}")

if __name__ == '__main__':
    main()