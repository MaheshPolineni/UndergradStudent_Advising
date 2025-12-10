from sqlalchemy import Column, Integer, String
from database import Base
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Survey(Base):
    __tablename__ = "survey"

    id = Column(Integer, primary_key=True, index=True)
    user_type = Column(String(100))
    name = Column(String(100))
    email = Column(String(100), unique=True)
    course_suggestion = Column(String(100))
    chatbot = Column(String(100))
    features = Column(String(100))
    suggestions = Column(String(300))
