from sqlalchemy import Column, String, Enum, UUID, Boolean
from sqlalchemy.orm import relationship
import uuid
import enum
from ..db import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    POWER_USER = "power_user"
    READER = "reader"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.READER)
    department = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    documents = relationship("Document", back_populates="owner")
