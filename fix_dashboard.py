#!/usr/bin/env python3
import os, re, sys
from datetime import datetime

# Import the generate_dashboard module
sys.path.insert(0, '/home/ubuntu/.openclaw/workspace-creation/scripts')
from generate_dashboard import main as gen_main, get_reviews

# Run the generator
print("Running generator...")
import subprocess
result = subprocess.run(['python3', 'scripts/generate_dashboard.py'], 
                       capture_output=True, text=True, 
                       cwd='/home/ubuntu/.openclaw/workspace-creation')
print(result.stdout)

# The generator produces web/index.html with NEW layout
# We want to keep OLD layout structure (hero, container, etc)
# and just swap the articles

# Read the OLD c5bc161 template
old_html = open('/home/ubuntu/.openclaw/workspace-creation/web/index.html').read()

# Find old articles section
old_articles_start = old_html.find('const articles = [')
old_articles_end = old_html.find('];', old_articles_start) + 2

# Read the NEW generated HTML (with NEW articles but NEW layout)
new_html = open('/home/ubuntu/.openclaw/workspace-creation/web/index.html').read()
new_articles_start = new_html.find('const articles = [')
new_articles_end = new_html.find('];', new_articles_start) + 2

# Extract new articles section
new_articles_section = new_html[new_articles_start:new_articles_end]

# Replace in old HTML
result_html = old_html[:old_articles_start] + new_articles_section + old_html[old_articles_end:]

# Save
with open('/home/ubuntu/.openclaw/workspace-creation/web/index.html', 'w') as f:
    f.write(result_html)

print(f"Done! Combined old layout with new articles ({len(new_articles_section)} chars)")
print(f"Result HTML size: {len(result_html)} chars")
print(f"First 5 lines:")
for line in result_html.split('\n')[:5]:
    print(f"  {line[:80]}")