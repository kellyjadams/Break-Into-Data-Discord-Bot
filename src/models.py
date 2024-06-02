import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String, 
    DateTime,
    Float, 
    Boolean, 
    ForeignKey, 
    BigInteger, 
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func


Base = declarative_base()


class TimeZoneEnum(enum.Enum):
    North_America = -5
    South_America = -3
    Europe = 1
    Asia = 5
    Africa = 3
    Oceania = 11


class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    email = Column(String, nullable=True)
    name = Column(String, nullable=True)
    last_llm_submission = Column(DateTime(timezone=True), nullable=True)
    time_zone_shift = Column(Integer, nullable=True)
    
    # Reverse relations are defined in the related models
    submissions = relationship("Submission", back_populates="user")
    goals = relationship("Goal", back_populates="user")
    

class Submission(Base):
    __tablename__ = 'submissions'

    submission_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    goal_id = Column(Integer, ForeignKey('goals.goal_id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    proof_url = Column(String, nullable=True)
    amount = Column(Float)
    is_voice = Column(Boolean, default=False)
    voice_channel = Column(String, nullable=True)

    user = relationship("User", back_populates="submissions")
    goal = relationship("Goal", back_populates="submissions")


class Category(Base):
    __tablename__ = 'categories'

    category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    text_channel = Column(String)
    voice_channel = Column(String)
    allow_llm_submissions = Column(Boolean, default=True)

    goals = relationship("Goal", back_populates="category")


class Goal(Base):
    __tablename__ = 'goals'

    goal_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    category_id = Column(Integer, ForeignKey('categories.category_id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    goal_description = Column(String)
    frequency = Column(String)
    metric = Column(String)
    target = Column(Float)
    active = Column(Boolean, default=True)

    user = relationship("User", back_populates="goals")
    category = relationship("Category", back_populates="goals")
    submissions = relationship("Submission", back_populates="goal")


class Leaderboard(Base):
    __tablename__ = 'leaderboards'
    
    leaderboard_id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    name = Column(String, nullable=False)
    voice_channels = Column(String, nullable=False)
    last_sent = Column(DateTime(timezone=True), nullable=True)
