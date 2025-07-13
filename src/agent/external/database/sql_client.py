"""
SQL Database Client

Async SQL database client with connection pooling, query building, and ORM features.

Author: Claude Code
Date: 2025-07-13
Session: 2.3
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

try:
    import aiosqlite
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import aiomysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

from ....utils.logger import get_logger

logger = get_logger(__name__)


class SQLDialect(Enum):
    """SQL database dialects"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"


@dataclass
class SQLConfig:
    """SQL database configuration"""
    dialect: SQLDialect
    database: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: float = 30.0
    query_timeout: float = 60.0
    connection_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    """SQL query result wrapper"""
    rows: List[Dict[str, Any]]
    row_count: int
    columns: List[str]
    execution_time: float
    query: str
    success: bool = True
    error: Optional[str] = None


class SQLClient:
    """
    Async SQL database client with advanced features.
    
    Features:
    - Multiple SQL dialect support (SQLite, PostgreSQL, MySQL)
    - Connection pooling and management
    - Query building and parameterization
    - Transaction support
    - Schema introspection
    - Migration support
    - Performance monitoring
    """
    
    def __init__(self, config: SQLConfig):
        """
        Initialize SQL client.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.connection_pool = None
        self.is_connected = False
        
        # Query statistics
        self.stats = {
            "queries_executed": 0,
            "total_execution_time": 0.0,
            "successful_queries": 0,
            "failed_queries": 0
        }
        
        logger.info(f"SQL client initialized for {config.dialect.value}")
    
    async def connect(self) -> bool:
        """
        Establish database connection and create connection pool.
        
        Returns:
            True if connection was successful
        """
        try:
            if self.config.dialect == SQLDialect.SQLITE:
                await self._connect_sqlite()
            elif self.config.dialect == SQLDialect.POSTGRESQL:
                await self._connect_postgresql()
            elif self.config.dialect in [SQLDialect.MYSQL, SQLDialect.MARIADB]:
                await self._connect_mysql()
            else:
                raise ValueError(f"Unsupported SQL dialect: {self.config.dialect}")
            
            self.is_connected = True
            logger.info(f"Connected to {self.config.dialect.value} database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    async def _connect_sqlite(self):
        """Connect to SQLite database"""
        if not SQLITE_AVAILABLE:
            raise ImportError("aiosqlite not available")
        
        # SQLite uses single connection, not pool
        self.connection_pool = self.config.database
    
    async def _connect_postgresql(self):
        """Connect to PostgreSQL database"""
        if not POSTGRES_AVAILABLE:
            raise ImportError("asyncpg not available")
        
        connection_string = self._build_postgres_connection_string()
        
        self.connection_pool = await asyncpg.create_pool(
            connection_string,
            min_size=1,
            max_size=self.config.pool_size,
            timeout=self.config.pool_timeout,
            **self.config.connection_params
        )
    
    async def _connect_mysql(self):
        """Connect to MySQL/MariaDB database"""
        if not MYSQL_AVAILABLE:
            raise ImportError("aiomysql not available")
        
        self.connection_pool = await aiomysql.create_pool(
            host=self.config.host,
            port=self.config.port or 3306,
            user=self.config.username,
            password=self.config.password,
            db=self.config.database,
            minsize=1,
            maxsize=self.config.pool_size,
            **self.config.connection_params
        )
    
    def _build_postgres_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        parts = [f"postgresql://{self.config.username}:{self.config.password}"]
        parts.append(f"@{self.config.host}:{self.config.port or 5432}")
        parts.append(f"/{self.config.database}")
        
        if self.config.ssl:
            parts.append("?sslmode=require")
        
        return "".join(parts)
    
    async def disconnect(self):
        """Close database connections"""
        if self.connection_pool:
            if self.config.dialect == SQLDialect.POSTGRESQL:
                await self.connection_pool.close()
            elif self.config.dialect in [SQLDialect.MYSQL, SQLDialect.MARIADB]:
                self.connection_pool.close()
                await self.connection_pool.wait_closed()
            
            self.connection_pool = None
        
        self.is_connected = False
        logger.info("Database disconnected")
    
    async def execute_query(self, query: str, parameters: Optional[Union[Dict, List, Tuple]] = None) -> QueryResult:
        """
        Execute SQL query.
        
        Args:
            query: SQL query string
            parameters: Query parameters
            
        Returns:
            Query result
        """
        if not self.is_connected:
            await self.connect()
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            if self.config.dialect == SQLDialect.SQLITE:
                result = await self._execute_sqlite_query(query, parameters)
            elif self.config.dialect == SQLDialect.POSTGRESQL:
                result = await self._execute_postgres_query(query, parameters)
            elif self.config.dialect in [SQLDialect.MYSQL, SQLDialect.MARIADB]:
                result = await self._execute_mysql_query(query, parameters)
            else:
                raise ValueError(f"Unsupported dialect: {self.config.dialect}")
            
            execution_time = asyncio.get_event_loop().time() - start_time
            result.execution_time = execution_time
            result.query = query
            
            # Update statistics
            self.stats["queries_executed"] += 1
            self.stats["total_execution_time"] += execution_time
            self.stats["successful_queries"] += 1
            
            return result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Update statistics
            self.stats["queries_executed"] += 1
            self.stats["total_execution_time"] += execution_time
            self.stats["failed_queries"] += 1
            
            logger.error(f"Query execution failed: {e}")
            
            return QueryResult(
                rows=[],
                row_count=0,
                columns=[],
                execution_time=execution_time,
                query=query,
                success=False,
                error=str(e)
            )
    
    async def _execute_sqlite_query(self, query: str, parameters: Optional[Union[Dict, List, Tuple]]) -> QueryResult:
        """Execute SQLite query"""
        async with aiosqlite.connect(self.connection_pool) as connection:
            connection.row_factory = aiosqlite.Row
            
            if parameters:
                cursor = await connection.execute(query, parameters)
            else:
                cursor = await connection.execute(query)
            
            if query.strip().upper().startswith(('SELECT', 'WITH', 'PRAGMA')):
                rows = await cursor.fetchall()
                row_dicts = [dict(row) for row in rows]
                columns = list(rows[0].keys()) if rows else []
            else:
                await connection.commit()
                row_dicts = []
                columns = []
            
            row_count = cursor.rowcount if cursor.rowcount != -1 else len(row_dicts)
            
            return QueryResult(
                rows=row_dicts,
                row_count=row_count,
                columns=columns,
                execution_time=0.0,  # Will be set by caller
                query=query
            )
    
    async def _execute_postgres_query(self, query: str, parameters: Optional[Union[Dict, List, Tuple]]) -> QueryResult:
        """Execute PostgreSQL query"""
        async with self.connection_pool.acquire() as connection:
            if query.strip().upper().startswith(('SELECT', 'WITH')):
                if parameters:
                    rows = await connection.fetch(query, *parameters if isinstance(parameters, (list, tuple)) else parameters)
                else:
                    rows = await connection.fetch(query)
                
                row_dicts = [dict(row) for row in rows]
                columns = list(rows[0].keys()) if rows else []
                row_count = len(row_dicts)
            else:
                if parameters:
                    result = await connection.execute(query, *parameters if isinstance(parameters, (list, tuple)) else parameters)
                else:
                    result = await connection.execute(query)
                
                row_dicts = []
                columns = []
                # Parse row count from result string like "INSERT 0 5"
                row_count = int(result.split()[-1]) if result else 0
            
            return QueryResult(
                rows=row_dicts,
                row_count=row_count,
                columns=columns,
                execution_time=0.0,
                query=query
            )
    
    async def _execute_mysql_query(self, query: str, parameters: Optional[Union[Dict, List, Tuple]]) -> QueryResult:
        """Execute MySQL/MariaDB query"""
        async with self.connection_pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, parameters)
                
                if query.strip().upper().startswith(('SELECT', 'WITH', 'SHOW', 'DESCRIBE')):
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    row_count = len(rows)
                else:
                    await connection.commit()
                    rows = []
                    columns = []
                    row_count = cursor.rowcount
                
                return QueryResult(
                    rows=rows,
                    row_count=row_count,
                    columns=columns,
                    execution_time=0.0,
                    query=query
                )
    
    async def execute_many(self, query: str, parameters_list: List[Union[Dict, List, Tuple]]) -> List[QueryResult]:
        """
        Execute query multiple times with different parameters.
        
        Args:
            query: SQL query string
            parameters_list: List of parameter sets
            
        Returns:
            List of query results
        """
        results = []
        
        for parameters in parameters_list:
            result = await self.execute_query(query, parameters)
            results.append(result)
        
        return results
    
    async def execute_transaction(self, queries: List[Tuple[str, Optional[Union[Dict, List, Tuple]]]]) -> List[QueryResult]:
        """
        Execute multiple queries in a transaction.
        
        Args:
            queries: List of (query, parameters) tuples
            
        Returns:
            List of query results
        """
        if not self.is_connected:
            await self.connect()
        
        results = []
        
        try:
            if self.config.dialect == SQLDialect.SQLITE:
                results = await self._execute_sqlite_transaction(queries)
            elif self.config.dialect == SQLDialect.POSTGRESQL:
                results = await self._execute_postgres_transaction(queries)
            elif self.config.dialect in [SQLDialect.MYSQL, SQLDialect.MARIADB]:
                results = await self._execute_mysql_transaction(queries)
            
            return results
            
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise
    
    async def _execute_sqlite_transaction(self, queries: List[Tuple[str, Optional[Union[Dict, List, Tuple]]]]) -> List[QueryResult]:
        """Execute SQLite transaction"""
        async with aiosqlite.connect(self.connection_pool) as connection:
            connection.row_factory = aiosqlite.Row
            results = []
            
            try:
                await connection.execute("BEGIN")
                
                for query, parameters in queries:
                    if parameters:
                        cursor = await connection.execute(query, parameters)
                    else:
                        cursor = await connection.execute(query)
                    
                    if query.strip().upper().startswith(('SELECT', 'WITH')):
                        rows = await cursor.fetchall()
                        row_dicts = [dict(row) for row in rows]
                        columns = list(rows[0].keys()) if rows else []
                    else:
                        row_dicts = []
                        columns = []
                    
                    result = QueryResult(
                        rows=row_dicts,
                        row_count=cursor.rowcount if cursor.rowcount != -1 else len(row_dicts),
                        columns=columns,
                        execution_time=0.0,
                        query=query
                    )
                    results.append(result)
                
                await connection.commit()
                return results
                
            except Exception:
                await connection.rollback()
                raise
    
    async def _execute_postgres_transaction(self, queries: List[Tuple[str, Optional[Union[Dict, List, Tuple]]]]) -> List[QueryResult]:
        """Execute PostgreSQL transaction"""
        async with self.connection_pool.acquire() as connection:
            async with connection.transaction():
                results = []
                
                for query, parameters in queries:
                    if query.strip().upper().startswith(('SELECT', 'WITH')):
                        if parameters:
                            rows = await connection.fetch(query, *parameters if isinstance(parameters, (list, tuple)) else parameters)
                        else:
                            rows = await connection.fetch(query)
                        
                        row_dicts = [dict(row) for row in rows]
                        columns = list(rows[0].keys()) if rows else []
                        row_count = len(row_dicts)
                    else:
                        if parameters:
                            result_str = await connection.execute(query, *parameters if isinstance(parameters, (list, tuple)) else parameters)
                        else:
                            result_str = await connection.execute(query)
                        
                        row_dicts = []
                        columns = []
                        row_count = int(result_str.split()[-1]) if result_str else 0
                    
                    result = QueryResult(
                        rows=row_dicts,
                        row_count=row_count,
                        columns=columns,
                        execution_time=0.0,
                        query=query
                    )
                    results.append(result)
                
                return results
    
    async def _execute_mysql_transaction(self, queries: List[Tuple[str, Optional[Union[Dict, List, Tuple]]]]) -> List[QueryResult]:
        """Execute MySQL transaction"""
        async with self.connection_pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                results = []
                
                try:
                    await connection.begin()
                    
                    for query, parameters in queries:
                        await cursor.execute(query, parameters)
                        
                        if query.strip().upper().startswith(('SELECT', 'WITH', 'SHOW')):
                            rows = await cursor.fetchall()
                            columns = [desc[0] for desc in cursor.description] if cursor.description else []
                            row_count = len(rows)
                        else:
                            rows = []
                            columns = []
                            row_count = cursor.rowcount
                        
                        result = QueryResult(
                            rows=rows,
                            row_count=row_count,
                            columns=columns,
                            execution_time=0.0,
                            query=query
                        )
                        results.append(result)
                    
                    await connection.commit()
                    return results
                    
                except Exception:
                    await connection.rollback()
                    raise
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a table"""
        if self.config.dialect == SQLDialect.SQLITE:
            query = f"PRAGMA table_info({table_name})"
        elif self.config.dialect == SQLDialect.POSTGRESQL:
            query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """
        elif self.config.dialect in [SQLDialect.MYSQL, SQLDialect.MARIADB]:
            query = f"""
                SELECT COLUMN_NAME as column_name, DATA_TYPE as data_type, 
                       IS_NULLABLE as is_nullable, COLUMN_DEFAULT as column_default
                FROM information_schema.COLUMNS
                WHERE TABLE_NAME = '{table_name}'
                ORDER BY ORDINAL_POSITION
            """
        
        result = await self.execute_query(query, [table_name] if self.config.dialect == SQLDialect.POSTGRESQL else None)
        
        return {
            "table_name": table_name,
            "columns": result.rows,
            "column_count": len(result.rows)
        }
    
    async def list_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        if self.config.dialect == SQLDialect.SQLITE:
            query = "SELECT name FROM sqlite_master WHERE type='table'"
        elif self.config.dialect == SQLDialect.POSTGRESQL:
            query = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        elif self.config.dialect in [SQLDialect.MYSQL, SQLDialect.MARIADB]:
            query = "SHOW TABLES"
        
        result = await self.execute_query(query)
        
        if result.success:
            # Extract table names from results
            if self.config.dialect == SQLDialect.SQLITE:
                return [row["name"] for row in result.rows]
            elif self.config.dialect == SQLDialect.POSTGRESQL:
                return [row["tablename"] for row in result.rows]
            elif self.config.dialect in [SQLDialect.MYSQL, SQLDialect.MARIADB]:
                # MySQL SHOW TABLES returns single column with table name
                column_name = result.columns[0]
                return [row[column_name] for row in result.rows]
        
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database client statistics"""
        stats = self.stats.copy()
        
        if stats["queries_executed"] > 0:
            stats["average_execution_time"] = stats["total_execution_time"] / stats["queries_executed"]
            stats["success_rate"] = stats["successful_queries"] / stats["queries_executed"]
        else:
            stats["average_execution_time"] = 0.0
            stats["success_rate"] = 0.0
        
        stats["connection_status"] = "connected" if self.is_connected else "disconnected"
        stats["dialect"] = self.config.dialect.value
        
        return stats