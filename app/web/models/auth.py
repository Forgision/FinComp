from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class SMTPConfig(BaseModel):
    smtp_server: Optional[str] = Field(None, description="SMTP server address")
    smtp_port: Optional[int] = Field(None, description="SMTP server port")
    smtp_username: Optional[str] = Field(None, description="SMTP username")
    smtp_password: Optional[str] = Field(None, description="SMTP password")
    smtp_use_tls: bool = Field(True, description="Use TLS for SMTP connection")
    smtp_from_email: Optional[EmailStr] = Field(None, description="From email address")
    smtp_helo_hostname: Optional[str] = Field(None, description="HELO/EHLO hostname")

class SMTPTest(BaseModel):
    test_email: EmailStr = Field(..., description="Email address to send a test email to")

class SMTPDebug(BaseModel):
    success: bool
    message: str
    details: List[str]