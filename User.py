# from sqlalchemy import Column, Integer, String
# from sqlalchemy.orm import sessionmaker
# # from DatabaseConnection import engine,Base
# from Auth_Utils import hash_password,verify_password

# # Define a model (table)
# class User(Base):
#     __tablename__ = 'user'

#     L_id = Column(String(50), primary_key=True)
#     username = Column(String(50))
#     password = Column(String(100))
#     L_email = Column(String(50))

# # # Create a session
# # Session = sessionmaker(bind=engine)
# # session = Session()

# # # Add a new user
# # new_user = User(L_id="L20586751",username="Mahesh", password=hash_password("Mahesh@123"),L_email="mpoli@email.com")
# # session.add(new_user)
# # session.commit()

# # # Query the user
# # user = session.query(User).filter_by(name="Mahesh").first()
# # print(user.usernamename, user.L_id,verify_password("Mahesh@123",user.password))

