from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PayrollStatus(str, Enum):
    DRAFT = "draft"
    PAID = "paid"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.EMPLOYEE)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    department: Mapped[Department | None] = relationship(back_populates="employees")
    attendance_records: Mapped[list["Attendance"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(back_populates="employee", cascade="all, delete-orphan", foreign_keys="LeaveRequest.employee_id")
    payroll_records: Mapped[list["Payroll"]] = relationship(back_populates="employee", cascade="all, delete-orphan")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    attendance_date: Mapped[date] = mapped_column(Date, default=date.today)
    check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="present")
    employee: Mapped[Employee] = relationship(back_populates="attendance_records")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String(40))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[LeaveStatus] = mapped_column(SqlEnum(LeaveStatus), default=LeaveStatus.PENDING)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    employee: Mapped[Employee] = relationship(back_populates="leave_requests", foreign_keys=[employee_id])


class Payroll(Base):
    __tablename__ = "payroll"
    __table_args__ = (UniqueConstraint("employee_id", "pay_period", name="uq_payroll_employee_period"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    pay_period: Mapped[date] = mapped_column(Date)
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[PayrollStatus] = mapped_column(SqlEnum(PayrollStatus), default=PayrollStatus.DRAFT)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    employee: Mapped[Employee] = relationship(back_populates="payroll_records")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
