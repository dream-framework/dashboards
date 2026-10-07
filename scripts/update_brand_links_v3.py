"""Split brand <a> into two links: logo → insight-analytics.ca, title → local
Handles both <div> and <span> for brand-mark/brand-text."""
import re, os, glob

CUSTOM = '/home/z/my-project/custom-html'

def update_file(fp):
    s = open(fp).read()
    orig = s
    
    # Match the entire <a class="brand" ...>...</a> block
    pat = re.compile(r'<a class="brand"[^>]*>(.*?)</a>', re.DOTALL)
    
    def repl(m):
        inner = m.group(1)
        # Find brand-mark element (span or div)
        mk = re.search(r'<(span|div) class="brand-mark">.*?</\1>', inner, re.DOTALL)
        # Find brand-text element (span or div)
        tx = re.search(r'<(span|div) class="brand-text">.*?</\1>', inner, re.DOTALL)
        if not mk or not tx:
            return m.group(0)
        local_href = '../index.html'  # custom-html pages
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

count = 0
for fp in sorted(glob.glob(os.path.join(CUSTOM, '*.html'))):
    if update_file(fp):
        print(f"  Updated {os.path.basename(fp)}")
        count += 1
print(f"\nTotal: {count} custom-html pages updated")
