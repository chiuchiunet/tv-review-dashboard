#!/usr/bin/env python3
"""
創作室 Dashboard Generator — Full Width (No Sidebar)
支援 TV 評論 + K-Pop 內容 dual-source
"""

import json
import os
import re
from collections import OrderedDict
from datetime import datetime

TV_REVIEWS_DIR = "/home/ubuntu/.openclaw/workspace-creation/tv-reviews"
KPOP_POSTS_DIR = "/home/ubuntu/.openclaw/workspace-kpop/posts"
OUTPUT_PATH = "/home/ubuntu/.openclaw/workspace-creation/web/index.html"

# GitHub repo that hosts the TV reviews. K-Pop posts live in a separate repo
# that is NOT public, so kpop articles only expose `sourcePath`.
GITHUB_BLOB_BASE = "https://github.com/chiuchiunet/tv-review-dashboard/blob/main"

CONTENT_TYPE_LABELS = {
    'tv': '電視劇',
    'kpop': 'K-Pop',
}

# Single source of truth for platform ids + display labels.
# Ordered so filter chips / KPI legends render in a stable, deliberate order.
PLATFORMS = OrderedDict([
    ('netflix', 'Netflix'),
    ('disney_plus', 'Disney+'),
    ('viutv', 'ViuTV'),
    ('tvb', 'TVB'),
    ('hoy_tv', 'HOY TV'),
    ('wetv', 'WeTV'),
    ('youtube', 'YouTube'),
    ('spotify', 'Spotify'),
    ('apple_music', 'Apple Music'),
    ('threads', 'Threads'),
    ('twitter', 'Twitter'),
    ('instagram', 'Instagram'),
    ('tiktok', 'TikTok'),
    ('iqiyi', '優酷'),
    ('tvb_plus', 'TVB Plus'),
    ('mbc', 'MBC'),
])

# Lowercased label -> canonical id, for case-insensitive lookup of PLATFORMS labels.
_PLATFORM_BY_LABEL = OrderedDict(
    (label.lower(), pid) for pid, label in PLATFORMS.items()
)

# Extra spellings that appear in the raw frontmatter.
PLATFORM_ALIASES = {
    'tvb+': 'tvb_plus',
    'tvb plus': 'tvb_plus',
    'disney+': 'disney_plus',
    'disney plus': 'disney_plus',
    'hoy tv': 'hoy_tv',
    'hoytv': 'hoy_tv',
    'wetv': 'wetv',
    'we tv': 'wetv',
    'viutv': 'viutv',
    'viu tv': 'viutv',
    'apple music': 'apple_music',
    'applemusic': 'apple_music',
    'ig': 'instagram',
    'x': 'twitter',
    '優酷': 'iqiyi',
    'youku': 'iqiyi',
    'iqiyi': 'iqiyi',
    'mbc': 'mbc',
}

# Single source of truth for status ids -> display label + accent colour class.
# `review` and `scheduled` intentionally share the 「待發布」 label because the
# KPI card treats them as one "pending" bucket.
STATUS_CONFIG = OrderedDict([
    ('draft', {'label': '草稿', 'accent': 'status-draft'}),
    ('review', {'label': '待發布', 'accent': 'status-pending'}),
    ('scheduled', {'label': '待發布', 'accent': 'status-pending'}),
    ('published', {'label': '已發布', 'accent': 'status-published'}),
    ('archived', {'label': '封存', 'accent': 'status-archived'}),
])

DEFAULT_STATUS = 'draft'
DEFAULT_PLATFORM_SEPARATOR = re.compile(r'[|/,]')


def platform_label(platform_id):
    """Display label for a canonical platform id ('' when unknown)."""
    return PLATFORMS.get(platform_id, '')


def parse_platforms(raw):
    """Raw `platform:` string -> ordered, deduped list of canonical platform ids.

    Splits on `|`, `/` and `,`. The literal token `ALL` means "all channels" and
    is dropped. Unknown tokens are dropped silently, never raising.
    """
    if not raw:
        return []

    tokens = [t.strip() for t in DEFAULT_PLATFORM_SEPARATOR.split(str(raw))]
    result = []

    for token in tokens:
        if not token:
            continue

        # "ALL" means every channel, not a platform of its own.
        if token.upper() == 'ALL':
            continue

        key = token.lower().strip()
        pid = _PLATFORM_BY_LABEL.get(key) or PLATFORM_ALIASES.get(key)

        if pid and pid not in result:
            result.append(pid)

    return result


def parse_status(raw):
    """Raw `status:` frontmatter value -> canonical status id (never raises)."""
    if not raw:
        return DEFAULT_STATUS

    key = str(raw).strip().strip('"').strip("'").lower()

    return key if key in STATUS_CONFIG else DEFAULT_STATUS


def _split_frontmatter(content):
    """Return (frontmatter_text, body_text) for a leading `---` block.

    Only the block between the leading `---` and the next `---` is treated as
    frontmatter; anything else is returned as body with frontmatter_text = ''.
    """
    if not content.startswith('---'):
        return '', content

    match = re.match(r'^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)',
                     content, re.DOTALL)
    if not match:
        return '', content

    return match.group(1), content[match.end():]


def _parse_frontmatter(frontmatter_text):
    """Parse the scalar keys we care about out of a frontmatter block."""
    fm = {}

    if not frontmatter_text:
        return fm

    for line in frontmatter_text.split('\n'):
        line = line.rstrip('\r')
        if not line.strip() or line.lstrip().startswith('#'):
            continue

        match = re.match(r'^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$', line)
        if not match:
            continue

        key = match.group(1).lower()
        value = match.group(2).strip()
        # Strip inline comments and surrounding quotes.
        value = re.sub(r'\s+#.*$', '', value).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        fm[key] = value

    return fm


def _extract_article_html(content):
    """Extract + lightly format the article body. Logic preserved from before."""
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

    return article


def _make_preview(article_html):
    preview_text = re.sub('<[^>]+>', '', article_html)
    return preview_text[:120] + '...' if len(preview_text) > 120 else preview_text


def _resolve_date(fm, filename):
    """Frontmatter `date:` -> filename date prefix -> today."""
    raw = fm.get('date', '')
    if raw:
        m = re.search(r'(\d{4}-\d{2}-\d{2})', raw)
        if m:
            return m.group(1)

    m = re.match(r'(\d{4}-\d{2}-\d{2})', filename)
    if m:
        return m.group(1)

    return datetime.now().strftime('%Y-%m-%d')


def _file_updated_date(filepath):
    """File mtime as YYYY-MM-DD, used for 「最近更新」 sorting."""
    try:
        return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d')
    except (OSError, ValueError):
        return ''


def _source_url(content_type, filename):
    """GitHub blob link for TV articles; K-Pop lives outside the public repo."""
    if content_type == 'tv':
        return f'{GITHUB_BLOB_BASE}/tv-reviews/{filename}'
    return ''


def build_article(raw_dict):
    """Normalize one parsed source file into the canonical article dict."""
    content_type = raw_dict.get('content_type', 'tv')
    filename = raw_dict.get('filename', '')
    filepath = raw_dict.get('filepath', '')
    content = raw_dict.get('content', '')

    fm_text, body = _split_frontmatter(content)
    fm = _parse_frontmatter(fm_text)

    # Title: frontmatter first, then the filename-derived fallback.
    title = fm.get('title') or filename.replace('.md', '').replace('2026-03-19-', '')

    # NOTE: `artist` is its own field and must never overwrite `platform`.
    artist = fm.get('artist', '') or ''
    album = fm.get('album', '') or ''
    release_date = fm.get('release_date', '') or ''
    cover = fm.get('cover', '') or ''

    raw_platform = fm.get('platform', '') or ''
    platforms = parse_platforms(raw_platform)
    platform_labels = [platform_label(p) for p in platforms]
    platform_summary = ', '.join(platform_labels) if platform_labels else raw_platform

    tags_str = fm.get('tags', '')
    tags = re.findall(r'\[([^\]]+)\]', tags_str) if tags_str else []

    status = parse_status(fm.get('status'))

    article_html = _extract_article_html(content)
    preview = _make_preview(article_html)

    return {
        'id': raw_dict.get('id', 0),
        'title': title,
        'content_type': content_type,
        'contentType': content_type,
        'contentTypeLabel': CONTENT_TYPE_LABELS.get(content_type, content_type),
        'date': _resolve_date(fm, filename),
        'created': _resolve_date(fm, filename),
        'updated': _file_updated_date(filepath),
        'status': status,
        'statusLabel': STATUS_CONFIG[status]['label'],
        'platforms': platforms,
        'platformLabels': platform_labels,
        'platform': platform_summary,
        'artist': artist,
        'album': album,
        'release_date': release_date,
        'tags': tags,
        'preview': preview,
        'article': article_html,
        'cover': cover,
        'sourcePath': filepath,
        'sourceUrl': _source_url(content_type, filename),
    }


