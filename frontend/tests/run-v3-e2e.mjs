import {spawnSync} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..')
const python=process.env.PYTHON||path.join(root,'backend','.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python')
const result=spawnSync(python,[path.join(root,'scripts','run_v3_e2e.py')],{cwd:root,stdio:'inherit'})
if(result.error)console.error(result.error.message)
process.exit(result.status??1)
