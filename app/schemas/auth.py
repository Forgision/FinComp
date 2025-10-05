from pydantic import BaseModel, EmailStr
from typing import Optional

class UserLogin(BaseModel):
    username: str
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class TOTPVerification(BaseModel):
    email: EmailStr
    totp_code: str

class NewPassword(BaseModel):
    email: EmailStr
    token: str
    password: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

class SMTPSettings(BaseModel):
    smtp_server: str
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = False
    smtp_from_email: EmailStr
    smtp_helo_hostname: Optional[str] = None

class TestEmail(BaseModel):
    test_email: EmailStr