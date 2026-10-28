from datetime import date
from typing import Literal, Annotated
from decimal import Decimal
from pydantic import Field, model_validator, StringConstraints
from app.schemas import Input, Name, Code

EmployeeNo = Annotated[str, StringConstraints(strip_whitespace=True,pattern=r'^[A-Za-z0-9_-]{1,20}$')]

class PositionInput(Input):
    code: Code
    name: Name
    department_id: int = Field(gt=0)
    grade: Name
    is_active: bool = True
    description: str | None = Field(None,max_length=1000)

class EmployeeInput(Input):
    employee_no: EmployeeNo
    name: Name
    department_id: int = Field(gt=0)
    position_id: int = Field(gt=0)
    hire_date: date
    phone: str | None = Field(None,max_length=25)
    remarks: str | None = Field(None,max_length=1000)
    base_salary: Decimal = Field(Decimal('0.00'),ge=0,max_digits=12,decimal_places=2)

class Bootstrap(EmployeeInput):
    position_id: int | None = Field(None,gt=0)
    position_name: Name | None = None
    grade: Name = 'L3'

class RoleInput(Input):
    role: Literal['EMPLOYEE','SUPERVISOR','HR']

class UsernameInput(Input):
    username: Name

class ReasonInput(Input):
    reason: str = Field(min_length=1,max_length=500)

class DateInput(Input):
    event_date: date
    note: str | None = Field(None,max_length=1000)

class ResetPassword(Input):
    new_password: str = Field(max_length=128)

class SupervisorInput(Input):
    user_id: int = Field(gt=0)

class RecoverInput(Input):
    employee_id: int = Field(gt=0)

class EmployeePatch(Input):
    employee_no: EmployeeNo | None = None
    name: Name | None = None
    department_id: int | None = Field(None,gt=0)
    position_id: int | None = Field(None,gt=0)
    hire_date: date | None = None
    phone: str | None = Field(None,max_length=25)
    remarks: str | None = Field(None,max_length=1000)
    base_salary: Decimal | None = Field(None,ge=0,max_digits=12,decimal_places=2)

class PositionPatch(Input):
    code: Code | None = None
    name: Name | None = None
    department_id: int | None = Field(None,gt=0)
    grade: Name | None = None
    is_active: bool | None = None
    description: str | None = Field(None,max_length=1000)
