from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, StringConstraints, Field, model_validator, AliasChoices
from decimal import Decimal

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Code = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r'^[A-Za-z0-9_-]{2,20}$')]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r'^\+?[0-9 ()-]{5,25}$')]

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Login(Input):
    username: Name
    password: str = Field(min_length=1, max_length=256)
    model_config = ConfigDict(extra='forbid')

class DictionaryCreate(Input):
    code: Code | None = None
    name: Name
    is_active: bool = True
    description: str | None = Field(None, max_length=1000)

class DictionaryPatch(Input):
    code: Code | None = None
    name: Name | None = None
    is_active: bool | None = None
    description: str | None = Field(None, max_length=1000)

    @model_validator(mode='after')
    def no_null(self):
        if any(getattr(self, field) is None for field in self.model_fields_set - {'description'}):
            raise ValueError('字段不可为空')
        return self

class PositionCreate(DictionaryCreate):
    department_id: int = Field(gt=0)

class PositionPatch(DictionaryPatch):
    department_id: int | None = Field(default=None, gt=0)

class EmployeeCreate(Input):
    employee_no: Code | None = None
    full_name: Name = Field(validation_alias=AliasChoices('full_name','name'))
    birth_date: date | None = None
    base_salary: Decimal = Field(Decimal('0.00'), ge=0, max_digits=12, decimal_places=2)
    create_account: bool = False
    initial_password: str | None = None
    department_id: int = Field(gt=0)
    position_id: int = Field(gt=0)
    hire_date: date
    phone: Phone | None = None
    remark: str | None = Field(default=None, max_length=1000)

    @model_validator(mode='before')
    @classmethod
    def new_contract(cls,value):
        # Keep the old full_name adapter while enforcing the new public name contract.
        if isinstance(value,dict) and 'name' in value:
            if 'base_salary' not in value:raise ValueError('基本工资必填')
            if 'employee_no' in value or 'employee_code' in value:raise ValueError('员工编号由系统生成')
        return value

class EmployeePatch(Input):
    full_name: Name | None = Field(None, validation_alias=AliasChoices('full_name','name'))
    birth_date: date | None = None
    base_salary: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    department_id: int | None = Field(default=None, gt=0)
    position_id: int | None = Field(default=None, gt=0)
    hire_date: date | None = None
    phone: Phone | None = None
    remark: str | None = Field(default=None, max_length=1000)

    @model_validator(mode='after')
    def required_not_null(self):
        for field in self.model_fields_set - {'phone', 'remark','birth_date'}:
            if getattr(self, field) is None:
                raise ValueError('必填字段不可为空')
        return self

class Archive(Input):
    resignation_date: date = Field(validation_alias=AliasChoices('resignation_date','departure_date'))

class Proficiency(Input):
    proficiency: Literal['basic', 'skilled', 'expert']

class SkillBind(Proficiency):
    skill_id: int = Field(gt=0)
