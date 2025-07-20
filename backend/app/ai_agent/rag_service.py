"""
Ytili RAG (Retrieval-Augmented Generation) Service
Provides semantic search and context enhancement for AI conversations
"""
import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
import structlog
import numpy as np
from pathlib import Path

# SentenceTransformer is heavy; import lazily / handle missing env.
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:  # library not present in minimal env
    SentenceTransformer = None  # fallback to None; embedding generation disabled

from ..core.supabase import get_supabase_service
from ..core.config import settings

logger = structlog.get_logger()

# Paths for offline cache
OFFLINE_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OFFLINE_EMBED = OFFLINE_DATA_DIR / "knowledge_embeddings.npy"
OFFLINE_META = OFFLINE_DATA_DIR / "knowledge_meta.json"


class SupabaseRAGService:
    """
    RAG service using Supabase as knowledge base with semantic search capabilities
    """
    
    def __init__(self):
        self.supabase = get_supabase_service()
        self.embedding_model = None
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dim

        # Initialize embedding model only if library is available
        if SentenceTransformer is not None:
            self._initialize_embedding_model()
        else:
            logger.warning("sentence-transformers library not installed – embedding generation disabled; RAG will use offline cache or keyword search")

        # Offline cache
        self._offline_loaded = False
        self._offline_embeddings: Optional[np.ndarray] = None
        self._offline_meta: List[Dict[str, Any]] = []
    
    def _initialize_embedding_model(self):
        """Initialize the sentence transformer model for embeddings"""
        try:
            # Use a lightweight multilingual model that works well with Vietnamese
            self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            logger.info("Embedding model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {str(e)}")
            self.embedding_model = None
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using sentence transformers"""
        if not self.embedding_model:
            logger.warning("Embedding model not available")
            return None
        
        try:
            # Run embedding generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                lambda: self.embedding_model.encode(text, convert_to_tensor=False)
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            return None
    
    async def search_knowledge(
        self,
        query: str,
        content_type: Optional[str] = None,
        category: Optional[str] = None,
        language: str = 'vi',
        limit: int = 5,
        similarity_threshold: float = 0.4,  # Lowered from 0.7 to 0.4 for better results
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base using semantic similarity
        
        Args:
            query: Search query
            content_type: Filter by content type (medical_info, drug_info, etc.)
            category: Filter by category
            language: Language filter (default: Vietnamese)
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            use_hybrid: Whether to use hybrid search (semantic + keyword)
            
        Returns:
            List of relevant knowledge items with similarity scores
        """
        try:
            # Generate embedding for query
            query_embedding = await self.get_embedding(query)
            if not query_embedding:
                # Fallback to keyword search only
                return await self._keyword_search(query, content_type, category, language, limit)

            # Use semantic search for now (hybrid search has SQL issues)
            results = await self._semantic_search(
                query_embedding, content_type, category, language, limit, similarity_threshold
            )

            # If no results with semantic search, try with lower threshold
            if not results and similarity_threshold > 0.2:
                logger.info("No results with current threshold, trying lower threshold")
                results = await self._semantic_search(
                    query_embedding, content_type, category, language, limit, 0.2
                )

            # If still no results, fallback to keyword search
            if not results:
                logger.info("Semantic search returned no results, falling back to keyword search")
                results = await self._keyword_search(query, content_type, category, language, limit)

            logger.info(
                "Knowledge search completed",
                query_length=len(query),
                results_count=len(results),
                content_type=content_type,
                category=category
            )

            return results

        except Exception as e:
            logger.error(f"Knowledge search failed: {str(e)}")
            # Emergency fallback - return some verified knowledge
            return await self._get_fallback_knowledge(content_type, category, language, limit)
    
    async def _semantic_search(
        self,
        query_embedding: List[float],
        content_type: Optional[str],
        category: Optional[str],
        language: str,
        limit: int,
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using vector similarity"""
        try:
            # Primary – Supabase RPC
            result = self.supabase.rpc(
                'search_knowledge_semantic',
                {
                    'query_embedding': query_embedding,
                    'content_type_filter': content_type,
                    'category_filter': category,
                    'language_filter': language,
                    'limit_results': limit,
                    'similarity_threshold': similarity_threshold
                }
            ).execute()
            return result.data if result.data else []

        except Exception as e:
            logger.warning("Semantic search via Supabase failed, switching to offline cache", err=str(e))

            # Attempt offline fallback
            offline = await self._semantic_search_offline(
                np.array(query_embedding, dtype=np.float32),
                content_type, category, limit, similarity_threshold
            )
            return offline


    async def _semantic_search_offline(
        self,
        query_vec: np.ndarray,
        content_type: Optional[str],
        category: Optional[str],
        limit: int,
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """Local numpy dot-product search"""
        # Lazy load offline data
        if not self._offline_loaded:
            if OFFLINE_EMBED.exists() and OFFLINE_META.exists():
                try:
                    self._offline_embeddings = np.load(OFFLINE_EMBED)
                    with OFFLINE_META.open("r", encoding="utf-8") as f:
                        self._offline_meta = json.load(f)
                    self._offline_loaded = True
                    logger.info("Offline RAG cache loaded", items=len(self._offline_meta))
                except Exception as cache_err:
                    logger.error("Failed to load offline cache", err=str(cache_err))
                    self._offline_loaded = False
            else:
                logger.warning("Offline cache files not found", path=str(OFFLINE_DATA_DIR))
                self._offline_loaded = False

        if not self._offline_loaded or self._offline_embeddings is None:
            return []

        # Compute similarities (dot product) – assume embeddings already unit-norm
        sims = np.dot(self._offline_embeddings, query_vec)
        top_idx = np.argsort(-sims)[:limit]
        results: List[Dict[str, Any]] = []
        for idx in top_idx:
            score = float(sims[idx])
            if score < similarity_threshold:
                continue
            meta = self._offline_meta[idx]
            # Filter if needed
            if content_type and meta.get("content_type") != content_type:
                continue
            if category and meta.get("category") != category:
                continue
            results.append({**meta, "similarity_score": score})
        return results
    
    async def _hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        content_type: Optional[str],
        category: Optional[str],
        language: str,
        limit: int,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining semantic and keyword matching"""
        try:
            # Call the hybrid search function in Supabase
            result = self.supabase.rpc(
                'search_knowledge_hybrid',
                {
                    'query_text': query,
                    'query_embedding': query_embedding,
                    'content_type_filter': content_type,
                    'category_filter': category,
                    'language_filter': language,
                    'limit_results': limit,
                    'semantic_weight': semantic_weight,
                    'keyword_weight': keyword_weight
                }
            ).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            return []
    
    async def _keyword_search(
        self,
        query: str,
        content_type: Optional[str],
        category: Optional[str],
        language: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback keyword search when embeddings are not available"""
        try:
            query_builder = self.supabase.table('rag_knowledge_base').select(
                'id, title, content, content_type, category, metadata'
            ).eq('is_verified', True).eq('language', language)

            # Add filters
            if content_type:
                query_builder = query_builder.eq('content_type', content_type)
            if category:
                query_builder = query_builder.eq('category', category)

            # Add text search - use ilike for simple text matching
            query_builder = query_builder.ilike('content', f'%{query}%')

            result = query_builder.limit(limit).execute()

            # Add dummy similarity scores for consistency
            for item in result.data:
                item['similarity_score'] = 0.5  # Default score for keyword matches

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}")
            return []

    async def _get_fallback_knowledge(
        self,
        content_type: Optional[str],
        category: Optional[str],
        language: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Emergency fallback - return some verified knowledge"""
        try:
            query_builder = self.supabase.table('rag_knowledge_base').select(
                'id, title, content, content_type, category, metadata'
            ).eq('is_verified', True).eq('language', language)

            # Add filters if specified
            if content_type:
                query_builder = query_builder.eq('content_type', content_type)
            if category:
                query_builder = query_builder.eq('category', category)

            result = query_builder.limit(limit).execute()

            # Add dummy similarity scores
            for item in result.data:
                item['similarity_score'] = 0.3  # Lower score for fallback

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Fallback knowledge retrieval failed: {str(e)}")
            return []
    
    async def enhance_conversation_context(
        self,
        conversation_id: int,
        user_message: str,
        conversation_type: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Enhance conversation with relevant context from knowledge base
        
        Args:
            conversation_id: ID of the conversation
            user_message: Latest user message
            conversation_type: Type of conversation
            
        Returns:
            Tuple of (enhanced_context, knowledge_items_used)
        """
        try:
            # Determine search parameters based on conversation type
            search_params = self._get_search_params_for_conversation_type(conversation_type)
            
            # Search for relevant knowledge
            knowledge_items = await self.search_knowledge(
                query=user_message,
                content_type=search_params.get('content_type'),
                category=search_params.get('category'),
                limit=3,  # Limit to top 3 most relevant items
                similarity_threshold=0.3  # Lowered threshold for better context retrieval
            )
            
            if not knowledge_items:
                return "", []
            
            # Build enhanced context
            context_parts = []
            knowledge_ids = []
            relevance_scores = []
            
            for item in knowledge_items:
                context_parts.append(f"**{item['title']}**\n{item['content']}")
                knowledge_ids.append(item['id'])
                relevance_scores.append(item.get('similarity_score', 0.5))
            
            enhanced_context = "\n\n".join(context_parts)
            
            # Save context usage for tracking
            await self._save_conversation_context(
                conversation_id, knowledge_ids, enhanced_context, user_message, relevance_scores
            )
            
            logger.info(
                "Conversation context enhanced",
                conversation_id=conversation_id,
                knowledge_items_count=len(knowledge_items),
                context_length=len(enhanced_context)
            )
            
            return enhanced_context, knowledge_items
            
        except Exception as e:
            logger.error(f"Failed to enhance conversation context: {str(e)}")
            return "", []
    
    def _get_search_params_for_conversation_type(self, conversation_type: str) -> Dict[str, str]:
        """Get search parameters based on conversation type"""
        type_mapping = {
            'DONATION_ADVISORY': {'content_type': 'procedure_info', 'category': 'donation_process'},
            'MEDICAL_INFO': {'content_type': 'medical_info', 'category': None},
            'CAMPAIGN_HELP': {'content_type': 'procedure_info', 'category': 'fundraising'},
            'EMERGENCY_REQUEST': {'content_type': 'medical_info', 'category': 'emergency'},
            'GENERAL_SUPPORT': {'content_type': None, 'category': None}
        }
        
        return type_mapping.get(conversation_type, {'content_type': None, 'category': None})
    
    async def _save_conversation_context(
        self,
        conversation_id: int,
        knowledge_ids: List[int],
        context_summary: str,
        retrieval_query: str,
        relevance_scores: List[float]
    ) -> bool:
        """Save conversation context usage for tracking and analytics"""
        try:
            context_data = {
                'conversation_id': conversation_id,
                'knowledge_base_ids': knowledge_ids,
                'context_summary': context_summary[:1000],  # Truncate for storage
                'retrieval_query': retrieval_query,
                'relevance_scores': relevance_scores
            }
            
            result = self.supabase.table('rag_conversation_context').insert(context_data).execute()
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Failed to save conversation context: {str(e)}")
            return False
    
    async def add_knowledge_item(
        self,
        title: str,
        content: str,
        content_type: str,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        language: str = 'vi',
        source: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[int]:
        """
        Add new knowledge item to the knowledge base
        
        Returns:
            ID of the created knowledge item, or None if failed
        """
        try:
            # Generate embedding for the content
            embedding = await self.get_embedding(f"{title} {content}")
            
            knowledge_data = {
                'title': title,
                'content': content,
                'content_type': content_type,
                'category': category,
                'subcategory': subcategory,
                'language': language,
                'source': source,
                'keywords': keywords or [],
                'embedding': embedding,
                'metadata': metadata or {},
                'is_verified': False,  # Requires manual verification
                'created_by': 'api'
            }
            
            result = self.supabase.table('rag_knowledge_base').insert(knowledge_data).execute()
            
            if result.data:
                logger.info(f"Knowledge item added successfully: {title}")
                return result.data[0]['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to add knowledge item: {str(e)}")
            return None


# Global RAG service instance
rag_service = SupabaseRAGService()
