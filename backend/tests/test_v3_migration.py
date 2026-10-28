import os,sys,sqlite3,subprocess
from pathlib import Path
from app.core.security import password_hash

BACKEND=Path(__file__).resolve().parents[1]
def run(path,*args):
    env=dict(os.environ,DATABASE_PATH=str(path),SESSION_SECRET_KEY='migration-test-secret-which-is-more-than-32-characters')
    result=subprocess.run([sys.executable,*args],cwd=BACKEND,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    assert result.returncode==0,result.stdout+result.stderr

def test_empty_migrate_seed_repeat_and_persistent_password(tmp_path):
    path=tmp_path/'fresh.sqlite3'
    run(path,'-m','alembic','upgrade','head');run(path,'-m','app.scripts.init_data')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM departments').fetchone()[0]==4
        assert 'gender' not in {row[1] for row in db.execute('PRAGMA table_info(employees)')}
        assert db.execute('SELECT username,role,employee_id FROM users').fetchall()==[('admin','SYS_ADMIN',None)]
        assert db.execute('SELECT count(*) FROM positions').fetchone()[0]==0
        new_hash=password_hash.hash('Changed1');db.execute('UPDATE users SET password_hash=?',(new_hash,))
    run(path,'-m','alembic','upgrade','head');run(path,'-m','app.scripts.init_data')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT password_hash FROM users').fetchone()[0]==new_hash
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]

def test_legacy_upgrade_preserves_ids_credentials_money_punches_and_accounts(tmp_path):
    path=tmp_path/'legacy.sqlite3';old_hash=password_hash.hash('Legacy1')
    with sqlite3.connect(path) as db:
        db.executescript('''
        CREATE TABLE departments(id INTEGER PRIMARY KEY,code VARCHAR(20) UNIQUE NOT NULL,name VARCHAR(50) UNIQUE NOT NULL,is_active BOOLEAN NOT NULL,description VARCHAR,created_at DATETIME NOT NULL);
        CREATE TABLE positions(id INTEGER PRIMARY KEY,code VARCHAR(20) UNIQUE NOT NULL,name VARCHAR(50) NOT NULL,department_id INTEGER NOT NULL REFERENCES departments(id),is_active BOOLEAN NOT NULL,description VARCHAR,created_at DATETIME NOT NULL,UNIQUE(department_id,name));
        CREATE TABLE employees(id INTEGER PRIMARY KEY,employee_no VARCHAR(20) UNIQUE NOT NULL,full_name VARCHAR(50) NOT NULL,gender VARCHAR,birth_date DATE,base_salary_cents INTEGER NOT NULL DEFAULT 0,phone VARCHAR,department_id INTEGER NOT NULL REFERENCES departments(id),position_id INTEGER NOT NULL REFERENCES positions(id),hire_date DATE NOT NULL,status VARCHAR NOT NULL,resignation_date DATE,remark VARCHAR,created_at DATETIME NOT NULL,updated_at DATETIME NOT NULL,CHECK(status IN ('active','resigned')),CHECK((status='active' AND resignation_date IS NULL) OR (status='resigned' AND resignation_date >= hire_date)));
        CREATE TABLE users(id INTEGER PRIMARY KEY,username VARCHAR(50) UNIQUE NOT NULL,password_hash VARCHAR NOT NULL,role VARCHAR NOT NULL,employee_id INTEGER UNIQUE REFERENCES employees(id),display_name VARCHAR,is_active BOOLEAN NOT NULL,created_at DATETIME NOT NULL,CONSTRAINT user_role_valid CHECK(role IN ('ADMIN','EMPLOYEE','admin')));
        INSERT INTO departments VALUES(1,'OLD','旧木工部门',1,NULL,CURRENT_TIMESTAMP);
        INSERT INTO positions VALUES(1,'OLDPOS','制琴师',1,1,NULL,CURRENT_TIMESTAMP);
        INSERT INTO employees VALUES(1,'OLD001','旧员工',NULL,NULL,0,NULL,1,1,'2026-01-01','active',NULL,NULL,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP);
        INSERT INTO employees VALUES(2,'OLD002','离职员工',NULL,NULL,0,NULL,1,1,'2026-01-01','resigned','2026-02-01',NULL,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP);
        UPDATE employees SET gender='male' WHERE id=1;
        ''')
        db.execute("INSERT INTO users VALUES(1,'ljm',?,'ADMIN',NULL,NULL,1,CURRENT_TIMESTAMP)",(old_hash,))
    run(path,'-m','alembic','upgrade','20261027_01')
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO payroll_records(employee_id,salary_month,base_salary_cents,bonus_cents,deduction_cents,net_salary_cents,status) VALUES(1,'2026-01',123456,0,0,123456,'unpaid')")
        db.execute("INSERT INTO attendance_records(employee_id,attendance_date,clock_in,clock_out,status,source) VALUES(1,'2026-01-05','09:00','18:00','normal','web')")
    run(path,'-m','alembic','upgrade','head');run(path,'-m','app.scripts.init_data')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM departments').fetchone()[0]==4
        assert db.execute('SELECT id,username,password_hash,role FROM users WHERE id=1').fetchone()==(1,'ljm',old_hash,'SYS_ADMIN')
        assert db.execute('SELECT count(*) FROM employees').fetchone()[0]==2
        assert 'gender' not in {row[1] for row in db.execute('PRAGMA table_info(employees)')}
        assert db.execute('SELECT count(*) FROM users WHERE employee_id IS NOT NULL').fetchone()[0]==2
        assert db.execute('SELECT is_active,disabled_reason FROM users WHERE employee_id=2').fetchone()==(0,'EMPLOYEE_LEFT')
        assert db.execute('SELECT amount FROM salaries').fetchone()[0]==1234.56
        assert db.execute('SELECT count(*) FROM punch_records').fetchone()[0]==2
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]