def summary_counts(all_articles):
    """Counts for the KPI cards; `pending` combines review + scheduled."""
    counts = {
        'total': len(all_articles),
        'draft': 0,
        'review': 0,
        'scheduled': 0,
        'published': 0,
        'archived': 0,
    }

    for article in all_articles:
        status = article.get('status', DEFAULT_STATUS)
        if status in counts:
            counts[status] += 1

    counts['pending'] = counts['review'] + counts['scheduled']

    return counts


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

        reviews.append(build_article({
            'id': i,
            'filename': filename,
            'filepath': filepath,
            'content': content,
            'content_type': content_type,
        }))

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
    """Emit one article as a JS object literal using json.dumps for safe escaping."""
    return json.dumps({
        'id': idx + offset,
        'title': review.get('title', ''),
        'contentType': review.get('contentType', review.get('content_type', '')),
        'contentTypeLabel': review.get('contentTypeLabel', ''),
        'content_type': review.get('content_type', ''),
        'date': review.get('date', ''),
        'created': review.get('created', ''),
        'updated': review.get('updated', ''),
        'status': review.get('status', DEFAULT_STATUS),
        'statusLabel': review.get('statusLabel', ''),
        'platforms': review.get('platforms', []),
        'platformLabels': review.get('platformLabels', []),
        'platform': review.get('platform', ''),
        'artist': review.get('artist', ''),
        'tags': review.get('tags', []),
        'preview': review.get('preview', ''),
        'content': review.get('article', ''),
        'cover': review.get('cover', ''),
        'sourcePath': review.get('sourcePath', ''),
        'sourceUrl': review.get('sourceUrl', ''),
    }, ensure_ascii=False)

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-HK" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light dark">
    <title>🎬 創作室 Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+HK:wght@300;400;500;600;700&family=Noto+Serif+HK:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* ---------- Theme tokens ---------- */
        :root {
            --bg: #FFFFFF;
            --bg-subtle: #FAFAF9;
            --text: #18181B;
            --text-muted: #52525B;
            --border: #E4E4E7;
            --border-strong: #A1A1AA;
            --card-bg: #FFFFFF;
            --accent: #1D4ED8;
            --accent-text: #1E40AF;
            --accent-soft: #EFF6FF;
            --accent-border: #93C5FD;
            --chip-bg: #FAFAF9;
            --chip-text: #3F3F46;
            --chip-active-bg: #1D4ED8;
            --chip-active-text: #FFFFFF;
            --badge-bg: #F4F4F5;
            --badge-text: #3F3F46;
            --topbar-bg: #18181B;
            --topbar-text: #FAFAF8;
            --topbar-muted: #D4D4D8;
            --danger: #B91C1C;
            --shadow: 0 1px 2px rgba(24, 24, 27, .08);
            --shadow-lg: 0 12px 32px rgba(24, 24, 27, .18);
            --radius: .75rem;
        }

        [data-theme="dark"] {
            --bg: #18181B;
            --bg-subtle: #27272A;
            --text: #FAFAF8;
            --text-muted: #A1A1AA;
            --border: #3F3F46;
            --border-strong: #71717A;
            --card-bg: #27272A;
            --accent: #93C5FD;
            --accent-text: #BFDBFE;
            --accent-soft: #1E293B;
            --accent-border: #1D4ED8;
            --chip-bg: #27272A;
            --chip-text: #E4E4E7;
            --chip-active-bg: #93C5FD;
            --chip-active-text: #18181B;
            --badge-bg: #3F3F46;
            --badge-text: #E4E4E7;
            --topbar-bg: #09090B;
            --topbar-text: #FAFAF8;
            --topbar-muted: #D4D4D8;
            --danger: #FCA5A5;
            --shadow: 0 1px 2px rgba(0, 0, 0, .5);
            --shadow-lg: 0 12px 32px rgba(0, 0, 0, .6);
            --radius: .75rem;
        }

        /* ---------- Base ---------- */
        *, *::before, *::after { box-sizing: border-box; }

        html, body {
            max-width: 100%;
            overflow-x: hidden;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Noto Sans HK', 'Noto Sans TC', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            font-size: 1rem;
            min-height: 100vh;
        }

        img { max-width: 100%; height: auto; display: block; }

        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }

        a { color: var(--accent-text); }

        :focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
            border-radius: .25rem;
        }

        /* ---------- Topbar ---------- */
        .topbar {
            background: var(--topbar-bg);
            color: var(--topbar-text);
            padding: .75rem 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .topbar h1 {
            font-family: 'Noto Serif HK', serif;
            font-size: 1.25rem;
            margin: 0;
            font-weight: 700;
        }

        .topbar-muted {
            color: var(--topbar-muted);
            font-size: .875rem;
            margin: 0;
        }

        .theme-btn {
            background: transparent;
            color: var(--topbar-text);
            border: 1px solid var(--border-strong);
            border-radius: .5rem;
            min-width: 2.75rem;
            min-height: 2.75rem;
            font-size: 1.125rem;
            cursor: pointer;
        }

        /* ---------- Layout ---------- */
        .main {
            max-width: 90rem;
            margin: 0 auto;
            padding: 1.5rem 1rem 4rem;
        }

        .page-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
            margin-bottom: 1.5rem;
        }

        .page-subtitle {
            color: var(--text-muted);
            margin: 0 0 .5rem;
            font-size: 1rem;
        }

        .total-chip {
            display: inline-block;
            background: var(--badge-bg);
            color: var(--badge-text);
            border-radius: 999px;
            padding: .25rem .75rem;
            font-size: .875rem;
            font-weight: 500;
        }

        /* ---------- Buttons ---------- */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: .5rem;
            min-height: 2.75rem;
            padding: .5rem 1rem;
            border-radius: .5rem;
            border: 1px solid var(--border-strong);
            background: var(--card-bg);
            color: var(--text);
            font: inherit;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
        }

        .btn-primary {
            background: var(--accent);
            border-color: var(--accent);
            color: var(--chip-active-text);
        }

        .btn-ghost {
            background: transparent;
            border-color: var(--border);
        }

        /* ---------- Menu (新增文章) ---------- */
        .menu-wrap { position: relative; }

        .menu {
            position: absolute;
            right: 0;
            top: calc(100% + .5rem);
            z-index: 40;
            min-width: 14rem;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow-lg);
            padding: .375rem;
            display: flex;
            flex-direction: column;
        }

        .menu[hidden] { display: none; }

        .menu-item {
            display: block;
            padding: .625rem .75rem;
            border-radius: .5rem;
            color: var(--text);
            text-decoration: none;
            background: transparent;
            border: 0;
            font: inherit;
            text-align: start;
            cursor: pointer;
        }

        .menu-item:hover { background: var(--accent-soft); color: var(--accent-text); }

        /* ---------- KPI cards ---------- */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: .75rem;
            margin-bottom: 1.5rem;
        }

        .kpi-card {
            display: flex;
            flex-direction: column;
            gap: .25rem;
            padding: 1rem;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            cursor: pointer;
            font: inherit;
            color: var(--text);
            text-align: start;
            min-width: 0;
            position: relative;
        }

        .kpi-card:hover { border-color: var(--accent-border); }

        .kpi-card.active {
            border-color: var(--accent);
            background: var(--accent-soft);
            box-shadow: inset 0 0 0 1px var(--accent);
        }

        .kpi-value {
            font-size: 1.75rem;
            font-weight: 700;
            line-height: 1.2;
        }

        .kpi-label {
            color: var(--text-muted);
            font-size: .875rem;
        }

        .kpi-check {
            position: absolute;
            top: .5rem;
            inset-inline-end: .625rem;
            font-weight: 700;
            color: var(--accent-text);
        }

        .kpi-card:not(.active) .kpi-check { visibility: hidden; }

        /* ---------- Filter bar ---------- */
        .filter-bar {
            display: flex;
            flex-direction: column;
            gap: .75rem;
            background: var(--bg-subtle);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1rem;
            margin-bottom: 1rem;
        }

        .filter-group {
            display: flex;
            align-items: center;
            gap: .5rem;
            min-width: 0;
        }

        .filter-label {
            font-weight: 600;
            font-size: .875rem;
            color: var(--text-muted);
            flex: 0 0 auto;
        }

        .chip-row {
            display: flex;
            gap: .5rem;
            overflow-x: auto;
            padding-bottom: .25rem;
            scrollbar-width: thin;
            min-width: 0;
        }

        .chip {
            flex: 0 0 auto;
            min-height: 2.25rem;
            padding: .375rem .875rem;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: var(--chip-bg);
            color: var(--chip-text);
            font: inherit;
            font-size: .875rem;
            font-weight: 500;
            cursor: pointer;
            white-space: nowrap;
        }

        .chip:hover { border-color: var(--accent-border); }

        .chip.active {
            background: var(--chip-active-bg);
            border-color: var(--chip-active-bg);
            color: var(--chip-active-text);
        }

        /* ---------- Toolbar ---------- */
        .toolbar {
            display: flex;
            align-items: center;
            gap: .75rem;
            flex-wrap: wrap;
            margin-bottom: 1.25rem;
        }

        .search-wrap {
            flex: 1 1 16rem;
            min-width: 0;
        }

        .search-input {
            width: 100%;
            min-height: 2.75rem;
            padding: .5rem .875rem;
            border-radius: .5rem;
            border: 1px solid var(--border-strong);
            background: var(--card-bg);
            color: var(--text);
            font: inherit;
        }

        .result-count {
            color: var(--text-muted);
            font-size: .875rem;
            white-space: nowrap;
        }

        .filter-toggle { display: none; }

        /* ---------- Article grid ---------- */
        .article-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 1.25rem;
            align-items: stretch;
        }

        .article-grid[hidden], .state-block[hidden] { display: none; }

        .article-card {
            display: flex;
            flex-direction: column;
            min-width: 0;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            cursor: pointer;
        }

        .card-cover {
            position: relative;
            aspect-ratio: 16 / 9;
            width: 100%;
            min-width: 0;
            background: linear-gradient(135deg, var(--bg-subtle), var(--border));
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }

        .card-cover img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .cover-icon {
            font-size: 2rem;
            line-height: 1;
        }

        .cover-type {
            position: absolute;
            inset-block-end: .5rem;
            inset-inline-start: .5rem;
            background: rgba(24, 24, 27, .78);
            color: #FAFAFA;
            font-size: .75rem;
            padding: .125rem .5rem;
            border-radius: .375rem;
        }

        .card-body {
            display: flex;
            flex-direction: column;
            flex: 1 1 auto;
            min-width: 0;
            padding: .875rem 1rem 1rem;
            gap: .5rem;
        }

        .card-badges {
            display: flex;
            flex-wrap: wrap;
            gap: .375rem;
            min-width: 0;
        }

        .status-badge, .content-type-badge, .platform-badge, .artist-badge {
            display: inline-block;
            font-size: .75rem;
            font-weight: 600;
            padding: .125rem .5rem;
            border-radius: .375rem;
            background: var(--badge-bg);
            color: var(--badge-text);
            border: 1px solid var(--border);
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .status-badge.status-draft { border-color: var(--border-strong); }
        .status-badge.status-pending { border-color: var(--accent-border); color: var(--accent-text); }
        .status-badge.status-published { border-color: var(--accent); color: var(--accent-text); }
        .status-badge.status-archived { border-color: var(--border-strong); text-decoration: underline; }

        .card-title {
            margin: 0;
            font-size: 1.0625rem;
            line-height: 1.45;
            font-weight: 700;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            min-width: 0;
            word-break: break-word;
        }

        .card-excerpt {
            margin: 0;
            color: var(--text-muted);
            font-size: .9375rem;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            min-width: 0;
        }

        .card-meta {
            color: var(--text-muted);
            font-size: .8125rem;
            min-width: 0;
        }

        .card-actions {
            display: flex;
            align-items: center;
            gap: .5rem;
            margin-top: auto;
            padding-top: .75rem;
            flex-wrap: wrap;
        }

        .card-actions button, .card-actions a {
            font: inherit;
            font-size: .875rem;
            min-height: 2.25rem;
            padding: .375rem .75rem;
            border-radius: .5rem;
            border: 1px solid var(--border-strong);
            background: var(--card-bg);
            color: var(--text);
            cursor: pointer;
            text-decoration: none;
        }

        /* ---------- Skeletons ---------- */
        .skeleton-card {
            display: flex;
            flex-direction: column;
            min-width: 0;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }

        .skeleton-cover { aspect-ratio: 16 / 9; }
        .skeleton-line {
            height: .875rem;
            margin: .75rem 1rem;
            border-radius: .375rem;
            background: var(--bg-subtle);
        }

        .skeleton-line.short { width: 50%; }

        .skeleton-cover, .skeleton-line {
            background: linear-gradient(90deg, var(--bg-subtle) 25%, var(--border) 50%, var(--bg-subtle) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.4s linear infinite;
        }

        @keyframes shimmer {
            from { background-position: 200% 0; }
            to { background-position: -200% 0; }
        }

        /* ---------- Empty / error ---------- */
        .state-block {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 3rem 1.5rem;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: .75rem;
        }

        .state-block h2 { margin: 0; font-size: 1.25rem; }
        .state-block p { margin: 0; color: var(--text-muted); }
        .state-block .error-title { color: var(--danger); }

        /* ---------- Modals ---------- */
        .modal {
            position: fixed;
            inset: 0;
            z-index: 60;
            display: none;
            align-items: flex-start;
            justify-content: center;
            padding: 1rem;
            overflow-y: auto;
            background: rgba(24, 24, 27, .55);
        }

        .modal.active { display: flex; }

        .modal-content {
            background: var(--bg);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow-lg);
            width: min(48rem, 100%);
            margin: auto;
            padding: 1.5rem;
            position: relative;
            max-height: calc(100vh - 2rem);
            overflow-y: auto;
        }

        .modal-content h2 { margin: 0 2rem .5rem 0; font-size: 1.375rem; }

        .modal-close {
            position: absolute;
            top: .75rem;
            inset-inline-end: .75rem;
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 50%;
            border: 1px solid var(--border-strong);
            background: var(--card-bg);
            color: var(--text);
            font-size: 1.25rem;
            line-height: 1;
            cursor: pointer;
        }

        .modal-meta { color: var(--text-muted); margin-bottom: 1rem; font-size: .9375rem; }

        .modal-body { word-break: break-word; }
        .modal-body h3 { font-size: 1.125rem; margin: 1.25rem 0 .5rem; }
        .modal-body h4 { font-size: 1rem; margin: 1rem 0 .5rem; }
        .modal-body p { margin: 0 0 .875rem; }

        .modal-body pre, .frontmatter-template {
            background: var(--bg-subtle);
            border: 1px solid var(--border);
            border-radius: .5rem;
            padding: .875rem 1rem;
            overflow-x: auto;
            font-size: .875rem;
        }

        .modal-body code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
        .workflow-steps { margin: 0 0 1rem; padding-inline-start: 1.25rem; }
        .workflow-steps li { margin-bottom: .375rem; }

        /* ---------- Filter drawer (mobile) ---------- */
        .filter-drawer {
            position: fixed;
            inset-inline: 0;
            inset-block-end: 0;
            z-index: 70;
            background: var(--bg);
            border-top: 1px solid var(--border);
            box-shadow: var(--shadow-lg);
            border-radius: 1rem 1rem 0 0;
            padding: 1rem 1rem 1.5rem;
            max-height: 80vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .filter-drawer[hidden] { display: none; }

        .drawer-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }

        .drawer-head h2 { margin: 0; font-size: 1.125rem; }

        /* ---------- Responsive ---------- */
        @media (max-width: 1279px) {
            .article-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }

        @media (max-width: 1023px) {
            .article-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }

        @media (max-width: 639px) {
            .article-grid { grid-template-columns: minmax(0, 1fr); }
            .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }

            .filter-bar { display: none; }
            .filter-toggle { display: inline-flex; }

            /* Mobile tap targets >= 44px */
            .chip, .btn, .card-actions button, .card-actions a, .menu-item, .theme-btn {
                min-height: 2.75rem;
            }

            .filter-drawer .chip { min-height: 2.75rem; }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: .01ms !important;
                scroll-behavior: auto !important;
            }
        }
    </style>
