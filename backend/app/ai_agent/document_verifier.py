"""
Document Verification System for Ytili AI Agent
OCR-based verification of medical documents and certificates
"""
import re
import json
import base64
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import structlog

try:
    import cv2
    import numpy as np
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    logger = structlog.get_logger()
    logger.warning("OCR libraries not available. Document verification will be limited.")

from ..core.supabase import get_supabase_service
from ..core.config import settings

logger = structlog.get_logger()


class DocumentVerifier:
    """
    OCR-based document verification system for medical certificates and records
    """
    
    def __init__(self):
        self.supabase = get_supabase_service()
        
        # Configure Tesseract path if provided
        if settings.TESSERACT_PATH and HAS_OCR:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
        
        # Valid document patterns for Vietnamese medical system
        self.document_patterns = {
            "hospital_names": [
                r"bệnh viện\s+[\w\s]+",
                r"phòng khám\s+[\w\s]+",
                r"trung tâm y tế\s+[\w\s]+",
                r"hospital\s+[\w\s]+",
                r"medical center\s+[\w\s]+"
            ],
            "doctor_signatures": [
                r"bác sĩ\s+[\w\s]+",
                r"bs\.?\s+[\w\s]+",
                r"dr\.?\s+[\w\s]+",
                r"thầy thuốc\s+[\w\s]+"
            ],
            "medical_license": [
                r"giấy phép hành nghề\s*:?\s*[\w\d]+",
                r"license\s*:?\s*[\w\d]+",
                r"chứng chỉ\s*:?\s*[\w\d]+"
            ],
            "dates": [
                r"\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}",
                r"\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{2,4}"
            ],
            "diagnosis_codes": [
                r"[A-Z]\d{2}\.?\d?",  # ICD-10 codes
                r"mã bệnh\s*:?\s*[\w\d]+"
            ],
            "hospital_stamps": [
                r"con dấu",
                r"stamp",
                r"seal"
            ]
        }
        
        # Known legitimate hospitals in Vietnam
        self.legitimate_hospitals = [
            "bệnh viện bạch mai",
            "bệnh viện chợ rẫy", 
            "bệnh viện k",
            "bệnh viện việt đức",
            "bệnh viện 108",
            "bệnh viện đại học y hà nội",
            "bệnh viện nhi trung ương",
            "bệnh viện tim hà nội"
        ]
        
        # Document quality thresholds
        self.quality_thresholds = {
            "min_resolution": (300, 300),
            "max_file_size": settings.MAX_DOCUMENT_SIZE,
            "min_text_confidence": 60,
            "min_extracted_text_length": 50
        }
    
    async def verify_document(
        self,
        document_path: str,
        document_type: str = "medical_certificate",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify a medical document using OCR and pattern matching
        
        Args:
            document_path: Path to the document image
            document_type: Type of document (medical_certificate, hospital_record, etc.)
            user_id: ID of user submitting the document
            
        Returns:
            Verification result with confidence score
        """
        try:
            if not HAS_OCR:
                return {
                    "success": False,
                    "error": "OCR libraries not available",
                    "verification_score": 0
                }
            
            # Load and preprocess image
            image_data = await self._load_and_preprocess_image(document_path)
            if not image_data["success"]:
                return image_data
            
            # Extract text using OCR
            ocr_result = await self._extract_text_ocr(image_data["processed_image"])
            if not ocr_result["success"]:
                return ocr_result
            
            # Analyze extracted text
            text_analysis = self._analyze_extracted_text(
                ocr_result["text"], document_type
            )
            
            # Verify document authenticity
            authenticity_check = self._verify_authenticity(
                ocr_result["text"], image_data["original_image"]
            )
            
            # Calculate overall verification score
            verification_score = self._calculate_verification_score(
                text_analysis, authenticity_check, ocr_result
            )
            
            # Generate verification result
            result = {
                "success": True,
                "verification_score": verification_score,
                "confidence_level": self._get_confidence_level(verification_score),
                "extracted_text": ocr_result["text"],
                "text_analysis": text_analysis,
                "authenticity_check": authenticity_check,
                "ocr_confidence": ocr_result["confidence"],
                "document_type": document_type,
                "verification_timestamp": datetime.now(timezone.utc).isoformat(),
                "requires_manual_review": verification_score < 70
            }
            
            # Save verification result
            if user_id:
                await self._save_verification_result(user_id, document_path, result)
            
            logger.info(
                "Document verification completed",
                document_type=document_type,
                verification_score=verification_score,
                user_id=user_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to verify document: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "verification_score": 0,
                "requires_manual_review": True
            }
    
    async def _load_and_preprocess_image(self, image_path: str) -> Dict[str, Any]:
        """Load and preprocess image for OCR"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return {"success": False, "error": "Could not load image"}
            
            original_image = image.copy()
            
            # Check image quality
            height, width = image.shape[:2]
            if height < self.quality_thresholds["min_resolution"][0] or width < self.quality_thresholds["min_resolution"][1]:
                return {
                    "success": False,
                    "error": "Image resolution too low",
                    "resolution": (width, height)
                }
            
            # Preprocess for better OCR
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Deskew if needed (simple rotation correction)
            processed_image = self._deskew_image(thresh)
            
            return {
                "success": True,
                "original_image": original_image,
                "processed_image": processed_image,
                "resolution": (width, height)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Image preprocessing failed: {str(e)}"}
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Simple deskewing to correct document rotation"""
        try:
            # Find contours
            contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Get the largest contour (likely the document)
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Get minimum area rectangle
                rect = cv2.minAreaRect(largest_contour)
                angle = rect[2]
                
                # Correct angle
                if angle < -45:
                    angle = 90 + angle
                
                # Rotate image if angle is significant
                if abs(angle) > 1:
                    (h, w) = image.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                    return rotated
            
            return image
            
        except Exception:
            return image  # Return original if deskewing fails
    
    async def _extract_text_ocr(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract text from image using OCR"""
        try:
            # Configure Tesseract for Vietnamese
            config = '--oem 3 --psm 6 -l vie+eng'
            
            # Extract text with confidence scores
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            
            # Filter out low-confidence text
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Extract text
            text = pytesseract.image_to_string(image, config=config)
            
            # Clean extracted text
            cleaned_text = self._clean_extracted_text(text)
            
            if len(cleaned_text) < self.quality_thresholds["min_extracted_text_length"]:
                return {
                    "success": False,
                    "error": "Insufficient text extracted",
                    "text_length": len(cleaned_text)
                }
            
            if avg_confidence < self.quality_thresholds["min_text_confidence"]:
                return {
                    "success": False,
                    "error": "Low OCR confidence",
                    "confidence": avg_confidence
                }
            
            return {
                "success": True,
                "text": cleaned_text,
                "confidence": avg_confidence,
                "word_count": len(cleaned_text.split())
            }
            
        except Exception as e:
            return {"success": False, "error": f"OCR extraction failed: {str(e)}"}
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might be OCR artifacts
        text = re.sub(r'[^\w\s\.\,\:\;\-\(\)\/]', '', text)
        
        # Normalize Vietnamese characters if needed
        # (This would require additional Vietnamese text processing libraries)
        
        return text.strip()
    
    def _analyze_extracted_text(self, text: str, document_type: str) -> Dict[str, Any]:
        """Analyze extracted text for medical document patterns"""
        analysis = {
            "found_patterns": [],
            "missing_patterns": [],
            "pattern_score": 0,
            "content_analysis": {}
        }
        
        text_lower = text.lower()
        
        # Check for required patterns based on document type
        required_patterns = self._get_required_patterns(document_type)
        
        for pattern_type, patterns in required_patterns.items():
            found = False
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    analysis["found_patterns"].append({
                        "type": pattern_type,
                        "pattern": pattern,
                        "matches": matches
                    })
                    analysis["pattern_score"] += 10
                    found = True
                    break
            
            if not found:
                analysis["missing_patterns"].append(pattern_type)
        
        # Check for legitimate hospital names
        hospital_found = False
        for hospital in self.legitimate_hospitals:
            if hospital in text_lower:
                analysis["found_patterns"].append({
                    "type": "legitimate_hospital",
                    "hospital": hospital
                })
                analysis["pattern_score"] += 20
                hospital_found = True
                break
        
        if not hospital_found:
            analysis["missing_patterns"].append("legitimate_hospital")
        
        # Analyze content quality
        analysis["content_analysis"] = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "has_dates": bool(re.search(r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}', text)),
            "has_medical_terms": self._count_medical_terms(text_lower),
            "language_consistency": self._check_language_consistency(text)
        }
        
        return analysis
    
    def _verify_authenticity(self, text: str, image: np.ndarray) -> Dict[str, Any]:
        """Verify document authenticity using various checks"""
        authenticity = {
            "authenticity_score": 0,
            "checks_performed": [],
            "suspicious_indicators": []
        }
        
        # Check for digital manipulation signs
        # (This would require more sophisticated image analysis)
        
        # Check text consistency
        if self._check_text_consistency(text):
            authenticity["authenticity_score"] += 20
            authenticity["checks_performed"].append("text_consistency")
        else:
            authenticity["suspicious_indicators"].append("inconsistent_text")
        
        # Check for proper formatting
        if self._check_document_formatting(text):
            authenticity["authenticity_score"] += 15
            authenticity["checks_performed"].append("document_formatting")
        else:
            authenticity["suspicious_indicators"].append("poor_formatting")
        
        # Check for required elements
        required_elements = ["hospital", "doctor", "date"]
        found_elements = 0
        
        for element in required_elements:
            if self._has_required_element(text, element):
                found_elements += 1
        
        authenticity["authenticity_score"] += (found_elements / len(required_elements)) * 30
        authenticity["checks_performed"].append(f"required_elements_{found_elements}/{len(required_elements)}")
        
        return authenticity
    
    def _calculate_verification_score(
        self,
        text_analysis: Dict[str, Any],
        authenticity_check: Dict[str, Any],
        ocr_result: Dict[str, Any]
    ) -> int:
        """Calculate overall verification score"""
        score = 0
        
        # Pattern matching score (40% weight)
        pattern_score = min(text_analysis["pattern_score"], 40)
        score += pattern_score
        
        # Authenticity score (35% weight)
        auth_score = min(authenticity_check["authenticity_score"], 35)
        score += auth_score
        
        # OCR quality score (25% weight)
        ocr_score = min(ocr_result["confidence"] / 4, 25)  # Scale 0-100 to 0-25
        score += ocr_score
        
        return min(int(score), 100)
    
    def _get_confidence_level(self, score: int) -> str:
        """Get confidence level based on verification score"""
        if score >= 90:
            return "very_high"
        elif score >= 80:
            return "high"
        elif score >= 70:
            return "medium"
        elif score >= 50:
            return "low"
        else:
            return "very_low"
    
    def _get_required_patterns(self, document_type: str) -> Dict[str, List[str]]:
        """Get required patterns for document type"""
        base_patterns = {
            "hospital_names": self.document_patterns["hospital_names"],
            "dates": self.document_patterns["dates"]
        }
        
        if document_type == "medical_certificate":
            base_patterns.update({
                "doctor_signatures": self.document_patterns["doctor_signatures"],
                "medical_license": self.document_patterns["medical_license"]
            })
        elif document_type == "hospital_record":
            base_patterns.update({
                "diagnosis_codes": self.document_patterns["diagnosis_codes"]
            })
        
        return base_patterns
    
    def _count_medical_terms(self, text: str) -> int:
        """Count medical terms in text"""
        medical_terms = [
            "bệnh", "điều trị", "thuốc", "khám", "chẩn đoán", "phẫu thuật",
            "xét nghiệm", "siêu âm", "x-quang", "mri", "ct scan"
        ]
        
        count = 0
        for term in medical_terms:
            count += text.count(term)
        
        return count
    
    def _check_language_consistency(self, text: str) -> bool:
        """Check if language usage is consistent"""
        # Simple check for mixed languages inappropriately
        vietnamese_chars = sum(1 for c in text if ord(c) > 127)
        total_chars = len(text)
        
        if total_chars == 0:
            return False
        
        vietnamese_ratio = vietnamese_chars / total_chars
        return 0.1 <= vietnamese_ratio <= 0.8  # Reasonable mix for Vietnamese medical documents
    
    def _check_text_consistency(self, text: str) -> bool:
        """Check text consistency and formatting"""
        # Check for reasonable sentence structure
        sentences = text.split('.')
        if len(sentences) < 2:
            return False
        
        # Check for reasonable word distribution
        words = text.split()
        if len(words) < 10:
            return False
        
        return True
    
    def _check_document_formatting(self, text: str) -> bool:
        """Check if document has proper formatting"""
        # Check for proper capitalization
        lines = text.split('\n')
        properly_formatted_lines = 0
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isupper() or line.startswith(('Bệnh viện', 'Phòng khám'))):
                properly_formatted_lines += 1
        
        return properly_formatted_lines >= len(lines) * 0.3
    
    def _has_required_element(self, text: str, element: str) -> bool:
        """Check if text has required element"""
        text_lower = text.lower()
        
        if element == "hospital":
            return any(hospital in text_lower for hospital in ["bệnh viện", "phòng khám", "hospital"])
        elif element == "doctor":
            return any(title in text_lower for title in ["bác sĩ", "bs", "dr", "doctor"])
        elif element == "date":
            return bool(re.search(r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}', text))
        
        return False
    
    async def _save_verification_result(
        self,
        user_id: int,
        document_path: str,
        result: Dict[str, Any]
    ) -> bool:
        """Save verification result to database"""
        try:
            verification_data = {
                "user_id": user_id,
                "document_path": document_path,
                "verification_score": result["verification_score"],
                "confidence_level": result["confidence_level"],
                "extracted_text": result["extracted_text"],
                "text_analysis": result["text_analysis"],
                "authenticity_check": result["authenticity_check"],
                "requires_manual_review": result["requires_manual_review"],
                "verification_timestamp": result["verification_timestamp"]
            }
            
            db_result = self.supabase.table("document_verifications").insert(verification_data).execute()
            return bool(db_result.data)
            
        except Exception as e:
            logger.error(f"Failed to save verification result: {str(e)}")
            return False


# Global document verifier instance
document_verifier = DocumentVerifier()
