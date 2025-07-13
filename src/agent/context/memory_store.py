"""
Memory Store

Persistent memory storage for agent context and learning.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import asyncio
import sqlite3
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class MemoryType(Enum):
    """Types of memories to store"""
    TASK_EXECUTION = "task_execution"
    CONTEXT = "context"
    CONVERSATION = "conversation"
    LEARNING = "learning"
    PATTERN = "pattern"
    ERROR = "error"
    PERFORMANCE = "performance"


@dataclass
class MemoryEntry:
    """Individual memory entry"""
    id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: float
    expiry: Optional[float] = None
    access_count: int = 0
    last_accessed: Optional[float] = None


class MemoryStore:
    """
    Persistent memory storage using SQLite.
    
    Features:
    - Type-based memory organization
    - Automatic expiry and cleanup
    - Access tracking and analytics
    - Full-text search capabilities
    - Memory consolidation and optimization
    """
    
    def __init__(self, db_path: str = "agent_memory.db"):
        """
        Initialize memory store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self._lock = asyncio.Lock()
        
        # Memory configuration
        self.max_memories_per_type = 10000
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
        
        logger.info(f"Memory store initialized with database: {db_path}")
    
    async def initialize(self):
        """Initialize database and create tables"""
        async with self._lock:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            
            # Create memories table
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    expiry REAL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL
                )
            """)
            
            # Create indexes for better performance
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type 
                ON memories(memory_type)
            """)
            
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON memories(timestamp)
            """)
            
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_expiry 
                ON memories(expiry) WHERE expiry IS NOT NULL
            """)
            
            # Create full-text search table
            self.connection.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_search 
                USING fts5(id, content)
            """)
            
            self.connection.commit()
            logger.info("Memory store database initialized")
    
    async def store_memory(self, content: str, memory_type: str = "general",
                          metadata: Optional[Dict[str, Any]] = None, memory_id: Optional[str] = None,
                          expiry: Optional[float] = None) -> str:
        """
        Store a memory entry.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            metadata: Memory metadata
            memory_id: Optional memory ID
            expiry: Optional expiry timestamp
            
        Returns:
            Memory ID
        """
        if not self.connection:
            await self.initialize()
        
        if memory_id is None:
            memory_id = f"{memory_type}_{int(time.time() * 1000)}"
        
        if metadata is None:
            metadata = {}
        
        content_data = {"content": content}
        content_json = json.dumps(content_data)
        metadata_json = json.dumps(metadata)
        timestamp = time.time()
        
        async with self._lock:
            # Store in main table
            self.connection.execute("""
                INSERT OR REPLACE INTO memories 
                (id, memory_type, content, metadata, timestamp, expiry, access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, 0, NULL)
            """, (memory_id, memory_type, content_json, metadata_json, timestamp, expiry))
            
            # Add to search index
            search_content = content + " " + json.dumps(metadata)
            self.connection.execute("""
                INSERT OR REPLACE INTO memory_search (id, content)
                VALUES (?, ?)
            """, (memory_id, search_content))
            
            self.connection.commit()
        
        # Cleanup if necessary
        await self._cleanup_if_needed()
        
        logger.debug(f"Stored memory: {memory_id} ({memory_type})")
        return memory_id
    
    async def retrieve_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a specific memory by ID"""
        if not self.connection:
            await self.initialize()
        
        async with self._lock:
            cursor = self.connection.execute("""
                SELECT * FROM memories WHERE id = ?
            """, (memory_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Check expiry
            if row['expiry'] and time.time() > row['expiry']:
                await self.delete_memory(memory_id)
                return None
            
            # Update access tracking
            self.connection.execute("""
                UPDATE memories 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE id = ?
            """, (time.time(), memory_id))
            self.connection.commit()
            
            return MemoryEntry(
                id=row['id'],
                memory_type=MemoryType(row['memory_type']),
                content=json.loads(row['content']),
                metadata=json.loads(row['metadata']),
                timestamp=row['timestamp'],
                expiry=row['expiry'],
                access_count=row['access_count'] + 1,
                last_accessed=time.time()
            )
    
    async def query_memories(self, memory_type: Optional[MemoryType] = None,
                            metadata_filters: Optional[Dict[str, Any]] = None,
                            limit: int = 10, offset: int = 0) -> List[MemoryEntry]:
        """
        Query memories with filters.
        
        Args:
            memory_type: Optional memory type filter
            metadata_filters: Optional metadata filters
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of memory entries
        """
        if not self.connection:
            await self.initialize()
        
        query = "SELECT * FROM memories WHERE 1=1"
        params = []
        
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type.value)
        
        # Add expiry check
        query += " AND (expiry IS NULL OR expiry > ?)"
        params.append(time.time())
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with self._lock:
            cursor = self.connection.execute(query, params)
            rows = cursor.fetchall()
        
        memories = []
        for row in rows:
            # Apply metadata filters
            if metadata_filters:
                metadata = json.loads(row['metadata'])
                if not self._matches_metadata_filters(metadata, metadata_filters):
                    continue
            
            memories.append(MemoryEntry(
                id=row['id'],
                memory_type=MemoryType(row['memory_type']),
                content=json.loads(row['content']),
                metadata=json.loads(row['metadata']),
                timestamp=row['timestamp'],
                expiry=row['expiry'],
                access_count=row['access_count'],
                last_accessed=row['last_accessed']
            ))
        
        return memories
    
    async def search_memories(self, search_query: str, memory_type: Optional[MemoryType] = None,
                             limit: int = 10) -> List[MemoryEntry]:
        """
        Full-text search memories.
        
        Args:
            search_query: Search query
            memory_type: Optional memory type filter
            limit: Maximum number of results
            
        Returns:
            List of matching memory entries
        """
        if not self.connection:
            await self.initialize()
        
        query = """
            SELECT m.* FROM memories m
            JOIN memory_search s ON m.id = s.id
            WHERE s.content MATCH ?
        """
        params = [search_query]
        
        if memory_type:
            query += " AND m.memory_type = ?"
            params.append(memory_type.value)
        
        # Add expiry check
        query += " AND (m.expiry IS NULL OR m.expiry > ?)"
        params.append(time.time())
        
        query += " ORDER BY m.timestamp DESC LIMIT ?"
        params.append(limit)
        
        async with self._lock:
            cursor = self.connection.execute(query, params)
            rows = cursor.fetchall()
        
        memories = []
        for row in rows:
            memories.append(MemoryEntry(
                id=row['id'],
                memory_type=MemoryType(row['memory_type']),
                content=json.loads(row['content']),
                metadata=json.loads(row['metadata']),
                timestamp=row['timestamp'],
                expiry=row['expiry'],
                access_count=row['access_count'],
                last_accessed=row['last_accessed']
            ))
        
        return memories
    
    async def update_memory(self, memory_id: str, content: Optional[Dict[str, Any]] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update existing memory entry"""
        if not self.connection:
            await self.initialize()
        
        # Get current memory
        current = await self.retrieve_memory(memory_id)
        if not current:
            return False
        
        # Update content and metadata
        new_content = content if content is not None else current.content
        new_metadata = metadata if metadata is not None else current.metadata
        
        content_json = json.dumps(new_content)
        metadata_json = json.dumps(new_metadata)
        
        async with self._lock:
            self.connection.execute("""
                UPDATE memories 
                SET content = ?, metadata = ?
                WHERE id = ?
            """, (content_json, metadata_json, memory_id))
            
            # Update search index
            search_content = json.dumps(new_content) + " " + json.dumps(new_metadata)
            self.connection.execute("""
                UPDATE memory_search 
                SET content = ?
                WHERE id = ?
            """, (search_content, memory_id))
            
            self.connection.commit()
        
        logger.debug(f"Updated memory: {memory_id}")
        return True
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry"""
        if not self.connection:
            await self.initialize()
        
        async with self._lock:
            cursor = self.connection.execute("""
                DELETE FROM memories WHERE id = ?
            """, (memory_id,))
            
            self.connection.execute("""
                DELETE FROM memory_search WHERE id = ?
            """, (memory_id,))
            
            self.connection.commit()
            deleted = cursor.rowcount > 0
        
        if deleted:
            logger.debug(f"Deleted memory: {memory_id}")
        
        return deleted
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory store statistics"""
        if not self.connection:
            await self.initialize()
        
        async with self._lock:
            # Total memories by type
            cursor = self.connection.execute("""
                SELECT memory_type, COUNT(*) as count
                FROM memories
                WHERE expiry IS NULL OR expiry > ?
                GROUP BY memory_type
            """, (time.time(),))
            
            by_type = {row['memory_type']: row['count'] for row in cursor.fetchall()}
            
            # Total count
            cursor = self.connection.execute("""
                SELECT COUNT(*) as total
                FROM memories
                WHERE expiry IS NULL OR expiry > ?
            """, (time.time(),))
            
            total = cursor.fetchone()['total']
            
            # Most accessed
            cursor = self.connection.execute("""
                SELECT memory_type, AVG(access_count) as avg_access
                FROM memories
                WHERE expiry IS NULL OR expiry > ?
                GROUP BY memory_type
            """, (time.time(),))
            
            access_stats = {row['memory_type']: row['avg_access'] for row in cursor.fetchall()}
        
        return {
            "total_memories": total,
            "by_type": by_type,
            "access_stats": access_stats,
            "database_path": self.db_path
        }
    
    async def cleanup_expired_memories(self) -> int:
        """Clean up expired memories"""
        if not self.connection:
            await self.initialize()
        
        current_time = time.time()
        
        async with self._lock:
            # Delete expired memories
            cursor = self.connection.execute("""
                DELETE FROM memories 
                WHERE expiry IS NOT NULL AND expiry <= ?
            """, (current_time,))
            
            self.connection.execute("""
                DELETE FROM memory_search 
                WHERE id NOT IN (SELECT id FROM memories)
            """, ())
            
            self.connection.commit()
            deleted_count = cursor.rowcount
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired memories")
        
        return deleted_count
    
    def _matches_metadata_filters(self, metadata: Dict[str, Any], 
                                 filters: Dict[str, Any]) -> bool:
        """Check if metadata matches filters"""
        for key, value in filters.items():
            if key not in metadata:
                return False
            
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            else:
                if metadata[key] != value:
                    return False
        
        return True
    
    async def _cleanup_if_needed(self):
        """Cleanup if enough time has passed"""
        current_time = time.time()
        
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self.cleanup_expired_memories()
            self.last_cleanup = current_time
    
    async def shutdown(self):
        """Shutdown the memory store"""
        await self.close()
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            async with self._lock:
                self.connection.close()
                self.connection = None
            logger.info("Memory store connection closed")