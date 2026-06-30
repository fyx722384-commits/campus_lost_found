"""兼容部分本地 Python 解释器没有正确加载 site-packages 的情况。"""

import os
import site
import sys


prefixes = {sys.prefix, sys.base_prefix, os.path.dirname(sys.executable)}
drive, _ = os.path.splitdrive(sys.executable)
if drive:
    prefixes.add(drive + os.sep)

for prefix in prefixes:
    candidate = os.path.abspath(os.path.join(prefix, "Lib", "site-packages"))
    if os.path.isdir(candidate) and candidate not in sys.path:
        site.addsitedir(candidate)
