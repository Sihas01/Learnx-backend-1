import os
import base64
import uuid
import smtplib
from contextlib import asynccontextmanager
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from google.oauth2 import id_token
from google.auth.transport import requests

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
    studentId = Column(String(50), unique=True, nullable=True)
    password = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=True)
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

class GoogleLoginRequest(BaseModel):
    token: str
    studentId: str = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; }}
        .header {{ background-color: #ffffff; padding: 30px; text-align: center; border-bottom: 2px solid #f0f0f0; }}
        .content {{ padding: 40px; color: #333333; line-height: 1.6; }}
        .content h2 {{ color: #2c3e50; margin-top: 0; font-size: 24px; }}
        .content p {{ font-size: 16px; margin-bottom: 25px; }}
        .button-container {{ text-align: center; margin-top: 35px; }}
        .button {{ background: linear-gradient(135deg, #6e8efb, #a777e3); color: #ffffff !important; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 16px; display: inline-block; transition: transform 0.2s; box-shadow: 0 4px 15px rgba(110, 142, 251, 0.3); }}
        .footer {{ background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 13px; color: #888888; border-top: 1px solid #eeeeee; }}
        .footer p {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="cid:logo" alt="learnX Logo" width="160">
        </div>
        <div class="content">
            <h2>{title}</h2>
            <p>{message}</p>
            <div class="button-container">
                <a href="{link}" class="button">{button_text}</a>
            </div>
        </div>
        <div class="footer">
            <p>&copy; 2026 learnX. All rights reserved.</p>
            <p>Empowering your learning journey.</p>
        </div>
    </div>
</body>
</html>
"""

async def send_auth_email(email: str, subject: str, message_text: str, title: str, button_text: str, link: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM")

    if not all([smtp_host, smtp_user, smtp_password]):
        print(f"SMTP Error: Credentials not fully configured in .env for {subject}")
        raise HTTPException(status_code=500, detail="Mail server not configured")

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = email

    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)

    # Plain text version
    part_text = MIMEText(f"{title}\\n\\n{message_text}\\n\\n{link}", "plain")
    msg_alternative.attach(part_text)

    # HTML version
    html_content = HTML_TEMPLATE.format(
        title=title,
        message=message_text,
        button_text=button_text,
        link=link
    )
    part_html = MIMEText(html_content, "html")
    msg_alternative.attach(part_html)

    # Attach logo as inline image
    logo_path = os.path.join(os.path.dirname(__file__), "..", "learnX", "public", "logo.png")
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                logo_data = f.read()
                logo_image = MIMEImage(logo_data)
                logo_image.add_header("Content-ID", "<logo>")
                logo_image.add_header("Content-Disposition", "inline", filename="logo.png")
                msg.attach(logo_image)
        except Exception as e:
            print(f"Failed to attach logo: {e}")

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
            "Thank you for registering with learnX. Please verify your email address to get started.",
            "Welcome to learnX!",
            "Verify Email",
            verify_link
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

@app.post("/google-login")
async def google_login(req: GoogleLoginRequest):
    try:
        # First try to verify as ID token
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        try:
            idinfo = id_token.verify_oauth2_token(req.token, requests.Request(), client_id)
            email = idinfo['email']
            google_id = idinfo['sub']
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
        except Exception:
            # If ID token verification fails, try as access token by fetching user info
            import httpx
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {req.token}"}
                )
                if res.status_code != 200:
                    raise HTTPException(status_code=400, detail="Invalid Google token")
                userinfo = res.json()
                email = userinfo['email']
                google_id = userinfo['sub']
                first_name = userinfo.get('given_name', '')
                last_name = userinfo.get('family_name', '')
        
        async with async_session() as session:
            # Check if user exists by google_id
            result = await session.execute(select(UserDB).where(UserDB.google_id == google_id))
            user = result.scalars().first()
            
            is_new_user = False
            if not user:
                # Check if user exists by email (link account)
                result = await session.execute(select(UserDB).where(UserDB.email == email))
                user = result.scalars().first()
                
                if user:
                    user.google_id = google_id
                    user.is_verified = 1 # Google users are verified
                    if req.studentId and not user.studentId:
                        user.studentId = req.studentId
                else:
                    is_new_user = True
                    # Create new user
                    user = UserDB(
                        firstName=first_name,
                        lastName=last_name,
                        email=email,
                        google_id=google_id,
                        studentId=req.studentId,
                        is_verified=1
                    )
                    session.add(user)
                
                await session.commit()
                await session.refresh(user)
            
            return {
                "message": "Login successful",
                "is_new_user": is_new_user,
                "user": {
                    "firstName": user.firstName,
                    "lastName": user.lastName,
                    "studentId": user.studentId or "Google User"
                }
            }
            
    except Exception as e:
        print(f"Google Token Verification Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid Google token")

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
            "You requested a new verification link. Please click the button below to verify your account.",
            "Verify Your Email",
            "Verify Email",
            verify_link
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
        await send_auth_email(
            user.email, 
            "Password Reset", 
            "We received a request to reset your password. If you didn't make this request, you can safely ignore this email.",
            "Reset Your Password",
            "Reset Password",
            reset_link
        )
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
