import re, os
files = [
  '/home/z/my-project/index.html',
  '/home/z/my-project/custom-html/executive-chatters-portfolio.html',
]
patterns = [
  (re.compile(r'\?v=20260804'), '?v=20261007'),
  (re.compile(r'\?v=20260810'), '?v=20261007'),
  (re.compile(r'\?v=20260813'), '?v=20261007'),
  (re.compile(r'\?v=20260821'), '?v=20261007'),
  (re.compile(r'\?v=20260822'), '?v=20261007'),
]
for f in files:
  if not os.path.exists(f): continue
  s = open(f).read()
  for pat, repl in patterns:
    s = pat.sub(repl, s)
  open(f, 'w').write(s)
  print(f"bumped {os.path.basename(f)}")
