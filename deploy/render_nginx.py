import os
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'deploy/nginx.conf').read_text(encoding='utf-8')
port=int(os.getenv('PUBLIC_PORT','8080'))
if not 1024<=port<=65535:raise SystemExit('PUBLIC_PORT应为1024–65535')
source=source.replace('__PROJECT_ROOT__',ROOT.as_posix()).replace('__PUBLIC_PORT__',str(port))
# nginx's compiled default config directory supplies mime.types; use the installed copy explicitly.
candidates=[Path('/etc/nginx/mime.types'),Path('/usr/local/nginx/conf/mime.types')]
mime=next((p for p in candidates if p.exists()),None)
if not mime:raise SystemExit('找不到Nginx mime.types，请确认已安装完整Nginx')
source=source.replace('include mime.types;',f'include "{mime.as_posix()}";')
(ROOT/'deploy/nginx.generated.conf').write_text(source,encoding='utf-8')
