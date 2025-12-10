from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# URL to your MySQL database
DATABASE_URL = "mysql+asyncmy://Mahesh:Mahesh@123@localhost:3306/lu"

# Creates the connection engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Database session (used inside routes)
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
async def get_db():
    async with SessionLocal() as session:
        yield session
