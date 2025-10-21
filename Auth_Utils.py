# import os
# from passlib.context import CryptContext
# from jose import JWTError,jwt
# from datetime import datetime,timedelta
# from dotenv import load_dotenv

# secret_key=os.getenv("SECRET_KEY")
# algorithm=os.getenv("ALGORITHM")
# access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# pwd_context=CryptContext(schemes=["bcrypt"],deprecated="auto")


# def hash_password(password: str) -> str:
#     return pwd_context.hash(password)


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password,hashed_password)

# def create_access_token(data: dict, expires_delta: timedelta = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=access_token_expire_minutes))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, secret_key, algorithm)

# def decode_token(token: str):
#     try:
#         payload = jwt.decode(token, secret_key, algorithms=[algorithm])
#         return payload
#     except JWTError:
#         return None