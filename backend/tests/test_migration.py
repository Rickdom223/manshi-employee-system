import os,sqlite3,subprocess,sys
from pathlib import Path

def test_migration_preserves_legacy_data(tmp_path):
    path=tmp_path/'legacy.sqlite3'
    connection=sqlite3.connect(path)
    connection.executescript('''
    CREATE TABLE users (id INTEGER PRIMARY KEY,username VARCHAR(50) NOT NULL UNIQUE,password_hash VARCHAR NOT NULL,role VARCHAR NOT NULL CHECK(role='admin'),is_active BOOLEAN NOT NULL,created_at DATETIME NOT NULL);
    CREATE TABLE departments(id INTEGER PRIMARY KEY,code VARCHAR NOT NULL UNIQUE,name VARCHAR NOT NULL UNIQUE,is_active BOOLEAN NOT NULL,created_at DATETIME NOT NULL);
    CREATE TABLE positions(id INTEGER PRIMARY KEY,code VARCHAR NOT NULL UNIQUE,name VARCHAR NOT NULL,department_id INTEGER REFERENCES departments(id),is_active BOOLEAN NOT NULL,created_at DATETIME NOT NULL,UNIQUE(department_id,name));
    CREATE TABLE employees(id INTEGER PRIMARY KEY,employee_no VARCHAR NOT NULL UNIQUE,full_name VARCHAR NOT NULL,phone VARCHAR,department_id INTEGER REFERENCES departments(id),position_id INTEGER REFERENCES positions(id),hire_date DATE NOT NULL,status VARCHAR NOT NULL,resignation_date DATE,remark VARCHAR,created_at DATETIME NOT NULL,updated_at DATETIME NOT NULL);
    CREATE TABLE skills(id INTEGER PRIMARY KEY,code VARCHAR NOT NULL UNIQUE,name VARCHAR NOT NULL UNIQUE,is_active BOOLEAN NOT NULL);
    CREATE TABLE employee_skills(id INTEGER PRIMARY KEY,employee_id INTEGER REFERENCES employees(id),skill_id INTEGER REFERENCES skills(id),proficiency VARCHAR NOT NULL,updated_at DATETIME NOT NULL,UNIQUE(employee_id,skill_id));
    INSERT INTO users VALUES(1,'oldadmin','preserved-argon-hash','admin',1,'2026-10-26');
    INSERT INTO departments VALUES(1,'OLD','旧部门',1,'2026-10-26');
    INSERT INTO positions VALUES(1,'OLDP','旧岗位',1,1,'2026-10-26');
    INSERT INTO employees VALUES(1,'OLD01','旧员工',NULL,1,1,'2026-10-01','active',NULL,'保留备注','2026-10-26','2026-10-26');
    INSERT INTO skills VALUES(1,'SK01','旧技能',1);
    INSERT INTO employee_skills VALUES(1,1,1,'expert','2026-10-26');
    ''');connection.commit();connection.close()
    env=dict(os.environ,DATABASE_PATH=str(path))
    for _ in range(2):
        result=subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT username,password_hash,role FROM users').fetchone()==('oldadmin','preserved-argon-hash','ADMIN')
        assert db.execute('SELECT employee_no,full_name,remark,base_salary_cents FROM employees').fetchone()==('OLD01','旧员工','保留备注',0)
        assert db.execute('SELECT COUNT(*) FROM employee_skills').fetchone()[0]==1
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
