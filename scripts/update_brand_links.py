"""
Split the brand <a> into two links: logo → insight-analytics.ca, title → ../index.html
Also update the main index.html the same way.
"""
import re, os, glob

# Pattern: <a class="brand" href="../index.html">...<div class="brand-mark">SVG</div>...<div class="brand-text">...</div>...</a>
# OR: <a class="brand" href="#">...same structure...</a>

MAIN_INDEX = '/home/z/my-project/index.html'
CUSTOM_DIR = '/home/z/my-project/custom-html'

def update_file(fp):
    s = open(fp).read()
    orig = s
    
    # Pattern 1: href="../index.html" (custom-html pages)
    # Pattern 2: href="#" (main index)
    # Replace the outer <a class="brand" href="..."> with a <div class="brand"> wrapper
    # containing two separate <a> tags.
    
    # Match: <a class="brand" href="..."> <div class="brand-mark">...</div> <div class="brand-text">...</div> </a>
    pattern = r'<a class="brand" href="[^"]*">(.*?)</a>'
    
    def replace_brand(match):
        inner = match.group(1)
        # Split inner HTML at the brand-text div boundary
        # The inner HTML looks like:
        # <div class="brand-mark"><svg...></svg></div>
        # <div class="brand-text">...</div>
        # (with some whitespace between them)
        
        # Find the brand-mark div
        mark_match = re.search(r'(<div class="brand-mark">.*?</div>)', inner, re.DOTALL)
        text_match = re.search(r'(<div class="brand-text">.*?</div>)', inner, re.DOTALL)
        
        if not mark_match or not text_match:
            return match.group(0)  # Can't parse, leave as-is
        
        mark_html = mark_match.group(1)
        text_html = text_match.group(1)
        
        # Determine the local href (custom-html pages use ../index.html, main uses ./index.html)
        local_href = '../index.html' if 'custom-html' in fp else './index.html'
        
        return (
            '<div class="brand">' +
            '<a class="brand-mark-link" href="https://insight-analytics.ca/" target="_blank" rel="noopener" title="Insight Analytics — main site">' +
            mark_html +
            '</a>' +
            '<a class="brand-text-link" href="' + local_href + '" title="Dashboards Studio home">' +
            text_html +
            '</a>' +
            '</div>'
        )
    
    s = re.sub(pattern, replace_brand, s, flags=re.DOTALL)
    
    if s != orig:
        open(fp, 'w').write(s)
        return True
    return False

# Update main index.html
if update_file(MAIN_INDEX):
    print(f"  Updated {MAIN_INDEX}")
else:
    print(f"  No change {MAIN_INDEX}")

# Update all custom-html pages
count = 0
for fp in sorted(glob.glob(os.path.join(CUSTOM_DIR, '*.html'))):
    if update_file(fp):
        print(f"  Updated {os.path.basename(fp)}")
        count += 1
print(f"\nTotal: {count} custom-html pages updated")