</head>
<body>
    <header class="topbar">
        <div class="topbar-left">
            <h1>🎬 創作室</h1>
            <p class="topbar-muted">管理電視、串流、K-Pop 同社交平台內容</p>
        </div>
        <div class="topbar-right">
            <button id="themeBtn" class="theme-btn" type="button"
                    aria-label="切換深色模式" title="切換深色模式"
                    aria-pressed="false">🌙</button>
        </div>
    </header>

    <main class="main">
        <div class="page-header">
            <div class="page-header-text">
                <p class="page-subtitle">管理電視、串流、K-Pop 同社交平台內容</p>
                <span class="total-chip" id="totalCount">共 __TOTAL_COUNT__ 篇文章</span>
            </div>
            <div class="menu-wrap">
                <button id="addArticleBtn" class="btn btn-primary" type="button"
                        aria-haspopup="menu" aria-expanded="false"
                        aria-controls="addMenu">新增文章</button>
                <div id="addMenu" class="menu" role="menu" hidden>
                    <button type="button" class="menu-item" role="menuitem"
                            data-workflow="tv">新增 TV 評論</button>
                    <button type="button" class="menu-item" role="menuitem"
                            data-workflow="kpop">新增 K-Pop 內容</button>
                </div>
            </div>
        </div>

        <section id="kpiRow" class="kpi-grid" aria-label="文章狀態統計">
