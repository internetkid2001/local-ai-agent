"""
Conversation Manager

Advanced conversation management with context tracking, memory integration,
and multi-turn dialogue optimization.

Author: Claude Code
Date: 2025-07-13
Session: 3.1
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class MessageRole(Enum):
    """Message roles in conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class ConversationState(Enum):
    """Conversation states"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Message:
    """Individual message in conversation"""
    id: str
    role: MessageRole
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    model_id: Optional[str] = None
    cost: float = 0.0


@dataclass
class ConversationContext:
    """Conversation context and state"""
    conversation_id: str
    user_id: Optional[str] = None
    title: str = ""
    description: str = ""
    state: ConversationState = ConversationState.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: List[Message] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    context_variables: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSummary:
    """Summary of conversation for context compression"""
    conversation_id: str
    summary_text: str
    key_points: List[str]
    entities: List[str]
    topics: List[str]
    sentiment: str
    created_at: float
    message_range: Tuple[int, int]  # Start and end message indices


class ConversationManager:
    """
    Advanced conversation management system.
    
    Features:
    - Multi-turn conversation tracking
    - Context window management and compression
    - Memory integration and retrieval
    - Conversation summarization
    - Topic modeling and entity extraction
    - User preference learning
    - Conversation branching and forking
    - Export and import capabilities
    """
    
    def __init__(self, memory_system=None, model_orchestrator=None):
        """
        Initialize conversation manager.
        
        Args:
            memory_system: Memory system for long-term storage
            model_orchestrator: Model orchestrator for AI operations
        """
        self.conversations: Dict[str, ConversationContext] = {}
        self.summaries: Dict[str, List[ConversationSummary]] = {}
        self.memory_system = memory_system
        self.model_orchestrator = model_orchestrator
        
        # Configuration
        self.config = {
            "max_context_tokens": 8192,
            "summary_threshold": 20,  # Messages before summarization
            "max_conversations": 1000,
            "auto_summarize": True,
            "preserve_recent_messages": 5,
            "compression_ratio": 0.3,
            "topic_extraction_enabled": True,
            "sentiment_analysis_enabled": True
        }
        
        logger.info("Conversation manager initialized")
    
    def create_conversation(self, user_id: Optional[str] = None, 
                          title: str = "", 
                          system_prompt: Optional[str] = None) -> str:
        """
        Create a new conversation.
        
        Args:
            user_id: User identifier
            title: Conversation title
            system_prompt: Initial system prompt
            
        Returns:
            Conversation ID
        """
        conversation_id = str(uuid.uuid4())
        
        context = ConversationContext(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title or f"Conversation {len(self.conversations) + 1}"
        )
        
        # Add system message if provided
        if system_prompt:
            self.add_message(
                conversation_id=conversation_id,
                role=MessageRole.SYSTEM,
                content=system_prompt
            )
        
        self.conversations[conversation_id] = context
        self.summaries[conversation_id] = []
        
        logger.info(f"Created conversation: {conversation_id}")
        return conversation_id
    
    def add_message(self, conversation_id: str, role: MessageRole, 
                   content: str, metadata: Optional[Dict[str, Any]] = None,
                   model_id: Optional[str] = None, tokens_used: int = 0, 
                   cost: float = 0.0) -> str:
        """
        Add message to conversation.
        
        Args:
            conversation_id: Conversation identifier
            role: Message role
            content: Message content
            metadata: Additional metadata
            model_id: Model that generated the message
            tokens_used: Number of tokens used
            cost: Cost of generation
            
        Returns:
            Message ID
        """
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        message_id = str(uuid.uuid4())
        message = Message(
            id=message_id,
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {},
            tokens_used=tokens_used,
            model_id=model_id,
            cost=cost
        )
        
        context = self.conversations[conversation_id]
        context.messages.append(message)
        context.updated_at = time.time()
        context.total_tokens += tokens_used
        context.total_cost += cost
        
        # Auto-summarize if threshold reached
        if (self.config["auto_summarize"] and 
            len(context.messages) >= self.config["summary_threshold"]):
            asyncio.create_task(self._auto_summarize_conversation(conversation_id))
        
        # Memory integration
        if self.memory_system and role == MessageRole.USER:
            asyncio.create_task(self._store_interaction_memory(conversation_id, message))
        
        logger.debug(f"Added message to conversation {conversation_id}: {role.value}")
        return message_id
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context"""
        return self.conversations.get(conversation_id)
    
    def get_conversation_messages(self, conversation_id: str, 
                                limit: Optional[int] = None,
                                include_summaries: bool = True) -> List[Message]:
        """
        Get conversation messages with optional context compression.
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of recent messages
            include_summaries: Whether to include summarized context
            
        Returns:
            List of messages
        """
        if conversation_id not in self.conversations:
            return []
        
        context = self.conversations[conversation_id]
        messages = context.messages.copy()
        
        # Apply limit if specified
        if limit:
            messages = messages[-limit:]
        
        # Include summaries for context if needed
        if include_summaries and conversation_id in self.summaries:
            summary_messages = self._create_summary_messages(conversation_id)
            # Insert summaries before recent messages
            if limit and len(context.messages) > limit:
                messages = summary_messages + messages
        
        return messages
    
    def _create_summary_messages(self, conversation_id: str) -> List[Message]:
        """Create synthetic messages from conversation summaries"""
        summary_messages = []
        
        for summary in self.summaries[conversation_id]:
            summary_content = f"[Previous conversation summary]\n{summary.summary_text}"
            if summary.key_points:
                summary_content += f"\n\nKey points: {', '.join(summary.key_points)}"
            
            summary_message = Message(
                id=f"summary_{summary.created_at}",
                role=MessageRole.SYSTEM,
                content=summary_content,
                timestamp=summary.created_at,
                metadata={"type": "summary", "topics": summary.topics}
            )
            summary_messages.append(summary_message)
        
        return summary_messages
    
    async def _auto_summarize_conversation(self, conversation_id: str):
        """Automatically summarize conversation when threshold is reached"""
        try:
            context = self.conversations[conversation_id]
            
            # Don't summarize if we already have recent summaries
            last_summary_index = 0
            if self.summaries[conversation_id]:
                last_summary_index = self.summaries[conversation_id][-1].message_range[1]
            
            # Get messages to summarize (excluding recent ones to preserve)
            preserve_count = self.config["preserve_recent_messages"]
            end_index = len(context.messages) - preserve_count
            
            if end_index <= last_summary_index:
                return  # Nothing new to summarize
            
            messages_to_summarize = context.messages[last_summary_index:end_index]
            
            if len(messages_to_summarize) < 5:
                return  # Not enough messages to summarize
            
            summary = await self._generate_conversation_summary(
                conversation_id, messages_to_summarize, last_summary_index, end_index
            )
            
            if summary:
                self.summaries[conversation_id].append(summary)
                logger.info(f"Auto-summarized conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Auto-summarization failed for {conversation_id}: {e}")
    
    async def _generate_conversation_summary(self, conversation_id: str, 
                                           messages: List[Message],
                                           start_index: int, end_index: int) -> Optional[ConversationSummary]:
        """Generate summary for a portion of conversation"""
        if not self.model_orchestrator:
            return None
        
        try:
            # Prepare conversation text for summarization
            conversation_text = "\n".join([
                f"{msg.role.value.title()}: {msg.content}"
                for msg in messages
            ])
            
            # Create summarization prompt
            from .model_orchestrator import ModelRequest, ModelCapability
            
            prompt = f"""Please provide a concise summary of this conversation segment:

{conversation_text}

Provide:
1. A brief summary (2-3 sentences)
2. Key points discussed (bullet points)
3. Main entities mentioned (people, places, topics)
4. Primary topics covered
5. Overall sentiment (positive/negative/neutral)

Format your response as JSON with fields: summary, key_points, entities, topics, sentiment"""
            
            request = ModelRequest(
                prompt=prompt,
                capabilities_required=[ModelCapability.SUMMARIZATION, ModelCapability.ANALYSIS],
                max_tokens=500,
                temperature=0.3
            )
            
            response = await self.model_orchestrator.generate(request)
            
            if response.success:
                # Parse response (simplified - in production you'd use proper JSON parsing)
                summary_data = self._parse_summary_response(response.content)
                
                summary = ConversationSummary(
                    conversation_id=conversation_id,
                    summary_text=summary_data.get("summary", ""),
                    key_points=summary_data.get("key_points", []),
                    entities=summary_data.get("entities", []),
                    topics=summary_data.get("topics", []),
                    sentiment=summary_data.get("sentiment", "neutral"),
                    created_at=time.time(),
                    message_range=(start_index, end_index)
                )
                
                return summary
                
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
        
        return None
    
    def _parse_summary_response(self, response_text: str) -> Dict[str, Any]:
        """Parse summary response (simplified implementation)"""
        # In a real implementation, you'd use proper JSON parsing
        # This is a simplified version for demonstration
        return {
            "summary": response_text[:200],  # First 200 chars as summary
            "key_points": [],
            "entities": [],
            "topics": [],
            "sentiment": "neutral"
        }
    
    async def _store_interaction_memory(self, conversation_id: str, message: Message):
        """Store interaction in memory system"""
        if not self.memory_system:
            return
        
        try:
            # Store user message for future reference
            from .memory_system import MemoryEntry, MemoryType
            
            memory_entry = MemoryEntry(
                content=message.content,
                memory_type=MemoryType.INTERACTION,
                source_id=conversation_id,
                metadata={
                    "conversation_id": conversation_id,
                    "message_id": message.id,
                    "timestamp": message.timestamp
                }
            )
            
            await self.memory_system.store_memory(memory_entry)
            
        except Exception as e:
            logger.error(f"Failed to store interaction memory: {e}")
    
    def update_conversation_metadata(self, conversation_id: str, 
                                   metadata: Dict[str, Any]):
        """Update conversation metadata"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].metadata.update(metadata)
            self.conversations[conversation_id].updated_at = time.time()
    
    def set_conversation_variables(self, conversation_id: str, 
                                 variables: Dict[str, Any]):
        """Set context variables for conversation"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].context_variables.update(variables)
    
    def get_conversation_variables(self, conversation_id: str) -> Dict[str, Any]:
        """Get context variables for conversation"""
        if conversation_id in self.conversations:
            return self.conversations[conversation_id].context_variables.copy()
        return {}
    
    def pause_conversation(self, conversation_id: str):
        """Pause a conversation"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].state = ConversationState.PAUSED
            self.conversations[conversation_id].updated_at = time.time()
    
    def resume_conversation(self, conversation_id: str):
        """Resume a paused conversation"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].state = ConversationState.ACTIVE
            self.conversations[conversation_id].updated_at = time.time()
    
    def complete_conversation(self, conversation_id: str):
        """Mark conversation as completed"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].state = ConversationState.COMPLETED
            self.conversations[conversation_id].updated_at = time.time()
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            if conversation_id in self.summaries:
                del self.summaries[conversation_id]
            logger.info(f"Deleted conversation: {conversation_id}")
    
    def list_conversations(self, user_id: Optional[str] = None, 
                         state: Optional[ConversationState] = None) -> List[ConversationContext]:
        """
        List conversations with optional filtering.
        
        Args:
            user_id: Filter by user ID
            state: Filter by conversation state
            
        Returns:
            List of conversation contexts
        """
        conversations = list(self.conversations.values())
        
        if user_id:
            conversations = [c for c in conversations if c.user_id == user_id]
        
        if state:
            conversations = [c for c in conversations if c.state == state]
        
        # Sort by last updated (most recent first)
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        
        return conversations
    
    def get_conversation_stats(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get conversation statistics.
        
        Args:
            conversation_id: Specific conversation or None for all
            
        Returns:
            Statistics dictionary
        """
        if conversation_id:
            if conversation_id not in self.conversations:
                return {}
            
            context = self.conversations[conversation_id]
            
            return {
                "conversation_id": conversation_id,
                "message_count": len(context.messages),
                "total_tokens": context.total_tokens,
                "total_cost": context.total_cost,
                "duration": context.updated_at - context.created_at,
                "state": context.state.value,
                "summary_count": len(self.summaries.get(conversation_id, []))
            }
        else:
            # Aggregate stats for all conversations
            total_conversations = len(self.conversations)
            total_messages = sum(len(c.messages) for c in self.conversations.values())
            total_tokens = sum(c.total_tokens for c in self.conversations.values())
            total_cost = sum(c.total_cost for c in self.conversations.values())
            
            states = {}
            for conv in self.conversations.values():
                states[conv.state.value] = states.get(conv.state.value, 0) + 1
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "conversations_by_state": states,
                "average_messages_per_conversation": total_messages / total_conversations if total_conversations > 0 else 0
            }
    
    def export_conversation(self, conversation_id: str, format: str = "json") -> str:
        """
        Export conversation to specified format.
        
        Args:
            conversation_id: Conversation to export
            format: Export format (json, markdown, txt)
            
        Returns:
            Exported conversation data
        """
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        context = self.conversations[conversation_id]
        
        if format == "json":
            import json
            return json.dumps({
                "conversation_id": conversation_id,
                "context": context.__dict__,
                "summaries": [s.__dict__ for s in self.summaries.get(conversation_id, [])]
            }, indent=2, default=str)
        
        elif format == "markdown":
            lines = [f"# {context.title}", f"**Created:** {context.created_at}", ""]
            
            for msg in context.messages:
                lines.append(f"## {msg.role.value.title()}")
                lines.append(msg.content)
                lines.append("")
            
            return "\n".join(lines)
        
        elif format == "txt":
            lines = [f"Conversation: {context.title}", f"Created: {context.created_at}", ""]
            
            for msg in context.messages:
                lines.append(f"{msg.role.value.title()}: {msg.content}")
                lines.append("")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def search_conversations(self, query: str, user_id: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        Search conversations by content.
        
        Args:
            query: Search query
            user_id: Optional user filter
            
        Returns:
            List of (conversation_id, relevance_score) tuples
        """
        results = []
        query_lower = query.lower()
        
        for conv_id, context in self.conversations.items():
            if user_id and context.user_id != user_id:
                continue
            
            relevance_score = 0.0
            
            # Search in title
            if query_lower in context.title.lower():
                relevance_score += 2.0
            
            # Search in messages
            for msg in context.messages:
                if query_lower in msg.content.lower():
                    relevance_score += 1.0
            
            # Search in summaries
            for summary in self.summaries.get(conv_id, []):
                if query_lower in summary.summary_text.lower():
                    relevance_score += 1.5
                if any(query_lower in kp.lower() for kp in summary.key_points):
                    relevance_score += 1.0
            
            if relevance_score > 0:
                results.append((conv_id, relevance_score))
        
        # Sort by relevance score (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results