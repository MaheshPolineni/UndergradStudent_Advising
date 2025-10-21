# import os
# from sqlalchemy import create_engine
# from dotenv import load_dotenv
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.orm import declarative_base

# load_dotenv()

# # Base class for ORM
# Base = declarative_base()

# # MySQL connection settings
# username = os.getenv("DB_USERNAME")
# password = os.getenv("DB_PASSWORD")
# host = os.getenv('DB_HOST')
# port = os.getenv('DB_PORT')
# database = os.getenv('DB_NAME')

# # Create engine for MySQL
# engine = create_engine(
#     f'mysql+pymysql://{username}:{password}@{host}:{port}/{database}',
#     echo=True
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 
