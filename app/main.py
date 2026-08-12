from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.config import get_settings
from app.dependencies import get_current_employee, require_admin
from app.models import Attendance, AuditLog, Department, Employee, LeaveRequest, LeaveStatus, Payroll, PayrollStatus, UserRole
from app.schemas import AttendanceOut, AuditLogOut, DepartmentCreate, DepartmentOut, DepartmentUpdate, EmployeeCreate, EmployeeOut, EmployeeUpdate, LeaveRequestCreate, LeaveRequestOut, LeaveRequestReview, LoginRequest, PayrollCreate, PayrollOut, Token
from app.security import create_access_token, hash_password, verify_password


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    with Session(engine) as db:
        if not db.scalar(select(Employee).where(Employee.email == settings.initial_admin_email)):
            if not settings.initial_admin_password:
                raise RuntimeError("Set INITIAL_ADMIN_PASSWORD in .env before first startup.")
            db.add(Employee(first_name="System", last_name="Administrator", email=settings.initial_admin_email, hashed_password=hash_password(settings.initial_admin_password), role=UserRole.ADMIN, job_title="Administrator"))
            db.commit()
    yield


app = FastAPI(title="AR Brands Employee Management API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


def log_action(db: Session, actor_id: int | None, action: str, entity_type: str, entity_id: int | None, details: str | None = None):
    db.add(AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details))


