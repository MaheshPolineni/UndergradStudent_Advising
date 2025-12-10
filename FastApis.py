from fastapi import FastAPI, UploadFile, File, Form,Depends,HTTPException,Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import session
from Courses_Registration import course_suggestion
from fastapi.middleware.cors import CORSMiddleware
import os
# from User import Base,engine
# from DatabaseConnection import SessionLocal
from pydantic import BaseModel
# from User import User
# from Auth_Utils import hash_password,verify_password,create_access_token,decode_token
from typing import Optional, Dict
from uuid import uuid4
import time
import fitz  # PyMuPDF
import shutil
import uuid
from ChatBot import user_chain,chat_bot
from SurveyData import UserSurvey
from DataBaseConn import get_db
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI() 


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",     
        "http://127.0.0.1:3000",
        "*"       
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage
sessions: Dict[str, Dict] = {}
SESSION_TTL_SECONDS = 3600

class UserCreate(BaseModel):
    username:str
    password:str
    L_id:str
    L_email:str

class StoreSessionData(BaseModel):
    data:dict

class UserLogin(BaseModel):
    L_id:str
    password:str


user_sessions = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


# def get_db():
#     db=SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # Create all tables
# Base.metadata.create_all(engine)

def create_session() -> str:
    session_id = str(uuid4())
    sessions[session_id] = {
        "data": {},
        "created_at": time.time()
    }
    return session_id

# Your existing function — DO NOT CHANGE
def extract_text_from_pdf(pdf_path) -> str:
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_home():
    with open("static/index.html") as f:
        return f.read()

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    # Ensure it's a PDF
    if file.content_type != "application/pdf":
        return {"error": "Only PDF files are supported."}

    # Generate a unique temporary filename
    temp_filename = f"temp_{uuid.uuid4()}.pdf"

    # Save the uploaded file to disk
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Use your existing function
        extracted_text = extract_text_from_pdf(temp_filename)
    finally:
        # Clean up: delete temp file
        os.remove(temp_filename)

    return {"text": extracted_text}



@app.post("/course_registration_details")
async def read_root(term:str = Form(...),file: UploadFile = File(...)):
    print(f"Received term: {term}")
    print(f"Received file: {file.filename}")
    return {"message": await course_suggestion(file,term)}


# Store per-user sessions
user_sessions = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@app.post("/chat")
async def chat(request: ChatRequest):
    # 1. Check or create session
    session_id = request.session_id or str(uuid.uuid4())
    
    if session_id not in user_sessions:
        # Create a new memory + chain for this user
        chain = user_chain()
        user_sessions[session_id] = chain
    
    # 2. Run user's input through the chain
    chain = user_sessions[session_id]
    response = chat_bot(chain,request.message)
    
    # 3. Return response + session_id
    return {"session_id": session_id, "response": response}


@app.post("/survey")
async def save_survey(survey: UserSurvey, db: AsyncSession = Depends(get_db)):
    new_survey = UserSurvey(user_type=survey.user_type, id=survey.id ,email=survey.email, name=survey.name, course_suggestion=survey.course_suggestion,chatbot=survey.chatbot,features=survey.features, suggestions=survey.suggestions)
    db.add(new_survey)
    await db.commit()
    await db.refresh(new_survey)  # refresh to get id from db
    return "Thank you for the Survey!"


# @app.post("/sign_up")
# def signUp(user:UserCreate, db:session=Depends(get_db)):
#     existing=db.query(User).filter(User.L_id==user.L_id).first()
#     if existing:
#         raise HTTPException(status_code=400, detail="User already Exists")
#     hashed_password=hash_password(user.password)
#     new_user=User(username=user.username,password=hashed_password,L_id=user.L_id,L_email=user.L_email)
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
#     return {'L_id':user.L_id, 'L_email':user.L_email,'username':user.username}


# @app.post("/login")
# def login(user:UserLogin,db:session=Depends(get_db)):
#     existing_user = db.query(User).filter(User.L_id==user.L_id).first()
#     if not user or not verify_password(user.password,existing_user.password):
#         raise HTTPException(status_code=401, detail="Incorrect username or password")
#     token = create_access_token( data={"sub":existing_user.L_id})
#     return {"access_token": token, "token_type": "bearer","user":existing_user}


