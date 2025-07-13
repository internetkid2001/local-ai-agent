"""
Memory System with Semantic Search

Advanced memory management system that provides:
- Semantic memory storage and retrieval
- Vector-based similarity search
- Memory consolidation and optimization
- Long-term and short-term memory management
- Context-aware memory recall
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MemoryType(Enum):
    EPISODIC = "episodic"      # Specific events and experiences
    SEMANTIC = "semantic"      # Facts and knowledge
    PROCEDURAL = "procedural"  # Skills and procedures
    WORKING = "working"        # Temporary working memory

@dataclass
class MemoryItem:
    id: str
    content: str
    memory_type: MemoryType
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    importance_score: float = 0.5
    tags: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_accessed is None:
            self.last_accessed = self.created_at
        if self.tags is None:
            self.tags = []

class MemoryConsolidationStrategy(Enum):
    FREQUENCY_BASED = "frequency"      # Based on access frequency
    RECENCY_BASED = "recency"         # Based on recent access
    IMPORTANCE_BASED = "importance"    # Based on importance scores
    HYBRID = "hybrid"                 # Combination of all factors

class SemanticMemoryStore:
    """Vector-based semantic memory storage"""
    
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.memories: Dict[str, MemoryItem] = {}
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.memory_ids: List[str] = []
        
    def add_memory(self, memory: MemoryItem) -> None:
        """Add a memory item to the store"""
        if memory.embedding is None:
            raise ValueError("Memory item must have an embedding")
            
        self.memories[memory.id] = memory
        self._update_embeddings_matrix()
        
    def _update_embeddings_matrix(self) -> None:
        """Update the embeddings matrix for efficient similarity search"""
        if not self.memories:
            self.embeddings_matrix = None
            self.memory_ids = []
            return
            
        embeddings = []
        self.memory_ids = []
        
        for memory_id, memory in self.memories.items():
            if memory.embedding:
                embeddings.append(memory.embedding)
                self.memory_ids.append(memory_id)
                
        if embeddings:
            self.embeddings_matrix = np.array(embeddings)
            
    def similarity_search(self, query_embedding: List[float], top_k: int = 10) -> List[Tuple[str, float]]:
        """Find most similar memories using cosine similarity"""
        if self.embeddings_matrix is None or not query_embedding:
            return []
            
        query_vec = np.array(query_embedding).reshape(1, -1)
        
        # Normalize vectors
        query_norm = query_vec / np.linalg.norm(query_vec)
        embeddings_norm = self.embeddings_matrix / np.linalg.norm(self.embeddings_matrix, axis=1, keepdims=True)
        
        # Calculate cosine similarity
        similarities = np.dot(embeddings_norm, query_norm.T).flatten()
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            memory_id = self.memory_ids[idx]
            similarity = float(similarities[idx])
            results.append((memory_id, similarity))
            
        return results

class MemorySystem:
    """Advanced memory management system with semantic search capabilities"""
    
    def __init__(self, 
                 storage_path: Optional[str] = None,
                 embedding_dimension: int = 768,
                 working_memory_limit: int = 50,
                 consolidation_strategy: MemoryConsolidationStrategy = MemoryConsolidationStrategy.HYBRID):
        
        self.storage_path = Path(storage_path) if storage_path else Path("memory_store")
        self.storage_path.mkdir(exist_ok=True)
        
        self.semantic_store = SemanticMemoryStore(embedding_dimension)
        self.working_memory_limit = working_memory_limit
        self.consolidation_strategy = consolidation_strategy
        
        # Memory stores by type
        self.episodic_memories: Dict[str, MemoryItem] = {}
        self.semantic_memories: Dict[str, MemoryItem] = {}
        self.procedural_memories: Dict[str, MemoryItem] = {}
        self.working_memories: Dict[str, MemoryItem] = {}
        
        # Load existing memories
        self._load_memories()
        
    async def store_memory(self, 
                          content: str, 
                          memory_type: MemoryType,
                          embedding: Optional[List[float]] = None,
                          metadata: Optional[Dict[str, Any]] = None,
                          importance_score: float = 0.5,
                          tags: Optional[List[str]] = None) -> str:
        """Store a new memory item"""
        
        memory_id = f"{memory_type.value}_{datetime.now().isoformat()}_{hash(content) % 10000}"
        
        memory = MemoryItem(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            embedding=embedding,
            metadata=metadata or {},
            importance_score=importance_score,
            tags=tags or []
        )
        
        # Store in appropriate memory type
        if memory_type == MemoryType.EPISODIC:
            self.episodic_memories[memory_id] = memory
        elif memory_type == MemoryType.SEMANTIC:
            self.semantic_memories[memory_id] = memory
        elif memory_type == MemoryType.PROCEDURAL:
            self.procedural_memories[memory_id] = memory
        elif memory_type == MemoryType.WORKING:
            self.working_memories[memory_id] = memory
            await self._manage_working_memory()
            
        # Add to semantic store if embedding provided
        if embedding:
            self.semantic_store.add_memory(memory)
            
        await self._persist_memory(memory)
        logger.info(f"Stored memory: {memory_id}")
        
        return memory_id
        
    async def retrieve_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve a specific memory by ID"""
        
        # Search in all memory stores
        for store in [self.episodic_memories, self.semantic_memories, 
                     self.procedural_memories, self.working_memories]:
            if memory_id in store:
                memory = store[memory_id]
                memory.last_accessed = datetime.now()
                memory.access_count += 1
                await self._persist_memory(memory)
                return memory
                
        return None
        
    async def semantic_search(self, 
                            query: str,
                            query_embedding: Optional[List[float]] = None,
                            memory_types: Optional[List[MemoryType]] = None,
                            top_k: int = 10,
                            min_similarity: float = 0.5) -> List[MemoryItem]:
        """Search for memories using semantic similarity"""
        
        if not query_embedding:
            # Would normally generate embedding here using a model
            logger.warning("No query embedding provided for semantic search")
            return []
            
        # Get similar memory IDs
        similar_ids = self.semantic_store.similarity_search(query_embedding, top_k * 2)
        
        results = []
        for memory_id, similarity in similar_ids:
            if similarity < min_similarity:
                continue
                
            memory = await self.retrieve_memory(memory_id)
            if memory and (not memory_types or memory.memory_type in memory_types):
                results.append(memory)
                
            if len(results) >= top_k:
                break
                
        return results
        
    async def search_by_tags(self, tags: List[str], exact_match: bool = False) -> List[MemoryItem]:
        """Search memories by tags"""
        
        results = []
        all_memories = {**self.episodic_memories, **self.semantic_memories,
                       **self.procedural_memories, **self.working_memories}
        
        for memory in all_memories.values():
            if exact_match:
                if all(tag in memory.tags for tag in tags):
                    results.append(memory)
            else:
                if any(tag in memory.tags for tag in tags):
                    results.append(memory)
                    
        return sorted(results, key=lambda m: m.importance_score, reverse=True)
        
    async def search_by_content(self, query: str, case_sensitive: bool = False) -> List[MemoryItem]:
        """Search memories by content text"""
        
        results = []
        all_memories = {**self.episodic_memories, **self.semantic_memories,
                       **self.procedural_memories, **self.working_memories}
        
        search_query = query if case_sensitive else query.lower()
        
        for memory in all_memories.values():
            content = memory.content if case_sensitive else memory.content.lower()
            if search_query in content:
                results.append(memory)
                
        return sorted(results, key=lambda m: m.importance_score, reverse=True)
        
    async def get_recent_memories(self, 
                                memory_type: Optional[MemoryType] = None,
                                hours: int = 24,
                                limit: int = 50) -> List[MemoryItem]:
        """Get recent memories within specified time window"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        results = []
        
        stores = [self.episodic_memories, self.semantic_memories,
                 self.procedural_memories, self.working_memories]
        
        if memory_type:
            if memory_type == MemoryType.EPISODIC:
                stores = [self.episodic_memories]
            elif memory_type == MemoryType.SEMANTIC:
                stores = [self.semantic_memories]
            elif memory_type == MemoryType.PROCEDURAL:
                stores = [self.procedural_memories]
            elif memory_type == MemoryType.WORKING:
                stores = [self.working_memories]
                
        for store in stores:
            for memory in store.values():
                if memory.created_at >= cutoff_time:
                    results.append(memory)
                    
        return sorted(results, key=lambda m: m.created_at, reverse=True)[:limit]
        
    async def consolidate_memories(self) -> Dict[str, int]:
        """Consolidate memories based on strategy"""
        
        consolidated = {
            "deleted": 0,
            "merged": 0,
            "promoted": 0
        }
        
        if self.consolidation_strategy == MemoryConsolidationStrategy.FREQUENCY_BASED:
            consolidated.update(await self._consolidate_by_frequency())
        elif self.consolidation_strategy == MemoryConsolidationStrategy.RECENCY_BASED:
            consolidated.update(await self._consolidate_by_recency())
        elif self.consolidation_strategy == MemoryConsolidationStrategy.IMPORTANCE_BASED:
            consolidated.update(await self._consolidate_by_importance())
        else:  # HYBRID
            consolidated.update(await self._consolidate_hybrid())
            
        return consolidated
        
    async def _manage_working_memory(self) -> None:
        """Manage working memory size and move items to long-term storage"""
        
        if len(self.working_memories) <= self.working_memory_limit:
            return
            
        # Sort by last accessed time and importance
        sorted_memories = sorted(
            self.working_memories.values(),
            key=lambda m: (m.last_accessed, m.importance_score)
        )
        
        # Move oldest, least important memories to appropriate long-term storage
        excess_count = len(self.working_memories) - self.working_memory_limit
        
        for memory in sorted_memories[:excess_count]:
            # Determine destination based on content and importance
            if memory.importance_score > 0.7:
                if "procedure" in memory.content.lower() or "how to" in memory.content.lower():
                    memory.memory_type = MemoryType.PROCEDURAL
                    self.procedural_memories[memory.id] = memory
                else:
                    memory.memory_type = MemoryType.SEMANTIC
                    self.semantic_memories[memory.id] = memory
            else:
                memory.memory_type = MemoryType.EPISODIC
                self.episodic_memories[memory.id] = memory
                
            # Remove from working memory
            del self.working_memories[memory.id]
            await self._persist_memory(memory)
            
    async def _consolidate_by_frequency(self) -> Dict[str, int]:
        """Consolidate based on access frequency"""
        deleted = 0
        
        # Delete rarely accessed memories older than 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for store in [self.episodic_memories, self.semantic_memories]:
            to_delete = []
            for memory_id, memory in store.items():
                if (memory.created_at < cutoff_date and 
                    memory.access_count < 2 and 
                    memory.importance_score < 0.3):
                    to_delete.append(memory_id)
                    
            for memory_id in to_delete:
                del store[memory_id]
                deleted += 1
                
        return {"deleted": deleted}
        
    async def _consolidate_by_recency(self) -> Dict[str, int]:
        """Consolidate based on recency"""
        deleted = 0
        
        # Delete old, unimportant memories
        cutoff_date = datetime.now() - timedelta(days=60)
        
        for store in [self.episodic_memories]:
            to_delete = []
            for memory_id, memory in store.items():
                if (memory.last_accessed < cutoff_date and 
                    memory.importance_score < 0.4):
                    to_delete.append(memory_id)
                    
            for memory_id in to_delete:
                del store[memory_id]
                deleted += 1
                
        return {"deleted": deleted}
        
    async def _consolidate_by_importance(self) -> Dict[str, int]:
        """Consolidate based on importance scores"""
        deleted = 0
        promoted = 0
        
        # Delete low importance memories
        for store in [self.episodic_memories, self.working_memories]:
            to_delete = []
            for memory_id, memory in store.items():
                if memory.importance_score < 0.2:
                    to_delete.append(memory_id)
                    
            for memory_id in to_delete:
                del store[memory_id]
                deleted += 1
                
        # Promote high importance episodic to semantic
        to_promote = []
        for memory_id, memory in self.episodic_memories.items():
            if memory.importance_score > 0.8 and memory.access_count > 5:
                to_promote.append(memory_id)
                
        for memory_id in to_promote:
            memory = self.episodic_memories[memory_id]
            memory.memory_type = MemoryType.SEMANTIC
            self.semantic_memories[memory_id] = memory
            del self.episodic_memories[memory_id]
            promoted += 1
            
        return {"deleted": deleted, "promoted": promoted}
        
    async def _consolidate_hybrid(self) -> Dict[str, int]:
        """Hybrid consolidation strategy"""
        results = {"deleted": 0, "promoted": 0, "merged": 0}
        
        # Combine all strategies with weights
        freq_results = await self._consolidate_by_frequency()
        importance_results = await self._consolidate_by_importance()
        
        results["deleted"] += freq_results.get("deleted", 0)
        results["deleted"] += importance_results.get("deleted", 0)
        results["promoted"] += importance_results.get("promoted", 0)
        
        return results
        
    async def _persist_memory(self, memory: MemoryItem) -> None:
        """Persist memory to storage"""
        
        memory_file = self.storage_path / f"{memory.memory_type.value}" / f"{memory.id}.json"
        memory_file.parent.mkdir(exist_ok=True)
        
        # Convert memory to dict for JSON serialization
        memory_dict = asdict(memory)
        memory_dict['created_at'] = memory.created_at.isoformat() if memory.created_at else None
        memory_dict['last_accessed'] = memory.last_accessed.isoformat() if memory.last_accessed else None
        memory_dict['memory_type'] = memory.memory_type.value
        
        with open(memory_file, 'w') as f:
            json.dump(memory_dict, f, indent=2)
            
    def _load_memories(self) -> None:
        """Load memories from storage"""
        
        for memory_type in MemoryType:
            type_dir = self.storage_path / memory_type.value
            if not type_dir.exists():
                continue
                
            for memory_file in type_dir.glob("*.json"):
                try:
                    with open(memory_file, 'r') as f:
                        memory_dict = json.load(f)
                        
                    # Convert back to MemoryItem
                    memory_dict['memory_type'] = MemoryType(memory_dict['memory_type'])
                    if memory_dict['created_at']:
                        memory_dict['created_at'] = datetime.fromisoformat(memory_dict['created_at'])
                    if memory_dict['last_accessed']:
                        memory_dict['last_accessed'] = datetime.fromisoformat(memory_dict['last_accessed'])
                        
                    memory = MemoryItem(**memory_dict)
                    
                    # Store in appropriate memory store
                    if memory_type == MemoryType.EPISODIC:
                        self.episodic_memories[memory.id] = memory
                    elif memory_type == MemoryType.SEMANTIC:
                        self.semantic_memories[memory.id] = memory
                    elif memory_type == MemoryType.PROCEDURAL:
                        self.procedural_memories[memory.id] = memory
                    elif memory_type == MemoryType.WORKING:
                        self.working_memories[memory.id] = memory
                        
                    # Add to semantic store if has embedding
                    if memory.embedding:
                        self.semantic_store.add_memory(memory)
                        
                except Exception as e:
                    logger.error(f"Failed to load memory from {memory_file}: {e}")
                    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        
        total_memories = (len(self.episodic_memories) + len(self.semantic_memories) + 
                         len(self.procedural_memories) + len(self.working_memories))
        
        return {
            "total_memories": total_memories,
            "episodic_count": len(self.episodic_memories),
            "semantic_count": len(self.semantic_memories),
            "procedural_count": len(self.procedural_memories),
            "working_count": len(self.working_memories),
            "semantic_store_size": len(self.semantic_store.memories),
            "working_memory_utilization": len(self.working_memories) / self.working_memory_limit,
            "consolidation_strategy": self.consolidation_strategy.value
        }
        
    async def cleanup(self) -> None:
        """Cleanup and final consolidation"""
        await self.consolidate_memories()
        logger.info("Memory system cleanup completed")