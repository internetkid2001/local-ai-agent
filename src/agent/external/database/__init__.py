"""
Database Connectivity

Database integration for SQL and NoSQL databases with query building and ORM capabilities.

Author: Claude Code
Date: 2025-07-13
Session: 2.3
"""

from .sql_client import SQLClient, SQLConfig, QueryResult
from .nosql_client import NoSQLClient, NoSQLConfig, DocumentResult
from .query_builder import QueryBuilder, Query, QueryType
from .database_manager import DatabaseManager, DatabaseType

__all__ = [
    'SQLClient',
    'SQLConfig', 
    'QueryResult',
    'NoSQLClient',
    'NoSQLConfig',
    'DocumentResult',
    'QueryBuilder',
    'Query',
    'QueryType',
    'DatabaseManager',
    'DatabaseType'
]