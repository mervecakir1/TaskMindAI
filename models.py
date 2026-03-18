from database import Base
from sqlalchemy import Column, INTEGER, String, Boolean, ForeignKey


class ToDo(Base):
    __tablename__ = 'todos'
    id = Column(INTEGER,primary_key= True, index= True)
    title = Column(String)
    description = Column(String)
    priority = Column(INTEGER)
    complete = Column(Boolean, default= False)
    owner_id = Column(INTEGER,ForeignKey('users.id'))

class User(Base):
    __tablename__= 'users'

    id = Column(INTEGER,primary_key= True, index= True)
    email = Column(String, unique= True)
    username = Column(String, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default= True)
    role = Column(String)
    phone_number = Column(String)
