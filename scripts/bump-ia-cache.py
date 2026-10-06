import re
p = '/home/z/insight-analytics/index.html'
s = open(p).read()
s = re.sub(r'\?v=4\.48\.0', '?v=4.49.0', s)
open(p, 'w').write(s)
print("Bumped index.html cache strings to v4.49.0")
