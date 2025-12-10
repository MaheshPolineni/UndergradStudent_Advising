from pydantic import BaseModel

class UserSurvey(BaseModel):
    name: str
    email: str
    user_type:str
    id:str
    course_suggestion:str
    chatbot:str
    features:str
    suggestions:str