__KPI_CARDS__
        </section>

        <section id="filterBar" class="filter-bar" aria-label="篩選器">
            <div id="typeFilters" class="filter-group" data-group="type" role="group" aria-label="內容類型">
                <span class="filter-label">內容類型</span>
                <div class="chip-row">
__TYPE_CHIPS__
                </div>
            </div>
            <div id="platformFilters" class="filter-group" data-group="platform" role="group" aria-label="平台">
                <span class="filter-label">平台</span>
                <div class="chip-row">
__PLATFORM_CHIPS__
                </div>
            </div>
            <div id="statusFilters" class="filter-group" data-group="status" role="group" aria-label="狀態">
                <span class="filter-label">狀態</span>
                <div class="chip-row">
__STATUS_CHIPS__
                </div>
            </div>
            <div id="sortFilters" class="filter-group" data-group="sort" role="group" aria-label="排序">
                <span class="filter-label">排序</span>
                <div class="chip-row">
__SORT_CHIPS__
                </div>
            </div>
        </section>

        <div id="toolbar" class="toolbar">
            <div class="search-wrap">
                <input id="searchInput" class="search-input" type="search"
                       placeholder="搜尋標題、平台、標籤"
                       aria-label="搜尋文章" autocomplete="off">
            </div>
            <button id="filterToggle" class="btn btn-ghost filter-toggle" type="button"
                    aria-controls="filterDrawer" aria-expanded="false">篩選</button>
            <span id="resultCount" class="result-count" aria-live="polite">顯示 __TOTAL_COUNT__ / __TOTAL_COUNT__ 篇文章</span>
            <button id="clearFilters" class="btn btn-ghost" type="button">清除篩選</button>
        </div>

        <section id="articleList" class="article-grid" aria-label="文章列表"></section>

        <section id="skeletonGrid" class="article-grid" hidden aria-hidden="true" aria-label="載入中">
__SKELETON_CARDS__
        </section>

        <section id="emptyState" class="state-block" hidden>
            <h2>冇符合篩選條件嘅文章</h2>
            <p>試下清除部分篩選，或者搜尋其他關鍵字</p>
            <button id="emptyClearBtn" class="btn btn-primary" type="button">清除篩選</button>
        </section>

        <section id="errorState" class="state-block" hidden role="alert">
            <h2 class="error-title">載入文章時出錯</h2>
            <p>請檢查網絡或重新載入頁面</p>
            <button id="retryBtn" class="btn btn-primary" type="button">重試</button>
        </section>
    </main>

    <div id="filterDrawer" class="filter-drawer" hidden role="dialog"
         aria-modal="true" aria-label="篩選">
        <div class="drawer-head">
            <h2>篩選</h2>
            <button type="button" class="modal-close" id="drawerCloseBtn" aria-label="關閉篩選">×</button>
        </div>
