"""
Medical Knowledge Base for Ytili AI Agent
Provides medical information, drug interactions, and hospital specializations
"""
import json
from typing import Dict, List, Optional, Any
import structlog

from ..core.supabase import get_supabase_service

logger = structlog.get_logger()


class MedicalKnowledgeBase:
    """
    Medical knowledge base for AI Agent with Vietnamese medical context
    """
    
    def __init__(self):
        self.supabase = get_supabase_service()
        
        # Common medical conditions in Vietnamese context
        self.common_conditions = {
            "tim_mach": {
                "vietnamese_names": ["bệnh tim", "tim mạch", "đau tim", "nhồi máu cơ tim"],
                "english_names": ["heart disease", "cardiac", "myocardial infarction"],
                "symptoms": ["đau ngực", "khó thở", "mệt mỏi", "đánh trống ngực"],
                "emergency_signs": ["đau ngực dữ dội", "khó thở nặng", "bất tỉnh"],
                "specialties": ["tim mạch", "cấp cứu"],
                "common_medications": ["aspirin", "nitroglycerin", "beta-blocker"],
                "is_emergency": True
            },
            "ung_thu": {
                "vietnamese_names": ["ung thư", "cancer", "khối u", "u ác tính"],
                "english_names": ["cancer", "tumor", "malignancy", "oncology"],
                "symptoms": ["sụt cân", "mệt mỏi", "đau không rõ nguyên nhân"],
                "emergency_signs": ["chảy máu nhiều", "khó thở nặng", "đau dữ dội"],
                "specialties": ["ung bướu", "hóa trị", "xạ trị"],
                "common_medications": ["hóa trị", "giảm đau", "kháng sinh"],
                "is_emergency": False
            },
            "tieu_duong": {
                "vietnamese_names": ["tiểu đường", "đái tháo đường", "diabetes"],
                "english_names": ["diabetes", "diabetes mellitus", "blood sugar"],
                "symptoms": ["khát nước nhiều", "tiểu nhiều", "mệt mỏi", "sụt cân"],
                "emergency_signs": ["hôn mê", "thở nhanh", "mất nước nặng"],
                "specialties": ["nội tiết", "nội khoa"],
                "common_medications": ["insulin", "metformin", "thuốc hạ đường huyết"],
                "is_emergency": False
            },
            "cao_huyet_ap": {
                "vietnamese_names": ["cao huyết áp", "tăng huyết áp", "hypertension"],
                "english_names": ["hypertension", "high blood pressure"],
                "symptoms": ["đau đầu", "chóng mặt", "mệt mỏi"],
                "emergency_signs": ["đau đầu dữ dội", "buồn nôn", "nhìn mờ"],
                "specialties": ["tim mạch", "nội khoa"],
                "common_medications": ["ACE inhibitor", "thuốc lợi tiểu", "calcium blocker"],
                "is_emergency": False
            },
            "sot_xuat_huyet": {
                "vietnamese_names": ["sốt xuất huyết", "dengue", "sốt dengue"],
                "english_names": ["dengue fever", "hemorrhagic fever"],
                "symptoms": ["sốt cao", "đau đầu", "đau cơ", "nôn mửa"],
                "emergency_signs": ["chảy máu", "hạ huyết áp", "khó thở"],
                "specialties": ["nhiễm khuẩn", "cấp cứu"],
                "common_medications": ["paracetamol", "dịch truyền", "theo dõi"],
                "is_emergency": True
            }
        }
        
        # Hospital specializations in Vietnam
        self.hospital_specialties = {
            "benh_vien_bach_mai": {
                "name": "Bệnh viện Bạch Mai",
                "specialties": ["tim mạch", "ung bướu", "thần kinh", "cấp cứu"],
                "location": "Hà Nội",
                "type": "central"
            },
            "benh_vien_cho_ray": {
                "name": "Bệnh viện Chợ Rẫy", 
                "specialties": ["cấp cứu", "phẫu thuật", "tim mạch", "thần kinh"],
                "location": "TP.HCM",
                "type": "central"
            },
            "benh_vien_k": {
                "name": "Bệnh viện K",
                "specialties": ["ung bướu", "hóa trị", "xạ trị"],
                "location": "Hà Nội",
                "type": "specialized"
            }
        }
        
        # Drug interactions and contraindications
        self.drug_interactions = {
            "aspirin": {
                "contraindications": ["dị ứng aspirin", "loét dạ dày", "rối loạn đông máu"],
                "interactions": ["warfarin", "thuốc chống đông"],
                "side_effects": ["đau dạ dày", "chảy máu", "ù tai"]
            },
            "paracetamol": {
                "contraindications": ["suy gan", "dị ứng paracetamol"],
                "interactions": ["rượu", "thuốc gan"],
                "side_effects": ["độc gan nếu quá liều"]
            },
            "insulin": {
                "contraindications": ["hạ đường huyết"],
                "interactions": ["thuốc hạ đường huyết khác"],
                "side_effects": ["hạ đường huyết", "tăng cân"]
            }
        }
    
    async def search_medical_condition(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for medical conditions based on query
        
        Args:
            query: Search query (symptoms, condition name, etc.)
            
        Returns:
            List of matching medical conditions
        """
        try:
            query_lower = query.lower()
            matches = []
            
            # Search in predefined conditions
            for condition_id, condition_data in self.common_conditions.items():
                score = 0
                matched_terms = []
                
                # Check Vietnamese names
                for name in condition_data["vietnamese_names"]:
                    if name.lower() in query_lower:
                        score += 10
                        matched_terms.append(name)
                
                # Check English names
                for name in condition_data["english_names"]:
                    if name.lower() in query_lower:
                        score += 8
                        matched_terms.append(name)
                
                # Check symptoms
                for symptom in condition_data["symptoms"]:
                    if symptom.lower() in query_lower:
                        score += 5
                        matched_terms.append(symptom)
                
                if score > 0:
                    matches.append({
                        "condition_id": condition_id,
                        "condition_data": condition_data,
                        "relevance_score": score,
                        "matched_terms": matched_terms
                    })
            
            # Search in database knowledge base
            db_results = await self._search_database_knowledge(query)
            matches.extend(db_results)
            
            # Sort by relevance score
            matches.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return matches[:10]  # Return top 10 matches
            
        except Exception as e:
            logger.error(f"Failed to search medical conditions: {str(e)}")
            return []
    
    async def get_drug_information(self, drug_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific drug
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            Drug information or None if not found
        """
        try:
            drug_lower = drug_name.lower()
            
            # Check predefined drug interactions
            if drug_lower in self.drug_interactions:
                return {
                    "drug_name": drug_name,
                    "information": self.drug_interactions[drug_lower],
                    "source": "knowledge_base"
                }
            
            # Search in medication catalog
            result = self.supabase.table("medication_catalog").select("*").ilike("name", f"%{drug_name}%").execute()
            
            if result.data:
                medication = result.data[0]
                return {
                    "drug_name": medication["name"],
                    "information": {
                        "generic_name": medication.get("generic_name"),
                        "category": medication.get("category"),
                        "indications": medication.get("indications"),
                        "contraindications": medication.get("contraindications"),
                        "side_effects": medication.get("side_effects"),
                        "dosage_form": medication.get("dosage_form"),
                        "strength": medication.get("strength")
                    },
                    "source": "medication_catalog"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get drug information: {str(e)}")
            return None
    
    async def find_appropriate_hospitals(
        self,
        condition: str,
        location: Optional[str] = None,
        specialty: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find hospitals appropriate for a medical condition
        
        Args:
            condition: Medical condition
            location: Preferred location
            specialty: Required medical specialty
            
        Returns:
            List of appropriate hospitals
        """
        try:
            hospitals = []
            
            # Search predefined hospitals
            for hospital_id, hospital_data in self.hospital_specialties.items():
                score = 0
                
                # Location match
                if location and hospital_data["location"].lower() in location.lower():
                    score += 10
                
                # Specialty match
                if specialty:
                    for hosp_specialty in hospital_data["specialties"]:
                        if specialty.lower() in hosp_specialty.lower():
                            score += 15
                
                # Condition-based specialty matching
                condition_info = await self._get_condition_specialties(condition)
                for required_specialty in condition_info:
                    for hosp_specialty in hospital_data["specialties"]:
                        if required_specialty.lower() in hosp_specialty.lower():
                            score += 8
                
                if score > 0:
                    hospitals.append({
                        "hospital_id": hospital_id,
                        "hospital_data": hospital_data,
                        "relevance_score": score
                    })
            
            # Search database hospitals
            db_hospitals = await self._search_database_hospitals(condition, location, specialty)
            hospitals.extend(db_hospitals)
            
            # Sort by relevance
            hospitals.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return hospitals[:5]  # Return top 5 matches
            
        except Exception as e:
            logger.error(f"Failed to find appropriate hospitals: {str(e)}")
            return []
    
    async def check_emergency_condition(self, symptoms: str) -> Dict[str, Any]:
        """
        Check if symptoms indicate an emergency condition
        
        Args:
            symptoms: Description of symptoms
            
        Returns:
            Emergency assessment
        """
        try:
            symptoms_lower = symptoms.lower()
            emergency_indicators = []
            emergency_level = "low"
            
            # Check for critical emergency signs
            critical_signs = [
                "không thở", "ngừng tim", "bất tỉnh", "đột quỵ",
                "chảy máu nhiều", "đau ngực dữ dội", "khó thở nặng"
            ]
            
            high_priority_signs = [
                "đau ngực", "khó thở", "sốt cao", "co giật",
                "đau bụng dữ dội", "chấn thương đầu"
            ]
            
            for sign in critical_signs:
                if sign in symptoms_lower:
                    emergency_indicators.append(sign)
                    emergency_level = "critical"
            
            if emergency_level != "critical":
                for sign in high_priority_signs:
                    if sign in symptoms_lower:
                        emergency_indicators.append(sign)
                        emergency_level = "high"
            
            # Get recommended actions
            actions = self._get_emergency_actions(emergency_level)
            
            return {
                "is_emergency": len(emergency_indicators) > 0,
                "emergency_level": emergency_level,
                "indicators": emergency_indicators,
                "recommended_actions": actions,
                "confidence": 0.8 if emergency_indicators else 0.3
            }
            
        except Exception as e:
            logger.error(f"Failed to check emergency condition: {str(e)}")
            return {
                "is_emergency": False,
                "emergency_level": "unknown",
                "error": str(e)
            }
    
    async def _search_database_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Search medical knowledge in database"""
        try:
            result = self.supabase.table("medical_knowledge_base").select("*").or_(
                f"name.ilike.%{query}%,vietnamese_name.ilike.%{query}%,keywords.cs.{[query]}"
            ).limit(5).execute()
            
            matches = []
            for item in result.data or []:
                matches.append({
                    "condition_id": f"db_{item['id']}",
                    "condition_data": {
                        "vietnamese_names": [item["vietnamese_name"]] if item["vietnamese_name"] else [],
                        "english_names": [item["name"]],
                        "symptoms": item.get("symptoms", []),
                        "treatments": item.get("treatments", []),
                        "is_emergency": item.get("is_emergency_condition", False)
                    },
                    "relevance_score": 6,
                    "matched_terms": [query]
                })
            
            return matches
            
        except Exception as e:
            logger.error(f"Failed to search database knowledge: {str(e)}")
            return []
    
    async def _search_database_hospitals(
        self,
        condition: str,
        location: Optional[str],
        specialty: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Search hospitals in database"""
        try:
            query = self.supabase.table("users").select("*").eq("user_type", "hospital")
            
            if location:
                query = query.ilike("city", f"%{location}%")
            
            result = query.limit(10).execute()
            
            hospitals = []
            for hospital in result.data or []:
                score = 5  # Base score for database hospitals
                
                hospitals.append({
                    "hospital_id": f"db_{hospital['id']}",
                    "hospital_data": {
                        "name": hospital["organization_name"] or hospital["full_name"],
                        "location": f"{hospital.get('city', '')}, {hospital.get('province', '')}",
                        "type": "registered",
                        "contact": hospital.get("phone"),
                        "address": hospital.get("address")
                    },
                    "relevance_score": score
                })
            
            return hospitals
            
        except Exception as e:
            logger.error(f"Failed to search database hospitals: {str(e)}")
            return []
    
    async def _get_condition_specialties(self, condition: str) -> List[str]:
        """Get required medical specialties for a condition"""
        condition_lower = condition.lower()
        
        for condition_id, condition_data in self.common_conditions.items():
            for name in condition_data["vietnamese_names"] + condition_data["english_names"]:
                if name.lower() in condition_lower:
                    return condition_data.get("specialties", [])
        
        return []
    
    def _get_emergency_actions(self, emergency_level: str) -> List[str]:
        """Get recommended actions for emergency level"""
        actions = {
            "critical": [
                "Gọi cấp cứu 115 ngay lập tức",
                "Đưa đến bệnh viện gần nhất",
                "Thực hiện sơ cứu cơ bản nếu biết",
                "Thông báo cho gia đình"
            ],
            "high": [
                "Liên hệ bệnh viện hoặc bác sĩ",
                "Chuẩn bị đưa đến cơ sở y tế",
                "Theo dõi triệu chứng chặt chẽ",
                "Chuẩn bị giấy tờ y tế"
            ],
            "medium": [
                "Theo dõi triệu chứng",
                "Liên hệ phòng khám",
                "Nghỉ ngơi và chăm sóc tại nhà",
                "Đặt lịch khám nếu cần"
            ],
            "low": [
                "Theo dõi tình trạng",
                "Tự chăm sóc tại nhà",
                "Liên hệ bác sĩ nếu xấu đi"
            ]
        }
        
        return actions.get(emergency_level, actions["low"])


# Global knowledge base instance
medical_knowledge_base = MedicalKnowledgeBase()
