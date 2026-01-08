import os
import base64
import uuid
import smtplib
from contextlib import asynccontextmanager
from email.message import EmailMessage

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    firstName = Column(String(100))
    lastName = Column(String(100))
    email = Column(String(255), unique=True)
    studentId = Column(String(50), unique=True)
    password = Column(String(255))
    reset_token = Column(String(255), nullable=True)
    is_verified = Column(Integer, default=0)  
    verification_token = Column(String(255), nullable=True)

class User(BaseModel):
    firstName: str
    lastName: str
    email: str
    studentId: str
    password: str

class UserLogin(BaseModel):
    studentId: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ResendVerificationRequest(BaseModel):
    email: str

async def send_auth_email(email: str, subject: str, body: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM")

    if not all([smtp_host, smtp_user, smtp_password]):
        print(f"SMTP Error: Credentials not fully configured in .env for {subject}")
        raise HTTPException(status_code=500, detail="Mail server not configured")

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = email

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        
        with server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"SMTP error details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register")
async def register(user: User):
    async with async_session() as session:
        result = await session.execute(
            select(UserDB).where(
                (UserDB.studentId == user.studentId) | (UserDB.email == user.email)
            )
        )
        existing_user = result.scalars().first()
        if existing_user:
            if existing_user.studentId == user.studentId:
                raise HTTPException(status_code=400, detail="Student ID already registered")
            else:
                raise HTTPException(status_code=400, detail="Email already registered")
        
        encoded_password = base64.b64encode(user.password.encode()).decode()
        verification_token = uuid.uuid4().hex
        new_user = UserDB(
            firstName=user.firstName,
            lastName=user.lastName,
            email=user.email,
            studentId=user.studentId,
            password=encoded_password,
            is_verified=0,
            verification_token=verification_token
        )
        session.add(new_user)
        await session.commit()
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        verify_link = f"{frontend_url}/verify-email?token={verification_token}"
        await send_auth_email(
            user.email, 
            "Verify Your Email", 
            f"Click the link to verify your email address: {verify_link}"
        )
        
        return {"message": "User registered successfully. Please check your email to verify your account."}

@app.post("/login")
async def login(user_login: UserLogin):
    async with async_session() as session:
        encoded_password = base64.b64encode(user_login.password.encode()).decode()
        result = await session.execute(
            select(UserDB).where(
                UserDB.studentId == user_login.studentId,
                UserDB.password == encoded_password
            )
        )
        user = result.scalars().first()
        
        if user:
            if not user.is_verified:
                raise HTTPException(
                    status_code=403, 
                    detail={"message": "Email not verified", "email": user.email}
                )
                
            return {
                "message": "Login successful",
                "user": {
                    "firstName": user.firstName,
                    "lastName": user.lastName,
                    "studentId": user.studentId
                }
            }
        
    raise HTTPException(status_code=401, detail="Invalid student ID or password")

@app.get("/verify-email")
async def verify_email(token: str):
    async with async_session() as session:
        result = await session.execute(select(UserDB).where(UserDB.verification_token == token))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        user.is_verified = 1
        user.verification_token = None
        await session.commit()
        return {"message": "Email verified successfully"}

@app.post("/resend-verification")
async def resend_verification(req: ResendVerificationRequest):
    async with async_session() as session:
        result = await session.execute(select(UserDB).where(UserDB.email == req.email))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Email not found")
        
        if user.is_verified:
            return {"message": "Email is already verified"}
        
        token = uuid.uuid4().hex
        user.verification_token = token
        await session.commit()
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        verify_link = f"{frontend_url}/verify-email?token={token}"
        await send_auth_email(
            user.email, 
            "Verify Your Email", 
            f"Click the link to verify your email address: {verify_link}"
        )
        return {"message": "Verification email resent"}

@app.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    async with async_session() as session:
        result = await session.execute(select(UserDB).where(UserDB.email == req.email))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Email not found")
        
        token = uuid.uuid4().hex
        user.reset_token = token
        await session.commit()
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{frontend_url}/reset-password?token={token}"
        await send_auth_email(user.email, "Password Reset", f"Click the link to reset your password: {reset_link}")
        return {"message": "Reset email sent"}

@app.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    async with async_session() as session:
        result = await session.execute(select(UserDB).where(UserDB.reset_token == req.token))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        
        encoded_password = base64.b64encode(req.new_password.encode()).decode()
        user.password = encoded_password
        user.reset_token = None
        await session.commit()
        return {"message": "Password reset successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