__DRAWER_FILTERS__
    </div>

    <div class="modal" id="articleModal" role="dialog" aria-modal="true"
         aria-labelledby="modalTitle" aria-hidden="true">
        <div class="modal-content" role="document">
            <button type="button" class="modal-close" id="articleModalClose" aria-label="關閉">×</button>
            <div class="card-badges" id="modalBadges"></div>
            <h2 id="modalTitle"></h2>
            <div class="modal-meta" id="modalMeta"></div>
            <div class="modal-body" id="modalContent"></div>
        </div>
    </div>

    <div class="modal" id="addModal" role="dialog" aria-modal="true"
         aria-labelledby="addModalTitle" aria-hidden="true">
        <div class="modal-content" role="document">
            <button type="button" class="modal-close" id="addModalClose" aria-label="關閉">×</button>
            <h2 id="addModalTitle"></h2>
            <div class="modal-body" id="addModalBody"></div>
        </div>
    </div>

    <script>
        const ARTICLES = __ARTICLES_JSON__;
        const SUMMARY = __SUMMARY_JSON__;

        /* ------------------------------------------------------------------
         * ONE place for every status definition (label, badge class, KPI id).
         * `pending` is a derived bucket = review + scheduled (see PENDING_BUCKET).
         * ------------------------------------------------------------------ */
        const STATUS_CONFIG = {
            draft: { label: '草稿', cls: 'status-draft' },
            review: { label: '待發布', cls: 'status-pending' },
            scheduled: { label: '待發布', cls: 'status-pending' },
            published: { label: '已發布', cls: 'status-published' },
            archived: { label: '封存', cls: 'status-archived' }
        };

        // ONE place for the derived pending bucket mapping.
        const PENDING_BUCKET = ['review', 'scheduled'];

        const FILTER_DEFAULTS = {
            type: 'all',
            platform: [],
            status: 'all',
            sort: 'updated_desc',
            search: ''
        };

        const SORT_OPTIONS = ['updated_desc', 'created_desc', 'title_asc'];
        const TYPE_OPTIONS = ['all', 'tv', 'kpop'];
        const STATUS_OPTIONS = ['all', 'draft', 'pending', 'published', 'archived'];
        const THEME_KEY = 'creation-theme';

        /* ------------------------------------------------------------------
         * Single source of truth for all filter state.
         * platform is an ARRAY of canonical platform ids (multi-select).
         * ------------------------------------------------------------------ */
        const state = {
            type: FILTER_DEFAULTS.type,
            platform: FILTER_DEFAULTS.platform.slice(),
            status: FILTER_DEFAULTS.status,
            sort: FILTER_DEFAULTS.sort,
            search: FILTER_DEFAULTS.search
        };

        const $ = (id) => document.getElementById(id);

        function escapeHtml(text) {
            return String(text == null ? '' : text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function statusConfig(status) {
            return STATUS_CONFIG[status] || STATUS_CONFIG.draft;
        }

        /* ================= URL state (spec 6) ================= */

        function parseUrlState() {
            const params = new URLSearchParams(window.location.search || '');
            const next = {
                type: FILTER_DEFAULTS.type,
                platform: [],
                status: FILTER_DEFAULTS.status,
                sort: FILTER_DEFAULTS.sort,
                search: ''
            };

            const type = params.get('type');
            if (TYPE_OPTIONS.indexOf(type) !== -1) next.type = type;

            const status = params.get('status');
            if (STATUS_OPTIONS.indexOf(status) !== -1) next.status = status;

            const sort = params.get('sort');
            if (SORT_OPTIONS.indexOf(sort) !== -1) next.sort = sort;

            // Comma-separated canonical ids. Ids that do not exist anywhere in
            // the data are dropped, so a junk `?platform=nope` falls back to the
            // default (no platform filter) instead of hiding every article.
            const rawPlatform = params.get('platform');
            if (rawPlatform) {
                const known = [];
                ARTICLES.forEach((article) => {
                    (article.platforms || []).forEach((pid) => {
                        if (known.indexOf(pid) === -1) known.push(pid);
                    });
                });
                const valid = [];
                rawPlatform.split(',').forEach((pid) => {
                    const id = pid.trim();
                    if (id && known.indexOf(id) !== -1 && valid.indexOf(id) === -1) valid.push(id);
                });
                next.platform = valid;
            }

            const q = params.get('q');
            if (q) next.search = q;

            return next;
        }

        function buildUrlQuery() {
            const params = new URLSearchParams();
            if (state.type !== FILTER_DEFAULTS.type) params.set('type', state.type);
            if (state.platform.length) params.set('platform', state.platform.join(','));
            if (state.status !== FILTER_DEFAULTS.status) params.set('status', state.status);
            if (state.sort !== FILTER_DEFAULTS.sort) params.set('sort', state.sort);
            if (state.search) params.set('q', state.search);
            const query = params.toString();
            return query ? '?' + query : '';
        }

        function applyState(next) {
            state.type = next.type;
            state.platform = next.platform.slice();
            state.status = next.status;
            state.sort = next.sort;
            state.search = next.search;
        }

        // Every filter change goes through here: update state, push URL, re-render.
        function commitState(next, options) {
            const opts = options || {};
            applyState(next);
            if (opts.syncUrl !== false) syncUrl();
            if (opts.syncControls !== false) syncControls();
            if (opts.render !== false) render();
        }

        // ALWAYS pushState (never replaceState) so back/forward walks the states.
        function syncUrl() {
            const url = window.location.pathname + buildUrlQuery() + window.location.hash;
            window.history.pushState({}, '', url);
        }

        /* ================= Filtering + sorting (spec 5) ================= */

        function matchesStatus(article, wanted) {
            if (wanted === 'all') return true;
            if (wanted === 'pending') return PENDING_BUCKET.indexOf(article.status) !== -1;
            return article.status === wanted;
        }

        // Multi-select: an article matches if it includes ANY selected platform.
        // Uses the platforms ARRAY, never string equality on the summary string.
        function matchesPlatform(article) {
            if (!state.platform.length) return true;
            const own = article.platforms || [];
            return state.platform.some((pid) => own.indexOf(pid) !== -1);
        }

        function matchesSearch(article) {
            const needle = state.search.trim().toLowerCase();
            if (!needle) return true;
            const haystack = [
                article.title,
                (article.platformLabels || []).join(' '),
                (article.tags || []).join(' '),
                article.artist || ''
            ].join(' ').toLowerCase();
            return haystack.indexOf(needle) !== -1;
        }

        function applyFilters() {
            return ARTICLES.filter((article) =>
                (state.type === 'all' || article.contentType === state.type)
                && matchesPlatform(article)
                && matchesStatus(article, state.status)
                && matchesSearch(article));
        }

        function localeZh() {
            try {
                return new Intl.Collator('zh-HK').compare ? 'zh-HK' : 'zh';
            } catch (err) {
                return 'zh';
            }
        }

        function sortArticles(list) {
            const sorted = list.slice();
            const cmp = localeZh();
            if (state.sort === 'title_asc') {
                sorted.sort((a, b) => String(a.title).localeCompare(String(b.title), cmp));
            } else if (state.sort === 'created_desc') {
                sorted.sort((a, b) => {
                    const byDate = String(b.date || '').localeCompare(String(a.date || ''));
                    if (byDate !== 0) return byDate;
                    return String(b.updated || '').localeCompare(String(a.updated || ''));
                });
            } else {
                sorted.sort((a, b) => {
                    const byUpdated = String(b.updated || '').localeCompare(String(a.updated || ''));
                    if (byUpdated !== 0) return byUpdated;
                    return String(b.date || '').localeCompare(String(a.date || ''));
                });
            }
            return sorted;
        }

        function activeFilterCount() {
            let count = 0;
            if (state.type !== FILTER_DEFAULTS.type) count++;
            if (state.platform.length) count++;
            if (state.status !== FILTER_DEFAULTS.status) count++;
            if (state.search) count++;
            return count;
        }

        /* ================= Rendering (spec 7 / 8) ================= */

        function renderCard(article) {
            const config = statusConfig(article.status);
            const hasSource = !!article.sourceUrl;
            const editHref = hasSource ? article.sourceUrl : '#';
            const editTitle = hasSource ? article.sourcePath : '（此檔案喺另一個 repo：' + article.sourcePath + '）';

            let cover;
            if (article.cover) {
                cover = '<img src="' + escapeHtml(article.cover) + '"'
                    + ' alt="《' + escapeHtml(article.title) + '》封面">';
            } else {
                cover = '<span class="cover-icon" aria-hidden="true">'
                    + (article.contentType === 'kpop' ? '🎤' : '📺')
                    + '</span><span class="cover-type">'
                    + escapeHtml(article.contentTypeLabel) + '</span>';
            }

            let badges = '<span class="status-badge ' + config.cls + '">'
                + escapeHtml(config.label) + '</span>'
                + '<span class="content-type-badge">' + escapeHtml(article.contentTypeLabel) + '</span>';
            (article.platformLabels || []).forEach((label) => {
                badges += '<span class="platform-badge">' + escapeHtml(label) + '</span>';
            });
            if (article.artist) {
                badges += '<span class="artist-badge">🎤 ' + escapeHtml(article.artist) + '</span>';
            }

            const menuItems = '<button type="button" class="menu-item" role="menuitem" data-menu-action="copy">複製連結</button>'
                + (hasSource
                    ? '<a class="menu-item" role="menuitem" data-menu-action="github" href="'
                        + escapeHtml(article.sourceUrl) + '" target="_blank" rel="noopener noreferrer">開 GitHub 檔案</a>'
                    : '<button type="button" class="menu-item" role="menuitem" data-menu-action="copypath">複製源檔路徑</button>');

            return '<article class="article-card" data-id="' + article.id + '" tabindex="0" role="button"'
                + ' aria-label="打開文章：' + escapeHtml(article.title) + '">'
                + '<div class="card-cover">' + cover + '</div>'
                + '<div class="card-body">'
                + '<div class="card-badges">' + badges + '</div>'
                + '<h3 class="card-title">' + escapeHtml(article.title) + '</h3>'
                + '<p class="card-excerpt">' + escapeHtml(article.preview) + '</p>'
                + '<div class="card-meta">更新於 ' + escapeHtml(article.updated || article.date)
                + ' · 發布 ' + escapeHtml(article.date) + '</div>'
                + '<div class="card-actions">'
                + '<a class="btn btn-ghost" data-action="edit" href="' + escapeHtml(editHref) + '"'
                    + (hasSource ? ' target="_blank" rel="noopener noreferrer"' : '')
                    + ' title="' + escapeHtml(editTitle) + '">編輯</a>'
                + '<button class="btn btn-ghost" data-action="preview" type="button">預覽</button>'
                + '<button class="btn btn-ghost btn-more" data-action="more" type="button"'
                    + ' aria-label="更多操作" aria-haspopup="true" aria-expanded="false">更多</button>'
                + '<div class="menu" data-role="more-menu" hidden>'
                + menuItems
                + '</div>'
                + '</div>'
                + '</div>'
                + '</article>';
        }

        function renderSkeleton() {
            $('skeletonGrid').hidden = false;
            $('skeletonGrid').removeAttribute('aria-hidden');
            $('articleList').hidden = true;
            $('emptyState').hidden = true;
            $('errorState').hidden = true;
        }

        function renderEmpty() {
            $('skeletonGrid').hidden = true;
            $('articleList').hidden = true;
            $('errorState').hidden = true;
            $('emptyState').hidden = false;
        }

        function renderError() {
            $('skeletonGrid').hidden = true;
            $('articleList').hidden = true;
            $('emptyState').hidden = true;
            $('errorState').hidden = false;
        }

        function renderList(list) {
            $('skeletonGrid').hidden = true;
            $('errorState').hidden = true;
            $('emptyState').hidden = true;
            $('articleList').hidden = list.length === 0;
            $('articleList').innerHTML = list.map(renderCard).join('');
        }

        function render() {
            let list = [];
            try {
                list = sortArticles(applyFilters());
                if (!list.length) {
                    renderEmpty();
                } else {
                    renderList(list);
                }
                $('resultCount').textContent = '顯示 ' + list.length + ' / ' + ARTICLES.length + ' 篇文章';
            } catch (err) {
                renderError();
                $('resultCount').textContent = '載入文章時出錯';
                if (window.console && console.error) console.error(err);
            }
        }

        function initialRender() {
            renderSkeleton();
            window.setTimeout(() => {
                commitState(parseUrlState(), { syncUrl: false });
            }, 300);
        }

        /* ================= Control sync ================= */

        function chipIsActive(chip) {
            const group = chip.dataset.group;
            const value = chip.dataset.value;
            // platform is multi-select; the single 「全部」 chip stands for "none selected"
            if (group === 'platform') {
                if (value === 'all') return state.platform.length === 0;
                return state.platform.indexOf(value) !== -1;
            }
            return state[group] === value;
        }

        // One delegated handler covers desktop chips AND drawer chips because
        // both carry data-group / data-value.
        function syncControls() {
            document.querySelectorAll('.chip[data-group]').forEach((chip) => {
                const isActive = chipIsActive(chip);
                chip.classList.toggle('active', isActive);
                chip.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });

            document.querySelectorAll('.kpi-card').forEach((card) => {
                const isActive = card.dataset.status === state.status;
                card.classList.toggle('active', isActive);
                card.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });

            const input = $('searchInput');
            if (document.activeElement !== input && input.value !== state.search) {
                input.value = state.search;
            }

            const count = activeFilterCount();
            $('filterToggle').textContent = count ? '篩選 · ' + count : '篩選';
        }

        /* ================= Filter mutations ================= */

        function setFilter(group, value) {
            const next = {
                type: state.type,
                platform: state.platform.slice(),
                status: state.status,
                sort: state.sort,
                search: state.search
            };

            if (group === 'platform') {
                if (value === 'all') {
                    next.platform = [];
                } else {
                    const at = next.platform.indexOf(value);
                    if (at === -1) next.platform.push(value);
                    else next.platform.splice(at, 1);
                }
            } else if (Object.prototype.hasOwnProperty.call(next, group)) {
                next[group] = value;
            }

            commitState(next);
        }

        function clearFilters() {
            // Reset state + clear URL query entirely, but still pushState so
            // back/forward keeps working.
            commitState({
                type: FILTER_DEFAULTS.type,
                platform: [],
                status: FILTER_DEFAULTS.status,
                sort: FILTER_DEFAULTS.sort,
                search: FILTER_DEFAULTS.search
            });
        }

        /* ================= Clipboard helpers ================= */

        function copyText(text) {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).catch(() => copyTextFallback(text));
                return;
            }
            copyTextFallback(text);
        }

        function copyTextFallback(text) {
            const area = document.createElement('textarea');
            area.value = text;
            area.setAttribute('readonly', '');
            area.style.position = 'fixed';
            area.style.opacity = '0';
            document.body.appendChild(area);
            area.select();
            try { document.execCommand('copy'); } catch (err) { /* no-op */ }
            document.body.removeChild(area);
        }

        function articlePermalink(article) {
            return window.location.origin + window.location.pathname
                + buildUrlQuery() + '#article-' + article.id;
        }

        /* ================= Article modal (spec 10) ================= */

        let articleModalTrigger = null;

        function findArticle(id) {
            const key = String(id);
            return ARTICLES.find((article) => String(article.id) === key);
        }

        function openArticleModal(id, trigger) {
            const article = findArticle(id);
            if (!article) return;
            const config = statusConfig(article.status);

            let badges = '<span class="status-badge ' + config.cls + '">'
                + escapeHtml(config.label) + '</span>'
                + '<span class="content-type-badge">' + escapeHtml(article.contentTypeLabel) + '</span>';
            (article.platformLabels || []).forEach((label) => {
                badges += '<span class="platform-badge">' + escapeHtml(label) + '</span>';
            });
            if (article.artist) {
                badges += '<span class="artist-badge">🎤 ' + escapeHtml(article.artist) + '</span>';
            }

            $('modalBadges').innerHTML = badges;
            $('modalTitle').textContent = article.title;
            $('modalMeta').textContent = '更新於 ' + (article.updated || article.date)
                + ' · 發布 ' + article.date;
            // article.content is sanitised server-side article HTML: insert as HTML.
            $('modalContent').innerHTML = article.content;

            articleModalTrigger = trigger || document.activeElement;
            const modal = $('articleModal');
            modal.classList.add('active');
            modal.setAttribute('aria-hidden', 'false');
            $('articleModalClose').focus();
        }

        function closeArticleModal() {
            const modal = $('articleModal');
            if (!modal.classList.contains('active')) return;
            modal.classList.remove('active');
            modal.setAttribute('aria-hidden', 'true');
            if (articleModalTrigger && document.contains(articleModalTrigger)) {
                articleModalTrigger.focus();
            }
            articleModalTrigger = null;
        }

        function isArticleModalOpen() {
            return $('articleModal').classList.contains('active');
        }

        /* ================= 更多 menu ================= */

        let openMoreMenuEl = null;
        let moreMenuTrigger = null;

        function closeMoreMenu(refocus) {
            if (!openMoreMenuEl) return;
            openMoreMenuEl.hidden = true;
            const btn = openMoreMenuEl.querySelector('[data-action="more"]');
            if (btn) btn.setAttribute('aria-expanded', 'false');
            if (refocus && moreMenuTrigger && document.contains(moreMenuTrigger)) {
                moreMenuTrigger.focus();
            }
            openMoreMenuEl = null;
            moreMenuTrigger = null;
        }

        function openMoreMenu(articleId, trigger) {
            closeMoreMenu(false);
            const card = document.querySelector('.article-card[data-id="' + articleId + '"]');
            if (!card) return;
            const menu = card.querySelector('[data-role="more-menu"]');
            if (!menu) return;
            menu.hidden = false;
            trigger.setAttribute('aria-expanded', 'true');
            openMoreMenuEl = menu;
            moreMenuTrigger = trigger;
            const first = menu.querySelector('.menu-item');
            if (first) first.focus();
        }

        function toggleMoreMenu(articleId, trigger) {
            if (openMoreMenuEl && openMoreMenuEl.closest('.article-card[data-id="' + articleId + '"]')) {
                closeMoreMenu(true);
            } else {
                openMoreMenu(articleId, trigger);
            }
        }

        function isMoreMenuOpen() {
            return !!openMoreMenuEl;
        }

        /* ================= Filter drawer (spec 9) ================= */

        function toggleDrawer(open) {
            const drawer = $('filterDrawer');
            const shouldOpen = typeof open === 'boolean' ? open : drawer.hidden;
            drawer.hidden = !shouldOpen;
            $('filterToggle').setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
            if (shouldOpen) {
                $('drawerCloseBtn').focus();
            } else {
                $('filterToggle').focus();
            }
        }

        function isDrawerOpen() {
            return !$('filterDrawer').hidden;
        }

        /* ================= Theme (spec 3) ================= */

        function applyTheme(theme) {
            const dark = theme === 'dark';
            document.body.setAttribute('data-theme', dark ? 'dark' : 'light');
            document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
            const btn = $('themeBtn');
            btn.textContent = dark ? '☀️' : '🌙';
            btn.setAttribute('aria-label', dark ? '切換淺色模式' : '切換深色模式');
            btn.setAttribute('title', dark ? '切換淺色模式' : '切換深色模式');
            btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
        }

        function loadTheme() {
            let stored = null;
            try { stored = window.localStorage.getItem(THEME_KEY); } catch (err) { stored = null; }
            applyTheme(stored === 'dark' || stored === 'light' ? stored : 'light');
        }

        function toggleTheme() {
            const dark = document.body.getAttribute('data-theme') === 'dark';
            const next = dark ? 'light' : 'dark';
            applyTheme(next);
            try { window.localStorage.setItem(THEME_KEY, next); } catch (err) { /* no-op */ }
        }

        /* ================= 新增文章 modal ================= */

        const WORKFLOWS = {
            tv: {
                title: '新增 TV 評論',
                dir: 'tv-reviews/',
                note: '檔案放喺呢個 repo 嘅 tv-reviews/ 資料夾。',
                body: function () {
                    return '<p>' + this.note + ' 喺 <code>' + this.dir + '</code> 新增一個 .md 檔，'
                        + '以下面嘅 frontmatter 開頭，之後重新執行 generator。</p>'
                        + '<pre class="frontmatter-template"><code>---\\n'
                        + 'title: 劇集標題 — 標題\\n'
                        + 'platform: TVB\\n'
                        + 'status: draft\\n'
                        + 'date: 2026-01-01\\n'
                        + 'tags: [tag1, tag2]\\n'
                        + '---\\n\\n## 文章\\n\\n正文…\\n</code></pre>'
                        + '<pre class="frontmatter-template"><code>python3 scripts/generate_dashboard.py</code></pre>';
                }
            },
            kpop: {
                title: '新增 K-Pop 內容',
                dir: 'posts/',
                note: 'K-Pop 內容放喺另一個 repo（workspace-kpop），唔喺呢個 repo 入面。',
                body: function () {
                    return '<p>' + this.note + ' 喺 workspace-kpop 嘅 <code>' + this.dir
                        + '</code> 新增一個 .md 檔，然後重新執行 generator。</p>'
                        + '<pre class="frontmatter-template"><code>---\\n'
                        + 'title: 藝人 — 專輯\\n'
                        + 'platform: Spotify|YouTube\\n'
                        + 'status: draft\\n'
                        + 'artist: 藝人名\\n'
                        + 'date: 2026-01-01\\n'
                        + 'tags: [tag1, tag2]\\n'
                        + '---\\n\\n## 文章\\n\\n正文…\\n</code></pre>'
                        + '<pre class="frontmatter-template"><code>python3 scripts/generate_dashboard.py</code></pre>';
                }
            }
        };

        let addModalTrigger = null;

        function openAddModal(kind, trigger) {
            const workflow = WORKFLOWS[kind] || WORKFLOWS.tv;
            $('addModalTitle').textContent = workflow.title;
            $('addModalBody').innerHTML = workflow.body();
            closeAddMenu();
            addModalTrigger = trigger || document.activeElement;
            const modal = $('addModal');
            modal.classList.add('active');
            modal.setAttribute('aria-hidden', 'false');
            $('addModalClose').focus();
        }

        function closeAddModal() {
            const modal = $('addModal');
            if (!modal.classList.contains('active')) return;
            modal.classList.remove('active');
            modal.setAttribute('aria-hidden', 'true');
            if (addModalTrigger && document.contains(addModalTrigger)) {
                addModalTrigger.focus();
            }
            addModalTrigger = null;
        }

        function isAddModalOpen() {
            return $('addModal').classList.contains('active');
        }

        function closeAddMenu() {
            $('addMenu').hidden = true;
            $('addArticleBtn').setAttribute('aria-expanded', 'false');
        }

        function toggleAddMenu() {
            const menu = $('addMenu');
            menu.hidden = !menu.hidden;
            $('addArticleBtn').setAttribute('aria-expanded', menu.hidden ? 'false' : 'true');
        }

        /* ================= Event wiring ================= */

        function bindEvents() {
            // Delegated: covers filter bar chips AND drawer chips.
            document.addEventListener('click', (event) => {
                const chip = event.target.closest('.chip[data-group]');
                if (chip) {
                    setFilter(chip.dataset.group, chip.dataset.value);
                    return;
                }

                const kpi = event.target.closest('.kpi-card');
                if (kpi) {
                    const next = {
                        type: state.type,
                        platform: state.platform.slice(),
                        status: kpi.dataset.status,
                        sort: state.sort,
                        search: state.search
                    };
                    commitState(next);
                    return;
                }

                const workflow = event.target.closest('.menu-item[data-workflow]');
                if (workflow) {
                    openAddModal(workflow.dataset.workflow, event.target.closest('#addArticleBtn'));
                    return;
                }

                // 更多 menu items
                const menuAction = event.target.closest('.menu-item[data-menu-action]');
                if (menuAction) {
                    event.stopPropagation();
                    const card = menuAction.closest('.article-card');
                    const article = card ? findArticle(card.dataset.id) : null;
                    if (article) {
                        if (menuAction.dataset.menuAction === 'copy') {
                            copyText(articlePermalink(article));
                        } else if (menuAction.dataset.menuAction === 'copypath') {
                            copyText(article.sourcePath);
                        }
                    }
                    closeMoreMenu(true);
                    return;
                }

                // Card action buttons stopPropagation so the card does NOT open.
                const action = event.target.closest('.card-actions [data-action]');
                if (action) {
                    event.stopPropagation();
                    const card = action.closest('.article-card');
                    if (!card) return;
                    const kind = action.dataset.action;
                    if (kind === 'more') {
                        toggleMoreMenu(card.dataset.id, action);
                    } else if (kind === 'preview') {
                        openArticleModal(card.dataset.id, action);
                    } else if (kind === 'edit' && !articleHasSource(card)) {
                        event.preventDefault();
                    }
                    return;
                }

                // Whole card opens the detail modal.
                const card = event.target.closest('.article-card');
                if (card) {
                    openArticleModal(card.dataset.id, card);
                    return;
                }

                // Clicking outside closes menus / drawer-ish popovers.
                if (!event.target.closest('.card-actions')) {
                    closeMoreMenu(false);
                }
            });

            $('searchInput').addEventListener('input', (event) => {
                const next = {
                    type: state.type,
                    platform: state.platform.slice(),
                    status: state.status,
                    sort: state.sort,
                    search: event.target.value
                };
                commitState(next);
            });

            $('clearFilters').addEventListener('click', clearFilters);
            $('emptyClearBtn').addEventListener('click', clearFilters);
            $('retryBtn').addEventListener('click', () => {
                commitState(parseUrlState(), { syncUrl: false });
            });
            $('themeBtn').addEventListener('click', toggleTheme);
            $('addArticleBtn').addEventListener('click', toggleAddMenu);
            $('addModalClose').addEventListener('click', closeAddModal);
            $('articleModalClose').addEventListener('click', closeArticleModal);
            $('filterToggle').addEventListener('click', () => toggleDrawer());
            $('drawerCloseBtn').addEventListener('click', () => toggleDrawer(false));

            [$('articleModal'), $('addModal')].forEach((modal) => {
                modal.addEventListener('click', (event) => {
                    if (event.target === modal) {
                        if (modal.id === 'articleModal') closeArticleModal();
                        else closeAddModal();
                    }
                });
            });

            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape') {
                    // Esc closes the top-most thing first.
                    if (isMoreMenuOpen()) {
                        closeMoreMenu(true);
                    } else if (isDrawerOpen()) {
                        toggleDrawer(false);
                    } else if (isArticleModalOpen()) {
                        closeArticleModal();
                    } else if (isAddModalOpen()) {
                        closeAddModal();
                    } else {
                        closeAddMenu();
                    }
                    return;
                }

                if (event.target.classList && event.target.classList.contains('article-card')) {
                    if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
                        event.preventDefault();
                        openArticleModal(event.target.dataset.id, event.target);
                    }
                }
            });

            // MANDATORY: back/forward restores filter state.
            window.addEventListener('popstate', () => {
                commitState(parseUrlState(), { syncUrl: false });
            });
        }

        function articleHasSource(card) {
            const article = findArticle(card.dataset.id);
            return !!(article && article.sourceUrl);
        }

        /* ================= Boot ================= */

        function init() {
            loadTheme();
            bindEvents();
            initialRender();
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    </script>
</body>
</html>"""

# Sort options rendered in the 「排序」 group. `pending` is a derived KPI/status
# bucket (review + scheduled) rather than a raw status id.
SORT_OPTIONS = OrderedDict([
    ('updated_desc', '最近更新'),
    ('created_desc', '建立日期'),
    ('title_asc', '標題 A-Z'),
])

# KPI cards, in display order. `pending` = review + scheduled (see summary_counts).
KPI_CONFIG = (
    ('all', '全部文章'),
    ('draft', '草稿'),
    ('pending', '待發布'),
    ('published', '已發布'),
    ('archived', '封存'),
)


def _attr(value):
    """Escape a value for use inside a double-quoted HTML attribute."""
    return escape_html(value)


def escape_html(text):
    """Minimal HTML escaping for text placed into attributes / text nodes."""
    if text is None:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def used_content_types(all_articles):
    """Canonical content-type ids actually present in the data, in label order."""
    present = {a.get('contentType') or a.get('content_type') for a in all_articles}
    return [ct for ct in CONTENT_TYPE_LABELS if ct in present]


def used_platforms(all_articles):
    """Platform ids actually present, following the PLATFORMS declaration order."""
    present = set()
    for article in all_articles:
        present.update(article.get('platforms') or [])
    return [pid for pid in PLATFORMS if pid in present]


def render_kpi_cards(counts):
    """KPI buttons with server-rendered numbers so the HTML is meaningful pre-JS."""
    active = 'all'
    cards = []

    for value, label in KPI_CONFIG:
        # summary_counts exposes the grand total as `total`, not `all`.
        key = 'total' if value == 'all' else value
        number = counts.get(key, 0)
        is_active = value == active
        classes = 'kpi-card' + (' active' if is_active else '')
        cards.append(
            f'            <button type="button" class="{classes}" data-status="{_attr(value)}"'
            f' aria-pressed="{"true" if is_active else "false"}">'
            f'<span class="kpi-check" aria-hidden="true">✓</span>'
            f'<span class="kpi-value">{number}</span>'
            f'<span class="kpi-label">{_attr(label)}</span>'
            f'</button>'
        )

    return '\n'.join(cards)


def render_chip(value, label, group, active=False):
    """One filter chip. `aria-pressed` mirrors the active state, not colour alone."""
    classes = 'chip' + (' active' if active else '')
    pressed = 'true' if active else 'false'
    return (f'<button type="button" class="{classes}" data-group="{group}"'
            f' data-value="{_attr(value)}" aria-pressed="{pressed}">{_attr(label)}</button>')


def render_filter_groups(all_articles):
    """(type_chips, platform_chips, status_chips, sort_chips, drawer_html)."""
    type_chips = [render_chip('all', '全部', 'type', active=True)]
    for content_type in used_content_types(all_articles):
        type_chips.append(render_chip(content_type,
                                      CONTENT_TYPE_LABELS[content_type],
                                      'type'))

    platform_chips = [render_chip('all', '全部', 'platform', active=True)]
    for platform_id in used_platforms(all_articles):
        platform_chips.append(render_chip(platform_id,
                                          PLATFORMS[platform_id],
                                          'platform'))

    # One chip per visible bucket. `review`/`scheduled` both map to the derived
    # 「待發布」 bucket so the chips mirror the KPI cards exactly (5 chips, no dupes).
    status_chips = [render_chip('all', '全部', 'status', active=True)]
    seen_labels = {'全部'}
    for status_id, config in STATUS_CONFIG.items():
        label = config['label']
        if label in seen_labels:
            continue
        seen_labels.add(label)
        chip_value = 'pending' if label == '待發布' else status_id
        status_chips.append(render_chip(chip_value, label, 'status'))

    sort_chips = [render_chip(value, label, 'sort', active=value == 'updated_desc')
                  for value, label in SORT_OPTIONS.items()]

    drawer_groups = []
    for group_id, group_label, chips in (
        ('typeFilters', '內容類型', type_chips),
        ('platformFilters', '平台', platform_chips),
        ('statusFilters', '狀態', status_chips),
        ('sortFilters', '排序', sort_chips),
    ):
        drawer_groups.append(
            f'        <div id="{group_id}-drawer" class="filter-group" data-group-drawer="{group_id}"'
            f' role="group" aria-label="{_attr(group_label)}">\n'
            f'            <span class="filter-label">{_attr(group_label)}</span>\n'
            f'            <div class="chip-row">\n'
            + '\n'.join(f'                {chip}' for chip in chips)
            + '\n            </div>\n        </div>'
        )

    return (type_chips, platform_chips, status_chips, sort_chips,
            '\n'.join(drawer_groups))


def render_skeletons(count=8):
    cards = []
    for _ in range(count):
        cards.append(
            '            <div class="skeleton-card" aria-hidden="true">'
            '<div class="skeleton-cover"></div>'
            '<div class="skeleton-line"></div>'
            '<div class="skeleton-line short"></div>'
            '</div>'
        )
    return '\n'.join(cards)


def generate_html(all_articles):
    """Assemble the dashboard by substituting placeholders into PAGE_TEMPLATE.

    Deliberately `.replace()`-based (not an f-string / .format()) so the CSS and
    JS braces in the template stay literal.
    """
    counts = summary_counts(all_articles)
    total = counts['total']

    payload = []
    for idx, article in enumerate(all_articles):
        payload.append(json.loads(generate_article_js(article, idx, 0)))

    articles_js = json.dumps(payload, ensure_ascii=False)
    summary_json = json.dumps(counts, ensure_ascii=False)

    type_chips, platform_chips, status_chips, sort_chips, drawer_html = \
        render_filter_groups(all_articles)

    html = PAGE_TEMPLATE
    html = html.replace('__ARTICLES_JSON__', articles_js)
    html = html.replace('__SUMMARY_JSON__', summary_json)
    html = html.replace('__TOTAL_COUNT__', str(total))
    html = html.replace('__KPI_CARDS__', render_kpi_cards(counts))
    html = html.replace('__TYPE_CHIPS__', '\n'.join(
        f'                    {chip}' for chip in type_chips))
    html = html.replace('__PLATFORM_CHIPS__', '\n'.join(
        f'                    {chip}' for chip in platform_chips))
    html = html.replace('__STATUS_CHIPS__', '\n'.join(
        f'                    {chip}' for chip in status_chips))
    html = html.replace('__SORT_CHIPS__', '\n'.join(
        f'                    {chip}' for chip in sort_chips))
    html = html.replace('__SKELETON_CARDS__', render_skeletons())
    html = html.replace('__DRAWER_FILTERS__', drawer_html)

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

    counts = summary_counts(all_articles)
    print(f"   📊 Status — draft: {counts['draft']}, review: {counts['review']}, "
          f"scheduled: {counts['scheduled']}, published: {counts['published']}, "
          f"archived: {counts['archived']} (pending: {counts['pending']})")

    for a in all_articles:
        type_icon = "🎤" if a['content_type'] == 'kpop' else "📺"
        print(f"   {type_icon} {a['date']} - {a['title'][:50]}")

    html = generate_html(all_articles)

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"   ✅ Written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
