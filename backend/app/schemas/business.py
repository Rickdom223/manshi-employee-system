from datetime import date, time
from typing import Literal
from pydantic import Field, model_validator
from app.schemas import Input

class AttendanceInput(Input):
    employee_id: int = Field(gt=0)
    attendance_date: date
    clock_in: time | None = None
    clock_out: time | None = None
    status: Literal['normal','late','early_leave','absent','leave']
    @model_validator(mode='after')
    def order(self):
        if self.clock_in and self.clock_out and self.clock_out<self.clock_in:
            raise ValueError('下班时间不能早于上班时间')
        return self

class ContactInput(Input):
    phone: str = Field(pattern=r'^1[3-9]\d{9}$')
