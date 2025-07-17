"""
Donation Advisory System for Ytili AI Agent
Provides intelligent donation recommendations and campaign matching
"""
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import structlog

from ..models.ai_agent import AIRecommendation, RecommendationType
from ..core.supabase import get_supabase_service

logger = structlog.get_logger()


class DonationAdvisor:
    """
    Intelligent donation recommendation system
    """
    
    def __init__(self):
        self.supabase = get_supabase_service()
        
        # Donation amount suggestions based on budget ranges (VND)
        self.budget_suggestions = {
            "low": {"min": 50000, "max": 500000, "recommended": [100000, 200000, 300000]},
            "medium": {"min": 500000, "max": 2000000, "recommended": [750000, 1000000, 1500000]},
            "high": {"min": 2000000, "max": 10000000, "recommended": [3000000, 5000000, 7000000]},
            "premium": {"min": 10000000, "max": 100000000, "recommended": [15000000, 25000000, 50000000]}
        }
        
        # Medical specialties and common needs
        self.medical_specialties = {
            "cardiology": ["tim mạch", "cardiac", "heart", "tim"],
            "oncology": ["ung thư", "cancer", "oncology", "khối u"],
            "pediatrics": ["nhi", "pediatric", "trẻ em", "children"],
            "neurology": ["thần kinh", "neurology", "brain", "não"],
            "orthopedics": ["xương khớp", "orthopedic", "bone", "gãy xương"],
            "emergency": ["cấp cứu", "emergency", "khẩn cấp", "urgent"],
            "surgery": ["phẫu thuật", "surgery", "operation", "mổ"],
            "dialysis": ["thận", "kidney", "lọc máu", "dialysis"]
        }
    
    async def generate_recommendations(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate donation recommendations based on conversation context
        
        Args:
            session_id: Conversation session ID
            user_message: User's message
            ai_response: AI's response
            user_id: User ID (optional)
            
        Returns:
            List of donation recommendations
        """
        try:
            recommendations = []
            
            # Extract budget information from conversation
            budget_info = self._extract_budget_info(user_message)
            
            # Extract medical interests/conditions
            medical_interests = self._extract_medical_interests(user_message + " " + ai_response)
            
            # Get user context if available
            user_context = await self._get_user_context(session_id) if not user_id else await self._get_user_context_by_id(user_id)
            
            # Generate campaign recommendations
            campaign_recs = await self._recommend_campaigns(
                budget_info, medical_interests, user_context
            )
            recommendations.extend(campaign_recs)
            
            # Generate donation amount recommendations
            amount_recs = self._recommend_donation_amounts(budget_info, user_context)
            recommendations.extend(amount_recs)
            
            # Generate emergency recommendations if urgent keywords detected
            if self._detect_urgency(user_message):
                emergency_recs = await self._recommend_emergency_cases()
                recommendations.extend(emergency_recs)
            
            # Save recommendations to database
            for rec in recommendations:
                await self._save_recommendation(session_id, rec, user_context.get("user_id"))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            return []
    
    def _extract_budget_info(self, text: str) -> Dict[str, Any]:
        """Extract budget information from text"""
        budget_info = {"amount": None, "range": None, "currency": "VND"}
        
        # Look for specific amounts
        amount_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:triệu|million)',  # X triệu
            r'(\d+(?:\.\d+)?)\s*(?:nghìn|thousand)',  # X nghìn  
            r'(\d+(?:,\d{3})*)\s*(?:đồng|vnd)',  # X đồng
            r'(\d+(?:,\d{3})*)\s*(?:k|K)',  # XK (thousands)
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                amount = float(amount_str)
                
                if 'triệu' in match.group(0) or 'million' in match.group(0):
                    amount *= 1000000
                elif 'nghìn' in match.group(0) or 'thousand' in match.group(0) or 'k' in match.group(0).lower():
                    amount *= 1000
                
                budget_info["amount"] = int(amount)
                break
        
        # Determine budget range
        if budget_info["amount"]:
            amount = budget_info["amount"]
            if amount < 500000:
                budget_info["range"] = "low"
            elif amount < 2000000:
                budget_info["range"] = "medium"
            elif amount < 10000000:
                budget_info["range"] = "high"
            else:
                budget_info["range"] = "premium"
        
        # Look for budget range keywords
        range_keywords = {
            "low": ["ít tiền", "nghèo", "khó khăn", "hạn chế", "budget thấp"],
            "medium": ["trung bình", "vừa phải", "moderate", "reasonable"],
            "high": ["nhiều tiền", "giàu", "cao", "substantial", "significant"],
            "premium": ["rất nhiều", "unlimited", "không giới hạn", "maximum"]
        }
        
        for range_name, keywords in range_keywords.items():
            if any(keyword in text.lower() for keyword in keywords):
                budget_info["range"] = range_name
                break
        
        return budget_info
    
    def _extract_medical_interests(self, text: str) -> List[str]:
        """Extract medical specialties/interests from text"""
        interests = []
        
        for specialty, keywords in self.medical_specialties.items():
            if any(keyword in text.lower() for keyword in keywords):
                interests.append(specialty)
        
        return interests
    
    def _detect_urgency(self, text: str) -> bool:
        """Detect if the message indicates urgency"""
        urgent_keywords = [
            "khẩn cấp", "gấp", "urgent", "emergency", "cần gấp",
            "nguy hiểm", "critical", "life threatening", "sắp chết",
            "cứu", "help", "save", "immediately", "ngay lập tức"
        ]
        
        return any(keyword in text.lower() for keyword in urgent_keywords)
    
    async def _recommend_campaigns(
        self,
        budget_info: Dict[str, Any],
        medical_interests: List[str],
        user_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Recommend relevant campaigns"""
        try:
            recommendations = []
            
            # Build query for campaigns
            query = self.supabase.table("campaigns").select("*")
            
            # Filter by medical specialty if interests detected
            if medical_interests:
                # This would need to be implemented based on campaign categorization
                pass
            
            # Filter by location if user has location preference
            if user_context.get("location", {}).get("province"):
                query = query.eq("province", user_context["location"]["province"])
            
            # Get active campaigns
            query = query.eq("status", "active").order("created_at", desc=True).limit(5)
            
            result = query.execute()
            
            if result.data:
                for campaign in result.data:
                    # Calculate donation suggestion based on budget
                    suggested_amount = self._calculate_suggested_donation(
                        campaign, budget_info
                    )
                    
                    recommendations.append({
                        "type": "campaign_match",
                        "title": f"Chiến dịch: {campaign['title']}",
                        "description": f"Gợi ý quyên góp {suggested_amount:,} VND cho chiến dịch này",
                        "data": {
                            "campaign_id": campaign["id"],
                            "campaign_title": campaign["title"],
                            "suggested_amount": suggested_amount,
                            "campaign_goal": campaign.get("goal_amount"),
                            "current_amount": campaign.get("current_amount", 0),
                            "urgency": campaign.get("urgency_level", "medium")
                        },
                        "confidence": 0.8
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to recommend campaigns: {str(e)}")
            return []
    
    def _recommend_donation_amounts(
        self,
        budget_info: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Recommend donation amounts based on budget"""
        recommendations = []
        
        if budget_info.get("range"):
            budget_range = self.budget_suggestions[budget_info["range"]]
            
            for amount in budget_range["recommended"]:
                recommendations.append({
                    "type": "donation_amount",
                    "title": f"Gợi ý quyên góp {amount:,} VND",
                    "description": f"Số tiền phù hợp với ngân sách {budget_info['range']} của bạn",
                    "data": {
                        "amount": amount,
                        "currency": "VND",
                        "budget_range": budget_info["range"],
                        "impact_description": self._get_impact_description(amount)
                    },
                    "confidence": 0.9
                })
        
        return recommendations
    
    async def _recommend_emergency_cases(self) -> List[Dict[str, Any]]:
        """Recommend urgent emergency cases"""
        try:
            # Get emergency requests that need immediate attention
            result = self.supabase.table("emergency_requests").select("*").eq("status", "pending").order("created_at", desc=True).limit(3).execute()
            
            recommendations = []
            
            if result.data:
                for emergency in result.data:
                    recommendations.append({
                        "type": "emergency_support",
                        "title": f"🚨 Hỗ trợ khẩn cấp: {emergency['medical_condition']}",
                        "description": f"Trường hợp cần hỗ trợ gấp - {emergency['description'][:100]}...",
                        "data": {
                            "emergency_id": emergency["id"],
                            "condition": emergency["medical_condition"],
                            "priority": emergency["priority"],
                            "location": emergency.get("location"),
                            "estimated_cost": emergency.get("estimated_cost")
                        },
                        "confidence": 1.0
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to recommend emergency cases: {str(e)}")
            return []
    
    def _calculate_suggested_donation(
        self,
        campaign: Dict[str, Any],
        budget_info: Dict[str, Any]
    ) -> int:
        """Calculate suggested donation amount for a campaign"""
        # Default suggestion based on budget range
        if budget_info.get("amount"):
            # Suggest 10-30% of stated budget
            return min(int(budget_info["amount"] * 0.2), campaign.get("goal_amount", 1000000))
        
        if budget_info.get("range"):
            budget_range = self.budget_suggestions[budget_info["range"]]
            return budget_range["recommended"][1]  # Middle recommendation
        
        # Default suggestion
        return 500000
    
    def _get_impact_description(self, amount: int) -> str:
        """Get impact description for donation amount"""
        if amount >= 10000000:
            return "Có thể hỗ trợ một ca phẫu thuật lớn hoặc điều trị dài hạn"
        elif amount >= 5000000:
            return "Có thể hỗ trợ điều trị cho một bệnh nhân trong vài tháng"
        elif amount >= 1000000:
            return "Có thể mua thuốc thiết yếu cho nhiều bệnh nhân"
        elif amount >= 500000:
            return "Có thể hỗ trợ khám bệnh và thuốc cơ bản"
        else:
            return "Có thể hỗ trợ vật tư y tế cơ bản"
    
    async def _get_user_context(self, session_id: str) -> Dict[str, Any]:
        """Get user context from conversation session"""
        try:
            result = self.supabase.table("ai_conversations").select("user_id, context_data").eq("session_id", session_id).execute()
            
            if result.data:
                conversation = result.data[0]
                context = conversation.get("context_data", {})
                context["user_id"] = conversation["user_id"]
                return context
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get user context: {str(e)}")
            return {}
    
    async def _get_user_context_by_id(self, user_id: int) -> Dict[str, Any]:
        """Get user context by user ID"""
        try:
            user_result = self.supabase.table("users").select("*").eq("id", user_id).execute()
            
            if user_result.data:
                user = user_result.data[0]
                return {
                    "user_id": user_id,
                    "user_type": user.get("user_type"),
                    "location": {
                        "city": user.get("city"),
                        "province": user.get("province")
                    }
                }
            
            return {"user_id": user_id}
            
        except Exception as e:
            logger.error(f"Failed to get user context by ID: {str(e)}")
            return {"user_id": user_id}
    
    async def _save_recommendation(
        self,
        session_id: str,
        recommendation: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> bool:
        """Save recommendation to database"""
        try:
            # Get conversation ID
            conv_result = self.supabase.table("ai_conversations").select("id, user_id").eq("session_id", session_id).execute()
            
            if not conv_result.data:
                return False
            
            conversation = conv_result.data[0]
            conversation_id = conversation["id"]
            user_id = user_id or conversation["user_id"]
            
            # Save recommendation
            rec_data = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "recommendation_type": recommendation["type"],
                "title": recommendation["title"],
                "description": recommendation["description"],
                "recommendation_data": recommendation["data"],
                "confidence_score": recommendation["confidence"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table("ai_recommendations").insert(rec_data).execute()
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Failed to save recommendation: {str(e)}")
            return False


# Global donation advisor instance
donation_advisor = DonationAdvisor()
