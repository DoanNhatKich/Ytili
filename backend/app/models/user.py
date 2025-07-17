"""
User model for Ytili platform
Supports multi-tier user types: individual, hospital, organization
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..core.database import Base


class UserType(PyEnum):
    """User types as defined in ruleset"""
    INDIVIDUAL = "individual"
    HOSPITAL = "hospital"
    ORGANIZATION = "organization"
    # GOVERNMENT = "government"


class UserStatus(PyEnum):
    """User verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class User(Base):
    """Main user model supporting all user types"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Basic info
    full_name = Column(String(255), nullable=False)
    user_type = Column(Enum(UserType), nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING)
    
    # Verification
    is_email_verified = Column(Boolean, default=False)
    is_phone_verified = Column(Boolean, default=False)
    is_kyc_verified = Column(Boolean, default=False)
    
    # Organization specific fields
    organization_name = Column(String(255))  # For hospitals/organizations
    license_number = Column(String(100))  # Medical license for hospitals
    tax_id = Column(String(50))  # Tax ID for organizations
    
    # Location
    address = Column(Text)
    city = Column(String(100))
    province = Column(String(100))
    country = Column(String(100), default="Vietnam")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    donations = relationship("Donation", back_populates="donor")
    received_donations = relationship("Donation", back_populates="recipient")
    kyc_documents = relationship("KYCDocument", back_populates="user")
    points = relationship("UserPoints", back_populates="user", uselist=False)
    
    def __repr__(self):
        return f"<User {self.email} ({self.user_type.value})>"


class KYCDocument(Base):
    """KYC verification documents"""
    __tablename__ = "kyc_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    document_type = Column(String(50), nullable=False)  # ID, license, tax_cert
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255))
    
    # OCR extracted data
    extracted_data = Column(Text)  # JSON string of extracted information
    
    # Verification status
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(Integer, ForeignKey("users.id"))  # Admin who verified
    rejection_reason = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="kyc_documents")
    
    def __repr__(self):
        return f"<KYCDocument {self.document_type} for User {self.user_id}>"


class UserPoints(Base):
    """User points/rewards system"""
    __tablename__ = "user_points"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    total_points = Column(Integer, default=0)
    available_points = Column(Integer, default=0)  # Points that can be used
    lifetime_earned = Column(Integer, default=0)
    lifetime_spent = Column(Integer, default=0)
    
    # Tier system
    tier_level = Column(String(20), default="Bronze")  # Bronze, Silver, Gold, Platinum
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="points")
    
    def __repr__(self):
        return f"<UserPoints {self.available_points} for User {self.user_id}>"

