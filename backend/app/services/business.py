from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert
from app.models import NumberSequence, AuditLog, Employee
from app.core.errors import fail

def next_code(db, model, prefix, column='code'):
    while True:
        number = db.scalar(insert(NumberSequence).values(key=prefix, value=1).on_conflict_do_update(index_elements=['key'], set_={'value':NumberSequence.value+1}).returning(NumberSequence.value))
        code = f'{prefix}{number:06d}'
        if not db.scalar(select(model.id).where(getattr(model,column)==code)):
            return code

def cents(value):
    number = Decimal(str(value))
    if number < 0 or number > Decimal('9999999999.99') or number != number.quantize(Decimal('.01')):
        fail(422,'INVALID_AMOUNT','金额必须为非负且最多两位小数')
    return int(number*100)

def money(value):
    return f'{Decimal(value)/100:.2f}'

def month_range(month):
    try:
        start = datetime.strptime(month,'%Y-%m').date().replace(day=1)
        if start.strftime('%Y-%m') != month:
            raise ValueError()
        end = (start.replace(day=28)+timedelta(days=4)).replace(day=1)
        return start,end
    except (ValueError,TypeError):
        fail(422,'INVALID_MONTH','月份格式应为YYYY-MM')

def working_days(start,end):
    if end < start or (end-start).days > 366:
        fail(422,'INVALID_RANGE','日期范围无效或超过一年')
    return [start+timedelta(days=i) for i in range((end-start).days+1) if (start+timedelta(days=i)).weekday()<5]

def audit(db,user,action,kind,id,summary):
    db.add(AuditLog(actor_user_id=user.id,action=action,target_type=kind,target_id=id,summary=summary))

def page_result(db,query,page,page_size,view):
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.scalars(query.offset((page-1)*page_size).limit(page_size))
    return {'data':[view(row) for row in rows], 'total':total,'page':page,'page_size':page_size}
