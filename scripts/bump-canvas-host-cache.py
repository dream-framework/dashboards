import os, re, glob
root = '/home/z/my-project/dashboards/custom-html'
files = glob.glob(os.path.join(root, '*.html'))
pat = re.compile(r'canvas-host\.css\?v=\d+')
bumped = 0
for f in files:
    s = open(f).read()
    new = pat.sub('canvas-host.css?v=20261006', s)
    if new != s:
        open(f, 'w').write(new)
        bumped += 1
        print(f"bumped {os.path.basename(f)}")
print(f"Total bumped: {bumped}")
