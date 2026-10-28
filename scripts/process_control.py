"""Start a directly controlled test server, avoiding the Windows venv launcher."""
import os,sys,sysconfig

def uvicorn_command(*arguments):
    if os.name!='nt':return [sys.executable,'-m','uvicorn',*arguments]
    # Use the same Python build and venv libraries, with no launcher child.
    bootstrap=f"import sys,runpy;sys.path.insert(0,{sysconfig.get_path('purelib')!r});runpy.run_module('uvicorn',run_name='__main__')"
    return [sys._base_executable,'-c',bootstrap,*arguments]

def stop_process_tree(process):
    if process.poll() is not None:return
    process.terminate()
    process.wait(timeout=15)
