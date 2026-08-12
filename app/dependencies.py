from fastapi import Depends, HTTPException, status
import jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Employee, UserRole
from app.security import ALGORITHM, bearer_scheme


def get_current_employee(credentials=Depends(bearer_scheme), db: Session = Depends(get_db)) -> Employee:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    try:
        payload = jwt.decode(credentials.credentials, get_settings().secret_key, algorithms=[ALGORITHM])
        employee_id = int(payload.get("sub", ""))
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception
    employee = db.get(Employee, employee_id)
    if not employee or not employee.is_active:
        raise credentials_exception
    return employee


def require_admin(current: Employee = Depends(get_current_employee)) -> Employee:
    if current.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return current

