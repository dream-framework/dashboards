import re
files = [
  '/home/z/my-project/data/groq-config.json',
  '/home/z/my-project/dashboards/data/groq-config.json',
  '/home/z/insight-analytics/dashboards-preview/data/groq-config.json',
  '/home/z/insight-analytics/dashboards-preview/js/contact-chat.js',
]
for f in files:
  try:
    s = open(f).read()
    new = s.replace('https://dashboards-groq-proxy.netlify.app/groq-proxy', 'https://startling-belekoy-b0ec70.netlify.app/groq-proxy')
    if new != s:
      open(f, 'w').write(new)
      print(f"updated {f}")
    else:
      print(f"no change {f}")
  except FileNotFoundError:
    print(f"skip (not found) {f}")
