"""
Donation models for Ytili platform
Handles medication/supply donations and tracking
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..core.database import Base


class DonationType(PyEnum):
    """Types of donations"""
    MEDICATION = "medication"
    MEDICAL_SUPPLY = "medical_supply"
    FOOD = "food"
    CASH = "cash"


class DonationStatus(PyEnum):
    """Donation processing status"""
    PENDING = "pending"
    VERIFIED = "verified"
    MATCHED = "matched"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(PyEnum):
    """Payment processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Donation(Base):
    """Main donation record"""
    __tablename__ = "donations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Parties involved
    donor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"))  # Hospital/organization
    
    # Donation details
    donation_type = Column(Enum(DonationType), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # For medication/supply donations
    item_name = Column(String(255))
    quantity = Column(Integer)
    unit = Column(String(50))  # pieces, boxes, bottles, etc.
    expiry_date = Column(DateTime(timezone=True))
    batch_number = Column(String(100))
    manufacturer = Column(String(255))
    
    # For cash donations
    amount = Column(Numeric(10, 2))
    currency = Column(String(3), default="VND")
    
    # Status tracking
    status = Column(Enum(DonationStatus), default=DonationStatus.PENDING)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Verification and quality control
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(Integer, ForeignKey("users.id"))
    
    # Logistics
    pickup_address = Column(Text)
    delivery_address = Column(Text)
    tracking_number = Column(String(100))
    
    # Metadata
    images = Column(JSON)  # Array of image URLs
    documents = Column(JSON)  # Array of document URLs
    notes = Column(Text)
    
    # Points and rewards
    points_awarded = Column(Integer, default=0)

    # Blockchain tracking
    blockchain_status = Column(String(50), default="pending")  # pending, recorded, confirmed, failed
    blockchain_tx_hash = Column(String(66))  # Ethereum transaction hash
    blockchain_recorded_at = Column(DateTime(timezone=True))
    metadata_hash = Column(String(64))  # Hash of donation metadata for blockchain

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    donor = relationship("User", foreign_keys=[donor_id], back_populates="donations")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_donations")
    transactions = relationship("DonationTransaction", back_populates="donation")
    
    def __repr__(self):
        return f"<Donation {self.title} by User {self.donor_id}>"


class DonationTransaction(Base):
    """Transaction log for transparency"""
    __tablename__ = "donation_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("donations.id"), nullable=False)
    
    # Transaction details
    transaction_type = Column(String(50), nullable=False)  # created, verified, shipped, etc.
    description = Column(Text)
    
    # Actor
    actor_id = Column(Integer, ForeignKey("users.id"))  # Who performed this action
    actor_type = Column(String(50))  # system, user, admin
    
    # Transaction metadata
    transaction_metadata = Column(JSON)  # Additional transaction data
    
    # Blockchain-style hash for integrity
    transaction_hash = Column(String(64), unique=True, index=True)
    previous_hash = Column(String(64))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    donation = relationship("Donation", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction {self.transaction_type} for Donation {self.donation_id}>"


class MedicationCatalog(Base):
    """Catalog of approved medications and supplies"""
    __tablename__ = "medication_catalog"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic info
    name = Column(String(255), nullable=False, index=True)
    generic_name = Column(String(255))
    brand_names = Column(JSON)  # Array of brand names
    
    # Classification
    category = Column(String(100), nullable=False)  # medication, supply, food
    subcategory = Column(String(100))
    therapeutic_class = Column(String(100))
    
    # Regulatory
    registration_number = Column(String(100))  # Drug registration number
    is_prescription_required = Column(Boolean, default=False)
    is_controlled_substance = Column(Boolean, default=False)
    
    # Physical properties
    dosage_form = Column(String(100))  # tablet, capsule, injection, etc.
    strength = Column(String(100))  # 500mg, 10ml, etc.
    packaging = Column(String(100))  # box of 10, bottle of 100, etc.
    
    # Usage info
    indications = Column(Text)  # What it's used for
    contraindications = Column(Text)  # When not to use
    side_effects = Column(Text)
    storage_conditions = Column(Text)
    
    # Donation guidelines
    min_expiry_months = Column(Integer, default=6)  # Minimum months before expiry
    is_donation_allowed = Column(Boolean, default=True)
    donation_notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<MedicationCatalog {self.name}>"