@app.post("/api/v1/auth/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    employee = db.scalar(select(Employee).where(Employee.email == payload.email))
    if not employee or not employee.is_active or not verify_password(payload.password, employee.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return Token(access_token=create_access_token(str(employee.id)))


@app.post("/api/v1/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), _: Employee = Depends(require_admin)):
    department = Department(**payload.model_dump())
    db.add(department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Department name already exists")
    db.refresh(department)
    return department


@app.get("/api/v1/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _: Employee = Depends(get_current_employee)):
    return list(db.scalars(select(Department).order_by(Department.name)))


@app.patch("/api/v1/departments/{department_id}", response_model=DepartmentOut)
def update_department(department_id: int, payload: DepartmentUpdate, db: Session = Depends(get_db), _: Employee = Depends(require_admin)):
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    for field, value in payload.model_dump(exclude_unset=True).items(): setattr(department, field, value)
    db.commit(); db.refresh(department)
    return department


@app.delete("/api/v1/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(department_id: int, db: Session = Depends(get_db), _: Employee = Depends(require_admin)):
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    db.delete(department); db.commit()


@app.post("/api/v1/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), _: Employee = Depends(require_admin)):
    values = payload.model_dump(exclude={"password"})
    if values["department_id"] and not db.get(Department, values["department_id"]):
        raise HTTPException(status_code=404, detail="Department not found")
    employee = Employee(**values, hashed_password=hash_password(payload.password))
    db.add(employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered")
    db.refresh(employee)
    return employee


@app.get("/api/v1/employees", response_model=list[EmployeeOut])
def list_employees(skip: int = 0, limit: int = Query(default=50, le=100), db: Session = Depends(get_db), _: Employee = Depends(require_admin)):
    return list(db.scalars(select(Employee).order_by(Employee.id).offset(skip).limit(limit)))


@app.get("/api/v1/employees/me", response_model=EmployeeOut)
def read_my_profile(current: Employee = Depends(get_current_employee)):
    return current


@app.get("/api/v1/employees/{employee_id}", response_model=EmployeeOut)
def read_employee(employee_id: int, db: Session = Depends(get_db), current: Employee = Depends(get_current_employee)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if current.role != UserRole.ADMIN and current.id != employee_id:
        raise HTTPException(status_code=403, detail="You can only view your own profile")
    return employee


@app.patch("/api/v1/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db), current: Employee = Depends(get_current_employee)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    updates = payload.model_dump(exclude_unset=True)
    if current.role != UserRole.ADMIN:
        if current.id != employee_id:
            raise HTTPException(status_code=403, detail="You can only update your own profile")
        updates = {key: value for key, value in updates.items() if key in {"first_name", "last_name", "phone"}}
    if updates.get("department_id") and not db.get(Department, updates["department_id"]):
        raise HTTPException(status_code=404, detail="Department not found")
    for field, value in updates.items(): setattr(employee, field, value)
    db.commit(); db.refresh(employee)
    return employee


@app.delete("/api/v1/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: int, db: Session = Depends(get_db), current: Employee = Depends(require_admin)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.id == current.id:
        raise HTTPException(status_code=400, detail="Administrators cannot delete their own account")
    db.delete(employee); db.commit()


@app.post("/api/v1/attendance/check-in", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def check_in(db: Session = Depends(get_db), current: Employee = Depends(get_current_employee)):
    today = date.today()
    if db.scalar(select(Attendance).where(Attendance.employee_id == current.id, Attendance.attendance_date == today)):
        raise HTTPException(status_code=409, detail="You have already checked in today")
    record = Attendance(employee_id=current.id, attendance_date=today)
    db.add(record); log_action(db, current.id, "check_in", "attendance", None)
    db.commit(); db.refresh(record)
    return record


@app.patch("/api/v1/attendance/check-out", response_model=AttendanceOut)
def check_out(db: Session = Depends(get_db), current: Employee = Depends(get_current_employee)):
    record = db.scalar(select(Attendance).where(Attendance.employee_id == current.id, Attendance.attendance_date == date.today()))
    if not record:
        raise HTTPException(status_code=404, detail="No check-in found for today")
    if record.check_out:
        raise HTTPException(status_code=409, detail="You have already checked out today")
    record.check_out = datetime.now(timezone.utc); log_action(db, current.id, "check_out", "attendance", record.id)
    db.commit(); db.refresh(record)
    return record


@app.get("/api/v1/attendance", response_model=list[AttendanceOut])
def list_attendance(employee_id: int | None = None, db: Session = Depends(get_db), current: Employee = Depends(get_current_employee)):
    statement = select(Attendance).order_by(Attendance.attendance_date.desc())
    if current.role == UserRole.ADMIN:
        if employee_id: statement = statement.where(Attendance.employee_id == employee_id)
    else: statement = statement.where(Attendance.employee_id == current.id)
    return list(db.scalars(statement))


@app.post("/api/v1/leave-requests", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def create_leave_request(payload: LeaveRequestCreate, db: Session = Depends(get_db), current: Employee = Depends(get_current_employee)):
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="End date must be on or after start date")
    request = LeaveRequest(employee_id=current.id, **payload.model_dump())
    db.add(request); log_action(db, current.id, "create", "leave_request", None, payload.leave_type)
    db.commit(); db.refresh(request)
    return request


@app.get("/api/v1/leave-requests", response_model=list[LeaveRequestOut])
def list_leave_requests(db: Session = Depends(get_db), current: Employee = Depends(get_current_employee)):
    statement = select(LeaveRequest).order_by(LeaveRequest.created_at.desc())
    if current.role != UserRole.ADMIN: statement = statement.where(LeaveRequest.employee_id == current.id)
    return list(db.scalars(statement))


@app.patch("/api/v1/leave-requests/{request_id}/review", response_model=LeaveRequestOut)
def review_leave_request(request_id: int, payload: LeaveRequestReview, db: Session = Depends(get_db), current: Employee = Depends(require_admin)):
    request = db.get(LeaveRequest, request_id)
    if not request: raise HTTPException(status_code=404, detail="Leave request not found")
    if payload.status == LeaveStatus.PENDING: raise HTTPException(status_code=422, detail="A review must approve or reject the request")
    request.status = payload.status; request.reviewed_by = current.id; log_action(db, current.id, payload.status.value, "leave_request", request.id)
    db.commit(); db.refresh(request)
    return request


@app.post("/api/v1/payroll", response_model=PayrollOut, status_code=status.HTTP_201_CREATED)
def create_payroll(payload: PayrollCreate, db: Session = Depends(get_db), current: Employee = Depends(require_admin)):
    if not db.get(Employee, payload.employee_id): raise HTTPException(status_code=404, detail="Employee not found")
    payroll = Payroll(**payload.model_dump(), net_salary=payload.basic_salary - payload.deductions)
    db.add(payroll); log_action(db, current.id, "create", "payroll", None, str(payload.pay_period))
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Payroll already exists for this employee and period")
    db.refresh(payroll)
    return payroll


@app.get("/api/v1/payroll", response_model=list[PayrollOut])
def list_payroll(db: Session = Depends(get_db), current: Employee = Depends(get_current_employee)):
    statement = select(Payroll).order_by(Payroll.pay_period.desc())
    if current.role != UserRole.ADMIN: statement = statement.where(Payroll.employee_id == current.id)
    return list(db.scalars(statement))


@app.patch("/api/v1/payroll/{payroll_id}/mark-paid", response_model=PayrollOut)
def mark_payroll_paid(payroll_id: int, db: Session = Depends(get_db), current: Employee = Depends(require_admin)):
    payroll = db.get(Payroll, payroll_id)
    if not payroll: raise HTTPException(status_code=404, detail="Payroll record not found")
    payroll.status = PayrollStatus.PAID; payroll.paid_at = datetime.now(timezone.utc); log_action(db, current.id, "mark_paid", "payroll", payroll.id)
    db.commit(); db.refresh(payroll)
    return payroll


@app.get("/api/v1/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(db: Session = Depends(get_db), _: Employee = Depends(require_admin)):
    return list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)))
