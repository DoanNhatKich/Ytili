"""
KYC (Know Your Customer) verification service
"""
import os
import uuid
from typing import Optional, Dict, Any
import pytesseract
from PIL import Image
import json
import re
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import KYCDocument, User
from ..core.config import settings


class KYCService:
    """Service for KYC document processing and verification"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def process_document(
        self,
        user_id: int,
        document_type: str,
        file_content: bytes,
        original_filename: str
    ) -> KYCDocument:
        """Process uploaded KYC document"""
        
        # Save file to disk
        file_path = await self._save_file(file_content, original_filename)
        
        # Extract text using OCR
        extracted_data = await self._extract_text_from_image(file_path)
        
        # Parse extracted data based on document type
        parsed_data = await self._parse_document_data(document_type, extracted_data)
        
        # Create KYC document record
        kyc_document = KYCDocument(
            user_id=user_id,
            document_type=document_type,
            file_path=file_path,
            original_filename=original_filename,
            extracted_data=json.dumps(parsed_data)
        )
        
        self.db.add(kyc_document)
        await self.db.commit()
        await self.db.refresh(kyc_document)
        
        return kyc_document
    
    async def _save_file(self, file_content: bytes, original_filename: str) -> str:
        """Save uploaded file to disk"""
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(settings.UPLOAD_FOLDER, "kyc")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return file_path
    
    async def _extract_text_from_image(self, file_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            # Open image
            image = Image.open(file_path)
            
            # Use Tesseract OCR to extract text
            # Configure for Vietnamese and English
            custom_config = r'--oem 3 --psm 6 -l vie+eng'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            return text.strip()
        
        except Exception as e:
            print(f"OCR extraction failed: {e}")
            return ""
    
    async def _parse_document_data(self, document_type: str, text: str) -> Dict[str, Any]:
        """Parse extracted text based on document type"""
        parsed_data = {
            "raw_text": text,
            "document_type": document_type,
            "extracted_fields": {}
        }
        
        if document_type == "national_id":
            parsed_data["extracted_fields"] = self._parse_national_id(text)
        elif document_type == "medical_license":
            parsed_data["extracted_fields"] = self._parse_medical_license(text)
        elif document_type == "business_license":
            parsed_data["extracted_fields"] = self._parse_business_license(text)
        elif document_type == "tax_certificate":
            parsed_data["extracted_fields"] = self._parse_tax_certificate(text)
        
        return parsed_data
    
    def _parse_national_id(self, text: str) -> Dict[str, str]:
        """Parse Vietnamese national ID card"""
        fields = {}
        
        # Common patterns for Vietnamese ID cards
        patterns = {
            "id_number": r"(\d{9}|\d{12})",  # 9 or 12 digit ID
            "full_name": r"Họ và tên[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]+)",
            "date_of_birth": r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})",
            "place_of_birth": r"Nơi sinh[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s,]+)",
            "address": r"Nơi thường trú[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s,\d]+)"
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                fields[field] = match.group(1).strip()
        
        return fields
    
    def _parse_medical_license(self, text: str) -> Dict[str, str]:
        """Parse medical license document"""
        fields = {}
        
        patterns = {
            "license_number": r"(?:Số|Number)[:\s]*([A-Z0-9\/\-]+)",
            "doctor_name": r"(?:Họ và tên|Name)[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]+)",
            "specialization": r"(?:Chuyên khoa|Specialization)[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]+)",
            "issue_date": r"(?:Ngày cấp|Issue date)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})",
            "expiry_date": r"(?:Ngày hết hạn|Expiry date)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})"
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                fields[field] = match.group(1).strip()
        
        return fields
    
    def _parse_business_license(self, text: str) -> Dict[str, str]:
        """Parse business license document"""
        fields = {}
        
        patterns = {
            "license_number": r"(?:Số|Number)[:\s]*([A-Z0-9\/\-]+)",
            "business_name": r"(?:Tên doanh nghiệp|Business name)[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]+)",
            "business_type": r"(?:Loại hình|Type)[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]+)",
            "address": r"(?:Địa chỉ|Address)[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s,\d]+)",
            "issue_date": r"(?:Ngày cấp|Issue date)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})"
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                fields[field] = match.group(1).strip()
        
        return fields
    
    def _parse_tax_certificate(self, text: str) -> Dict[str, str]:
        """Parse tax certificate document"""
        fields = {}
        
        patterns = {
            "tax_id": r"(?:Mã số thuế|Tax ID)[:\s]*([0-9\-]+)",
            "organization_name": r"(?:Tên tổ chức|Organization)[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s]+)",
            "address": r"(?:Địa chỉ|Address)[:\s]*([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ\s,\d]+)",
            "issue_date": r"(?:Ngày cấp|Issue date)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})"
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                fields[field] = match.group(1).strip()
        
        return fields
    
    async def verify_document(
        self,
        document_id: int,
        verified_by: int,
        is_verified: bool,
        rejection_reason: Optional[str] = None
    ) -> bool:
        """Verify or reject a KYC document"""
        from ..services.user_service import UserService
        
        user_service = UserService(self.db)
        return await user_service.verify_kyc_document(
            document_id=document_id,
            verified_by=verified_by,
            is_verified=is_verified,
            rejection_reason=rejection_reason
        )
