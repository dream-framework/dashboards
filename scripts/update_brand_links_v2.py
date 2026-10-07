"""Split brand <a> into two links: logo → insight-analytics.ca, title → local"""
import re, os, glob

MAIN = '/home/z/my-project/index.html'
CUSTOM = '/home/z/my-project/custom-html'

def update_file(fp):
    s = open(fp).read()
    orig = s
    
    # Match: <a class="brand" ...>...</a>  (any attributes after class)
    # Use a marker-based split: find <div class="brand-mark"> and <div class="brand-text">
    # then rebuild as <div class="brand"> with two <a> children.
    
    pat = re.compile(r'<a class="brand"[^>]*>(.*?)</a>', re.DOTALL)
    
    def repl(m):
        inner = m.group(1)
        # Extract the brand-mark div (contains the SVG)
        mk = re.search(r'<div class="brand-mark">.*?</div>', inner, re.DOTALL)
        tx = re.search(r'<div class="brand-text">.*?</div>', inner, re.DOTALL)
        if not mk or not tx:
            return m.group(0)
        local_href = '../index.html' if 'custom-html' in fp else './index.html'
        return (
            '<div class="brand">' +
            '<a class="brand-mark-link" href="https://insight-analytics.ca/" target="_blank" rel="noopener" title="Insight Analytics — main site">' +
            mk.group(0) +
            '</a>' +
            '<a class="brand-text-link" href="' + local_href + '" title="Dashboards Studio home">' +
            tx.group(0) +
            '</a>' +
            '</div>'
        )
    
    s = pat.sub(repl, s)
    if s != orig:
        open(fp, 'w').write(s)
        return True
    return False

if update_file(MAIN):
    print(f"  Updated index.html")
else:
    print(f"  No change index.html")

count = 0
for fp in sorted(glob.glob(os.path.join(CUSTOM, '*.html'))):
    if update_file(fp):
        print(f"  Updated {os.path.basename(fp)}")
        count += 1
print(f"\nTotal: {count} custom-html pages updated")
