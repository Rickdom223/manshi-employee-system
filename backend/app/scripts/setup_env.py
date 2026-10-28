"""Generate local-only credentials; never overwrite an existing .env."""
import secrets
import os
from app.core.config import BACKEND

def main():
    path = BACKEND / '.env'
    text=(BACKEND/'.env.example').read_text(encoding='utf-8').replace('REPLACE_WITH_RANDOM_SECRET_AT_LEAST_32_CHARACTERS',secrets.token_urlsafe(48))
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print('已有 backend/.env，未覆盖。文档指定新账号仅在初始化时创建。')
        return
    with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
        output.write(text)
    print('已生成 backend/.env。请勿公开此文件；初始化登录及改密步骤见README。')

if __name__ == '__main__':
    main()
