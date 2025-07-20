"""
Comprehensive Database Query Service for AI Agent
Provides intelligent querying across all Supabase tables for chatbot responses
"""
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import structlog

from ..core.supabase import get_supabase_service

logger = structlog.get_logger()


class DatabaseQueryService:
    """
    Comprehensive database query service for AI Agent
    Handles multi-table queries with intelligent result summarization
    """
    
    def __init__(self):
        self.supabase = get_supabase_service()
        
        # Token limits for response optimization
        self.max_context_tokens = 3500  # Leave room for system prompt and user message
        self.max_items_per_table = 10   # Limit items per table to prevent overflow
        
        # Query patterns for different entity types
        self.query_patterns = {
            'donations': [
                r'quyên góp.*?([a-zA-ZÀ-ỹ\s]+)',
                r'donate.*?([a-zA-ZÀ-ỹ\s]+)',
                r'thuốc.*?([a-zA-ZÀ-ỹ\s]+)',
                r'medication.*?([a-zA-ZÀ-ỹ\s]+)',
                r'phiên.*?quyên góp',
                r'donation.*?session'
            ],
            'campaigns': [
                r'chiến dịch.*?([a-zA-ZÀ-ỹ\s]+)',
                r'campaign.*?([a-zA-ZÀ-ỹ\s]+)',
                r'gây quỹ.*?([a-zA-ZÀ-ỹ\s]+)',
                r'fundrais.*?([a-zA-ZÀ-ỹ\s]+)'
            ],
            'transactions': [
                r'giao dịch.*?([a-zA-Z0-9\-]+)',
                r'transaction.*?([a-zA-Z0-9\-]+)',
                r'thanh toán.*?([a-zA-Z0-9\-]+)',
                r'payment.*?([a-zA-Z0-9\-]+)'
            ],
            'blockchain': [
                r'blockchain.*?([a-zA-Z0-9\-]+)',
                r'hash.*?([a-zA-Z0-9\-]+)',
                r'tx.*?([a-zA-Z0-9\-]+)',
                r'smart contract'
            ],
            'fraud': [
                r'gian lận',
                r'fraud',
                r'phân tích.*?gian lận',
                r'fraud.*?analysis',
                r'suspicious'
            ],
            'medications': [
                r'thuốc.*?([a-zA-ZÀ-ỹ\s]+)',
                r'medication.*?([a-zA-ZÀ-ỹ\s]+)',
                r'dược phẩm.*?([a-zA-ZÀ-ỹ\s]+)',
                r'pharmaceutical.*?([a-zA-ZÀ-ỹ\s]+)'
            ]
        }

    async def query_comprehensive_context(
        self, 
        user_message: str, 
        conversation_type: str = "general_support"
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Query comprehensive context from database based on user message
        
        Args:
            user_message: User's query message
            conversation_type: Type of conversation
            
        Returns:
            Tuple of (formatted_context, raw_data_items)
        """
        try:
            # Detect what user is asking about
            query_intents = self._detect_query_intents(user_message)
            
            if not query_intents:
                return "", []
            
            # Query relevant data from multiple tables
            context_data = {}
            raw_items = []
            
            for intent, search_terms in query_intents.items():
                if intent == 'donations':
                    data, items = await self._query_donations(search_terms)
                elif intent == 'campaigns':
                    data, items = await self._query_campaigns(search_terms)
                elif intent == 'transactions':
                    data, items = await self._query_transactions(search_terms)
                elif intent == 'blockchain':
                    data, items = await self._query_blockchain_transactions(search_terms)
                elif intent == 'fraud':
                    data, items = await self._query_fraud_analysis(search_terms)
                elif intent == 'medications':
                    data, items = await self._query_medications(search_terms)
                
                if data:
                    context_data[intent] = data
                    raw_items.extend(items)
            
            # Format context for AI consumption
            formatted_context = self._format_context_for_ai(context_data, user_message)
            
            logger.info(
                "Database context queried",
                intents=list(query_intents.keys()),
                context_length=len(formatted_context),
                items_count=len(raw_items)
            )
            
            return formatted_context, raw_items
            
        except Exception as e:
            logger.error(f"Failed to query comprehensive context: {str(e)}")
            return "", []

    def _detect_query_intents(self, user_message: str) -> Dict[str, List[str]]:
        """Detect what the user is asking about and extract search terms"""
        intents = {}
        message_lower = user_message.lower()
        
        for intent, patterns in self.query_patterns.items():
            search_terms = []
            
            for pattern in patterns:
                matches = re.finditer(pattern, message_lower, re.IGNORECASE)
                for match in matches:
                    if match.groups():
                        # Extract captured group (search term)
                        term = match.group(1).strip()
                        if len(term) > 2:  # Avoid very short terms
                            search_terms.append(term)
                    else:
                        # Pattern matched but no specific term captured
                        search_terms.append(intent)
            
            if search_terms:
                intents[intent] = list(set(search_terms))  # Remove duplicates
        
        return intents

    async def _query_donations(self, search_terms: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """Query donations table"""
        try:
            results = []
            raw_items = []
            
            for term in search_terms[:3]:  # Limit search terms
                # Search by medication name, description, or donor info
                query = self.supabase.table("donations").select("*")
                
                # Build OR conditions for flexible search
                or_conditions = []
                if term != 'donations':
                    or_conditions.extend([
                        f"medication_name.ilike.%{term}%",
                        f"description.ilike.%{term}%",
                        f"notes.ilike.%{term}%"
                    ])
                
                if or_conditions:
                    result = query.or_(",".join(or_conditions)).limit(self.max_items_per_table).execute()
                else:
                    # General donations query
                    result = query.order("created_at", desc=True).limit(self.max_items_per_table).execute()
                
                if result.data:
                    results.extend(result.data)
                    raw_items.extend(result.data)
            
            return results, raw_items
            
        except Exception as e:
            logger.error(f"Failed to query donations: {str(e)}")
            return [], []

    async def _query_campaigns(self, search_terms: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """Query campaigns table"""
        try:
            results = []
            raw_items = []
            
            for term in search_terms[:3]:
                query = self.supabase.table("campaigns").select("*")
                
                if term != 'campaigns':
                    or_conditions = [
                        f"title.ilike.%{term}%",
                        f"description.ilike.%{term}%",
                        f"medical_condition.ilike.%{term}%"
                    ]
                    result = query.or_(",".join(or_conditions)).limit(self.max_items_per_table).execute()
                else:
                    result = query.order("created_at", desc=True).limit(self.max_items_per_table).execute()
                
                if result.data:
                    results.extend(result.data)
                    raw_items.extend(result.data)
            
            return results, raw_items
            
        except Exception as e:
            logger.error(f"Failed to query campaigns: {str(e)}")
            return [], []

    async def _query_transactions(self, search_terms: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """Query transactions table"""
        try:
            results = []
            raw_items = []
            
            for term in search_terms[:3]:
                # Try different transaction-related tables
                tables_to_search = ["transactions", "donation_transactions", "payments"]
                
                for table in tables_to_search:
                    try:
                        query = self.supabase.table(table).select("*")
                        
                        if term != 'transactions':
                            # Search by transaction ID, reference, or description
                            or_conditions = [
                                f"id.eq.{term}",
                                f"transaction_id.ilike.%{term}%",
                                f"reference.ilike.%{term}%"
                            ]
                            result = query.or_(",".join(or_conditions)).limit(5).execute()
                        else:
                            result = query.order("created_at", desc=True).limit(5).execute()
                        
                        if result.data:
                            results.extend(result.data)
                            raw_items.extend(result.data)
                    except:
                        continue  # Table might not exist
            
            return results, raw_items
            
        except Exception as e:
            logger.error(f"Failed to query transactions: {str(e)}")
            return [], []

    async def _query_blockchain_transactions(self, search_terms: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """Query blockchain transactions from database"""
        try:
            results = []
            raw_items = []
            
            # Search blockchain-related tables
            blockchain_tables = ["blockchain_transactions", "smart_contract_events", "audit_trail"]
            
            for table in blockchain_tables:
                try:
                    query = self.supabase.table(table).select("*")
                    
                    for term in search_terms[:2]:
                        if term != 'blockchain':
                            or_conditions = [
                                f"transaction_hash.ilike.%{term}%",
                                f"block_hash.ilike.%{term}%",
                                f"contract_address.ilike.%{term}%"
                            ]
                            result = query.or_(",".join(or_conditions)).limit(5).execute()
                        else:
                            result = query.order("created_at", desc=True).limit(5).execute()
                        
                        if result.data:
                            results.extend(result.data)
                            raw_items.extend(result.data)
                except:
                    continue
            
            return results, raw_items
            
        except Exception as e:
            logger.error(f"Failed to query blockchain transactions: {str(e)}")
            return [], []

    async def _query_fraud_analysis(self, search_terms: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """Query fraud analysis data"""
        try:
            results = []
            raw_items = []
            
            # Query fraud analysis table
            result = self.supabase.table("fraud_analysis").select("*").order("created_at", desc=True).limit(self.max_items_per_table).execute()
            
            if result.data:
                results.extend(result.data)
                raw_items.extend(result.data)
            
            # Also query suspicious activities if exists
            try:
                suspicious_result = self.supabase.table("suspicious_activities").select("*").order("created_at", desc=True).limit(5).execute()
                if suspicious_result.data:
                    results.extend(suspicious_result.data)
                    raw_items.extend(suspicious_result.data)
            except:
                pass
            
            return results, raw_items
            
        except Exception as e:
            logger.error(f"Failed to query fraud analysis: {str(e)}")
            return [], []

    async def _query_medications(self, search_terms: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """Query medication information"""
        try:
            results = []
            raw_items = []
            
            # Search medication catalog
            for term in search_terms[:3]:
                query = self.supabase.table("medication_catalog").select("*")
                
                or_conditions = [
                    f"name.ilike.%{term}%",
                    f"vietnamese_name.ilike.%{term}%",
                    f"active_ingredient.ilike.%{term}%"
                ]
                
                result = query.or_(",".join(or_conditions)).limit(5).execute()
                
                if result.data:
                    results.extend(result.data)
                    raw_items.extend(result.data)
            
            return results, raw_items
            
        except Exception as e:
            logger.error(f"Failed to query medications: {str(e)}")
            return [], []

    def _format_context_for_ai(self, context_data: Dict[str, List[Dict]], user_message: str) -> str:
        """Format queried data into AI-consumable context"""
        if not context_data:
            return ""
        
        context_parts = []
        context_parts.append(f"=== RELEVANT DATABASE INFORMATION FOR: {user_message} ===\n")
        
        for data_type, items in context_data.items():
            if not items:
                continue
                
            context_parts.append(f"\n--- {data_type.upper()} DATA ---")
            
            # Summarize items based on type
            if data_type == 'donations':
                context_parts.extend(self._format_donations_context(items))
            elif data_type == 'campaigns':
                context_parts.extend(self._format_campaigns_context(items))
            elif data_type == 'transactions':
                context_parts.extend(self._format_transactions_context(items))
            elif data_type == 'blockchain':
                context_parts.extend(self._format_blockchain_context(items))
            elif data_type == 'fraud':
                context_parts.extend(self._format_fraud_context(items))
            elif data_type == 'medications':
                context_parts.extend(self._format_medications_context(items))
        
        context_parts.append("\n=== END DATABASE INFORMATION ===")
        
        full_context = "\n".join(context_parts)
        
        # Truncate if too long (rough token estimation: 1 token ≈ 4 characters)
        if len(full_context) > self.max_context_tokens * 4:
            full_context = full_context[:self.max_context_tokens * 4] + "\n... (truncated for length)"
        
        return full_context

    def _format_donations_context(self, donations: List[Dict]) -> List[str]:
        """Format donations data for AI context"""
        lines = []
        for donation in donations[:5]:  # Limit to prevent overflow
            lines.append(f"• Donation ID: {donation.get('id')}")
            if donation.get('medication_name'):
                lines.append(f"  Medication: {donation['medication_name']}")
            if donation.get('quantity'):
                lines.append(f"  Quantity: {donation['quantity']}")
            if donation.get('expiry_date'):
                lines.append(f"  Expiry: {donation['expiry_date']}")
            if donation.get('status'):
                lines.append(f"  Status: {donation['status']}")
            if donation.get('description'):
                lines.append(f"  Description: {donation['description'][:100]}...")
            lines.append("")
        return lines

    def _format_campaigns_context(self, campaigns: List[Dict]) -> List[str]:
        """Format campaigns data for AI context"""
        lines = []
        for campaign in campaigns[:5]:
            lines.append(f"• Campaign: {campaign.get('title', 'N/A')}")
            if campaign.get('medical_condition'):
                lines.append(f"  Condition: {campaign['medical_condition']}")
            if campaign.get('goal_amount'):
                lines.append(f"  Goal: {campaign['goal_amount']:,} VND")
            if campaign.get('current_amount'):
                lines.append(f"  Raised: {campaign['current_amount']:,} VND")
            if campaign.get('status'):
                lines.append(f"  Status: {campaign['status']}")
            lines.append("")
        return lines

    def _format_transactions_context(self, transactions: List[Dict]) -> List[str]:
        """Format transactions data for AI context"""
        lines = []
        for tx in transactions[:5]:
            lines.append(f"• Transaction ID: {tx.get('id')}")
            if tx.get('amount'):
                lines.append(f"  Amount: {tx['amount']:,} VND")
            if tx.get('status'):
                lines.append(f"  Status: {tx['status']}")
            if tx.get('created_at'):
                lines.append(f"  Date: {tx['created_at']}")
            if tx.get('reference'):
                lines.append(f"  Reference: {tx['reference']}")
            lines.append("")
        return lines

    def _format_blockchain_context(self, blockchain_data: List[Dict]) -> List[str]:
        """Format blockchain data for AI context"""
        lines = []
        for item in blockchain_data[:3]:
            lines.append(f"• Blockchain Record:")
            if item.get('transaction_hash'):
                lines.append(f"  Hash: {item['transaction_hash']}")
            if item.get('block_number'):
                lines.append(f"  Block: {item['block_number']}")
            if item.get('contract_address'):
                lines.append(f"  Contract: {item['contract_address']}")
            if item.get('event_type'):
                lines.append(f"  Event: {item['event_type']}")
            lines.append("")
        return lines

    def _format_fraud_context(self, fraud_data: List[Dict]) -> List[str]:
        """Format fraud analysis data for AI context"""
        lines = []
        for item in fraud_data[:3]:
            lines.append(f"• Fraud Analysis:")
            if item.get('fraud_score'):
                lines.append(f"  Risk Score: {item['fraud_score']}/100")
            if item.get('risk_factors'):
                lines.append(f"  Risk Factors: {', '.join(item['risk_factors'])}")
            if item.get('status'):
                lines.append(f"  Status: {item['status']}")
            if item.get('created_at'):
                lines.append(f"  Date: {item['created_at']}")
            lines.append("")
        return lines

    def _format_medications_context(self, medications: List[Dict]) -> List[str]:
        """Format medication data for AI context"""
        lines = []
        for med in medications[:5]:
            lines.append(f"• Medication: {med.get('name', 'N/A')}")
            if med.get('vietnamese_name'):
                lines.append(f"  Vietnamese: {med['vietnamese_name']}")
            if med.get('active_ingredient'):
                lines.append(f"  Active Ingredient: {med['active_ingredient']}")
            if med.get('dosage_form'):
                lines.append(f"  Form: {med['dosage_form']}")
            if med.get('indications'):
                lines.append(f"  Uses: {med['indications'][:100]}...")
            lines.append("")
        return lines


# Global database query service instance
database_query_service = DatabaseQueryService()
