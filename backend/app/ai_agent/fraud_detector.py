"""
AI-Powered Fraud Detection for Ytili Platform
Analyzes campaigns, donations, and user behavior for suspicious patterns
"""
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
import structlog

from ..core.supabase import get_supabase_service

logger = structlog.get_logger()


class FraudDetector:
    """
    AI-powered fraud detection system for campaigns and donations
    """
    
    def __init__(self):
        self.supabase = get_supabase_service()
        
        # Suspicious patterns in campaign descriptions
        self.suspicious_patterns = {
            "urgency_manipulation": [
                r"chỉ còn \d+ (giờ|ngày)",  # "only X hours/days left"
                r"sắp chết",  # "about to die"
                r"không còn thời gian",  # "no time left"
                r"cần gấp trong \d+ (giờ|ngày)",  # "need urgently in X hours/days"
            ],
            "emotional_manipulation": [
                r"con tôi sắp chết",  # "my child is dying"
                r"không có tiền",  # "no money"
                r"gia đình nghèo",  # "poor family"
                r"cầu xin",  # "begging"
                r"tuyệt vọng",  # "desperate"
            ],
            "fake_medical_terms": [
                r"bệnh hiếm gặp",  # "rare disease"
                r"ca bệnh đặc biệt",  # "special case"
                r"bác sĩ nói",  # "doctor said" (without specifics)
                r"cần phẫu thuật gấp",  # "need urgent surgery"
            ],
            "financial_inconsistencies": [
                r"\d+\s*tỷ",  # billions (unrealistic amounts)
                r"chi phí cao",  # "high cost" (vague)
                r"tiền viện phí",  # "hospital fees" (vague)
            ]
        }
        
        # Red flags for user behavior
        self.behavioral_red_flags = {
            "account_age": 7,  # Account created less than 7 days ago
            "multiple_campaigns": 3,  # More than 3 campaigns in short time
            "rapid_succession": 24,  # Multiple campaigns within 24 hours
            "no_verification": True,  # No KYC verification
            "suspicious_location": ["unknown", "fake", "test"]
        }
        
        # Medical document verification patterns
        self.document_patterns = {
            "valid_hospital_names": [
                "bệnh viện", "phòng khám", "trung tâm y tế", "hospital", "clinic"
            ],
            "valid_doctor_titles": [
                "bác sĩ", "bs", "dr", "doctor", "thầy thuốc"
            ],
            "medical_license_format": r"[A-Z]{2,3}\d{4,6}",  # Medical license format
            "hospital_code_format": r"\d{5,6}"  # Hospital code format
        }
    
    async def analyze_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a campaign for fraud indicators
        
        Args:
            campaign_data: Campaign information to analyze
            
        Returns:
            Fraud analysis result
        """
        try:
            fraud_score = 0
            fraud_indicators = []
            
            # Analyze campaign description
            description_analysis = self._analyze_description(
                campaign_data.get("description", "")
            )
            fraud_score += description_analysis["score"]
            fraud_indicators.extend(description_analysis["indicators"])
            
            # Analyze user behavior
            user_analysis = await self._analyze_user_behavior(
                campaign_data.get("user_id")
            )
            fraud_score += user_analysis["score"]
            fraud_indicators.extend(user_analysis["indicators"])
            
            # Analyze financial aspects
            financial_analysis = self._analyze_financial_data(campaign_data)
            fraud_score += financial_analysis["score"]
            fraud_indicators.extend(financial_analysis["indicators"])
            
            # Analyze medical claims
            medical_analysis = await self._analyze_medical_claims(campaign_data)
            fraud_score += medical_analysis["score"]
            fraud_indicators.extend(medical_analysis["indicators"])
            
            # Determine risk level
            risk_level = self._calculate_risk_level(fraud_score)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(risk_level, fraud_indicators)
            
            result = {
                "fraud_score": fraud_score,
                "risk_level": risk_level,
                "fraud_indicators": fraud_indicators,
                "recommendations": recommendations,
                "requires_manual_review": risk_level in ["high", "critical"],
                "auto_approve": risk_level == "low" and fraud_score < 20,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Save analysis result
            await self._save_fraud_analysis(campaign_data.get("id"), result)
            
            logger.info(
                "Campaign fraud analysis completed",
                campaign_id=campaign_data.get("id"),
                fraud_score=fraud_score,
                risk_level=risk_level
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze campaign for fraud: {str(e)}")
            return {
                "fraud_score": 100,  # High score for safety
                "risk_level": "critical",
                "error": str(e),
                "requires_manual_review": True
            }
    
    def _analyze_description(self, description: str) -> Dict[str, Any]:
        """Analyze campaign description for suspicious patterns"""
        score = 0
        indicators = []
        
        description_lower = description.lower()
        
        # Check for suspicious patterns
        for pattern_type, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, description_lower)
                if matches:
                    score += 15
                    indicators.append({
                        "type": "suspicious_pattern",
                        "category": pattern_type,
                        "pattern": pattern,
                        "matches": matches
                    })
        
        # Check description length and quality
        if len(description) < 50:
            score += 20
            indicators.append({
                "type": "description_quality",
                "issue": "too_short",
                "length": len(description)
            })
        
        # Check for excessive capitalization
        caps_ratio = sum(1 for c in description if c.isupper()) / len(description) if description else 0
        if caps_ratio > 0.3:
            score += 10
            indicators.append({
                "type": "description_quality",
                "issue": "excessive_caps",
                "ratio": caps_ratio
            })
        
        # Check for repeated phrases
        words = description_lower.split()
        word_freq = {}
        for word in words:
            if len(word) > 3:  # Only check meaningful words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        repeated_words = [word for word, freq in word_freq.items() if freq > 3]
        if repeated_words:
            score += 5
            indicators.append({
                "type": "description_quality",
                "issue": "repeated_words",
                "words": repeated_words
            })
        
        return {
            "score": score,
            "indicators": indicators
        }
    
    async def _analyze_user_behavior(self, user_id: Optional[int]) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        score = 0
        indicators = []
        
        if not user_id:
            return {"score": 50, "indicators": [{"type": "user", "issue": "no_user_id"}]}
        
        try:
            # Get user information
            user_result = self.supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not user_result.data:
                return {"score": 50, "indicators": [{"type": "user", "issue": "user_not_found"}]}
            
            user = user_result.data[0]
            
            # Check account age
            created_at = datetime.fromisoformat(user["created_at"].replace('Z', '+00:00'))
            account_age_days = (datetime.now(timezone.utc) - created_at).days
            
            if account_age_days < self.behavioral_red_flags["account_age"]:
                score += 25
                indicators.append({
                    "type": "user_behavior",
                    "issue": "new_account",
                    "account_age_days": account_age_days
                })
            
            # Check KYC verification
            if not user.get("is_kyc_verified", False):
                score += 15
                indicators.append({
                    "type": "user_behavior",
                    "issue": "no_kyc_verification"
                })
            
            # Check for multiple campaigns
            campaigns_result = self.supabase.table("campaigns").select("*").eq("user_id", user_id).execute()
            
            if campaigns_result.data:
                campaign_count = len(campaigns_result.data)
                
                if campaign_count > self.behavioral_red_flags["multiple_campaigns"]:
                    score += 20
                    indicators.append({
                        "type": "user_behavior",
                        "issue": "multiple_campaigns",
                        "campaign_count": campaign_count
                    })
                
                # Check for rapid succession campaigns
                recent_campaigns = [
                    c for c in campaigns_result.data
                    if datetime.fromisoformat(c["created_at"].replace('Z', '+00:00')) > 
                    datetime.now(timezone.utc) - timedelta(hours=self.behavioral_red_flags["rapid_succession"])
                ]
                
                if len(recent_campaigns) > 1:
                    score += 30
                    indicators.append({
                        "type": "user_behavior",
                        "issue": "rapid_succession_campaigns",
                        "recent_count": len(recent_campaigns)
                    })
            
            # Check location information
            if not user.get("city") or user.get("city", "").lower() in self.behavioral_red_flags["suspicious_location"]:
                score += 10
                indicators.append({
                    "type": "user_behavior",
                    "issue": "suspicious_location",
                    "location": user.get("city", "unknown")
                })
            
            return {
                "score": score,
                "indicators": indicators
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze user behavior: {str(e)}")
            return {
                "score": 30,
                "indicators": [{"type": "user_behavior", "issue": "analysis_error", "error": str(e)}]
            }
    
    def _analyze_financial_data(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze financial aspects of the campaign"""
        score = 0
        indicators = []
        
        goal_amount = campaign_data.get("goal_amount", 0)
        
        # Check for unrealistic amounts
        if goal_amount > 1000000000:  # > 1 billion VND
            score += 40
            indicators.append({
                "type": "financial",
                "issue": "unrealistic_amount",
                "amount": goal_amount
            })
        elif goal_amount > 100000000:  # > 100 million VND
            score += 20
            indicators.append({
                "type": "financial",
                "issue": "very_high_amount",
                "amount": goal_amount
            })
        
        # Check for round numbers (often fake)
        if goal_amount > 0 and goal_amount % 1000000 == 0:  # Exact millions
            score += 5
            indicators.append({
                "type": "financial",
                "issue": "round_number",
                "amount": goal_amount
            })
        
        # Check for missing financial breakdown
        description = campaign_data.get("description", "")
        if goal_amount > 10000000 and "chi phí" not in description.lower():  # No cost breakdown
            score += 15
            indicators.append({
                "type": "financial",
                "issue": "no_cost_breakdown"
            })
        
        return {
            "score": score,
            "indicators": indicators
        }
    
    async def _analyze_medical_claims(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze medical claims and documentation"""
        score = 0
        indicators = []
        
        description = campaign_data.get("description", "")
        
        # Check for vague medical terms
        vague_terms = ["bệnh hiếm", "bệnh lạ", "ca đặc biệt", "bác sĩ nói"]
        for term in vague_terms:
            if term in description.lower():
                score += 10
                indicators.append({
                    "type": "medical_claims",
                    "issue": "vague_medical_term",
                    "term": term
                })
        
        # Check for specific hospital/doctor mentions
        has_hospital = any(hospital in description.lower() for hospital in self.document_patterns["valid_hospital_names"])
        has_doctor = any(title in description.lower() for title in self.document_patterns["valid_doctor_titles"])
        
        if not has_hospital and campaign_data.get("goal_amount", 0) > 5000000:
            score += 15
            indicators.append({
                "type": "medical_claims",
                "issue": "no_hospital_mentioned"
            })
        
        if not has_doctor and campaign_data.get("goal_amount", 0) > 10000000:
            score += 10
            indicators.append({
                "type": "medical_claims",
                "issue": "no_doctor_mentioned"
            })
        
        # Check for medical documents
        documents = campaign_data.get("documents", [])
        if not documents and campaign_data.get("goal_amount", 0) > 5000000:
            score += 25
            indicators.append({
                "type": "medical_claims",
                "issue": "no_medical_documents"
            })
        
        return {
            "score": score,
            "indicators": indicators
        }
    
    def _calculate_risk_level(self, fraud_score: int) -> str:
        """Calculate risk level based on fraud score"""
        if fraud_score >= 80:
            return "critical"
        elif fraud_score >= 60:
            return "high"
        elif fraud_score >= 40:
            return "medium"
        elif fraud_score >= 20:
            return "low"
        else:
            return "minimal"
    
    def _generate_recommendations(self, risk_level: str, indicators: List[Dict]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if risk_level in ["critical", "high"]:
            recommendations.extend([
                "Yêu cầu xác minh danh tính bổ sung",
                "Kiểm tra tài liệu y tế với bệnh viện",
                "Tạm dừng chiến dịch cho đến khi xác minh",
                "Liên hệ trực tiếp với người tạo chiến dịch"
            ])
        
        if risk_level == "medium":
            recommendations.extend([
                "Yêu cầu bổ sung tài liệu y tế",
                "Xác minh thông tin bệnh viện/bác sĩ",
                "Theo dõi chiến dịch chặt chẽ"
            ])
        
        # Specific recommendations based on indicators
        indicator_types = [ind.get("type") for ind in indicators]
        
        if "user_behavior" in indicator_types:
            recommendations.append("Xác minh thông tin người dùng")
        
        if "medical_claims" in indicator_types:
            recommendations.append("Yêu cầu giấy tờ y tế chi tiết")
        
        if "financial" in indicator_types:
            recommendations.append("Xem xét lại mục tiêu tài chính")
        
        return list(set(recommendations))  # Remove duplicates
    
    async def _save_fraud_analysis(self, campaign_id: Optional[int], analysis: Dict[str, Any]) -> bool:
        """Save fraud analysis result to database"""
        try:
            if not campaign_id:
                return False
            
            analysis_data = {
                "campaign_id": campaign_id,
                "fraud_score": analysis["fraud_score"],
                "risk_level": analysis["risk_level"],
                "fraud_indicators": analysis["fraud_indicators"],
                "recommendations": analysis["recommendations"],
                "requires_manual_review": analysis["requires_manual_review"],
                "analysis_timestamp": analysis["analysis_timestamp"]
            }
            
            result = self.supabase.table("fraud_analysis").insert(analysis_data).execute()
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Failed to save fraud analysis: {str(e)}")
            return False
    
    async def get_user_fraud_history(self, user_id: int) -> Dict[str, Any]:
        """Get fraud analysis history for a user"""
        try:
            # Get user's campaigns and their fraud analysis
            campaigns_result = self.supabase.table("campaigns").select("id, title, created_at").eq("user_id", user_id).execute()
            
            if not campaigns_result.data:
                return {"total_campaigns": 0, "fraud_analyses": []}
            
            campaign_ids = [c["id"] for c in campaigns_result.data]
            
            # Get fraud analyses for these campaigns
            analyses_result = self.supabase.table("fraud_analysis").select("*").in_("campaign_id", campaign_ids).execute()
            
            return {
                "total_campaigns": len(campaigns_result.data),
                "fraud_analyses": analyses_result.data or [],
                "average_fraud_score": sum(a["fraud_score"] for a in analyses_result.data) / len(analyses_result.data) if analyses_result.data else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get user fraud history: {str(e)}")
            return {"error": str(e)}


# Global fraud detector instance
fraud_detector = FraudDetector()
