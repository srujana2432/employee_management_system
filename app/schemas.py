from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import LeaveStatus, PayrollStatus, UserRole


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class DepartmentOut(DepartmentCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    job_title: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    department_id: int | None = None
    role: UserRole = UserRole.EMPLOYEE


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    job_title: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    department_id: int | None = None
    is_active: bool | None = None
    role: UserRole | None = None


class EmployeeOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    job_title: str | None
    phone: str | None
    department_id: int | None
    role: UserRole
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AttendanceOut(BaseModel):
    id: int; employee_id: int; attendance_date: date; check_in: datetime; check_out: datetime | None; status: str
    model_config = ConfigDict(from_attributes=True)


class LeaveRequestCreate(BaseModel):
    leave_type: str = Field(min_length=2, max_length=40)
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=1000)


class LeaveRequestReview(BaseModel):
    status: LeaveStatus


class LeaveRequestOut(LeaveRequestCreate):
    id: int; employee_id: int; status: LeaveStatus; reviewed_by: int | None; created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PayrollCreate(BaseModel):
    employee_id: int
    pay_period: date
    basic_salary: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    deductions: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class PayrollOut(BaseModel):
    id: int; employee_id: int; pay_period: date; basic_salary: Decimal; deductions: Decimal; net_salary: Decimal
    status: PayrollStatus; paid_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class AuditLogOut(BaseModel):
    id: int; actor_id: int | None; action: str; entity_type: str; entity_id: int | None; details: str | None; created_at: datetime
    model_config = ConfigDict(from_attributes=True)
