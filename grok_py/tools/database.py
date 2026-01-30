"""Database tool for interacting with SQLite, PostgreSQL, and MySQL databases."""

import sqlite3
import json
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager

try:
    import psycopg2
    from psycopg2 import pool
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

try:
    import pymysql
    from pymysql import pool
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

from .base import SyncTool, ToolCategory, ToolResult


class DatabaseTool(SyncTool):
    """Tool for database operations on SQLite, PostgreSQL, and MySQL."""

    def __init__(self):
        super().__init__(
            name="database",
            description="Database operations for SQLite, PostgreSQL, and MySQL (query, schema inspection, table operations)",
            category=ToolCategory.UTILITY
        )
        self.connections = {}  # Store active connections by db_type:db_name
        self.pools = {}  # Connection pools for PostgreSQL and MySQL

    def execute_sync(
        self,
        operation: str,
        db_type: str,
        db_name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        sql: Optional[str] = None,
        params: Optional[List[Any]] = None,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
        output_format: str = "table"
    ) -> ToolResult:
        """Execute database operation.

        Args:
            operation: Operation to perform (connect, disconnect, query, execute, list_tables, describe_table, create_table, drop_table, begin_transaction, commit, rollback)
            db_type: Database type (sqlite, postgresql, mysql)
            db_name: Database name (required for all operations)
            host: Host for PostgreSQL/MySQL
            port: Port for PostgreSQL/MySQL
            user: Username for PostgreSQL/MySQL
            password: Password for PostgreSQL/MySQL
            sql: SQL query/statement
            params: Parameters for parameterized queries
            table_name: Table name for schema operations
            schema: Schema name (for PostgreSQL)
            output_format: Output format (table, json, csv)

        Returns:
            ToolResult with operation result
        """
        try:
            # Validate db_type
            valid_types = ['sqlite', 'postgresql', 'mysql']
            if db_type not in valid_types:
                return ToolResult(
                    success=False,
                    error=f"Invalid db_type: {db_type}. Valid types: {', '.join(valid_types)}"
                )

            # Check dependencies
            if db_type == 'postgresql' and not HAS_POSTGRES:
                return ToolResult(
                    success=False,
                    error="psycopg2 not installed. Install with: pip install psycopg2-binary"
                )
            if db_type == 'mysql' and not HAS_MYSQL:
                return ToolResult(
                    success=False,
                    error="PyMySQL not installed. Install with: pip install PyMySQL"
                )

            # Validate operation
            valid_operations = [
                'connect', 'disconnect', 'query', 'execute', 'list_tables',
                'describe_table', 'create_table', 'drop_table',
                'begin_transaction', 'commit', 'rollback'
            ]
            if operation not in valid_operations:
                return ToolResult(
                    success=False,
                    error=f"Invalid operation: {operation}. Valid operations: {', '.join(valid_operations)}"
                )

            # Handle operations
            if operation == 'connect':
                return self._connect(db_type, db_name, host, port, user, password)
            elif operation == 'disconnect':
                return self._disconnect(db_type, db_name)
            elif operation in ['query', 'execute']:
                return self._execute_sql(operation, db_type, db_name, sql, params, output_format)
            elif operation == 'list_tables':
                return self._list_tables(db_type, db_name, schema)
            elif operation == 'describe_table':
                return self._describe_table(db_type, db_name, table_name, schema, output_format)
            elif operation in ['create_table', 'drop_table']:
                return self._table_operation(operation, db_type, db_name, sql, params)
            elif operation in ['begin_transaction', 'commit', 'rollback']:
                return self._transaction_operation(operation, db_type, db_name)
            else:
                return ToolResult(success=False, error=f"Operation not implemented: {operation}")

        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_connection_key(self, db_type: str, db_name: str) -> str:
        """Get connection key for storing connections."""
        return f"{db_type}:{db_name}"

    def _connect(self, db_type: str, db_name: str, host: str = None, port: int = None,
                 user: str = None, password: str = None) -> ToolResult:
        """Establish database connection."""
        if not db_name:
            return ToolResult(success=False, error="db_name is required for connect operation")

        conn_key = self._get_connection_key(db_type, db_name)

        try:
            if db_type == 'sqlite':
                conn = sqlite3.connect(db_name)
                conn.row_factory = sqlite3.Row  # Enable column access by name
            elif db_type == 'postgresql':
                if not all([host, port, user, password]):
                    return ToolResult(success=False, error="host, port, user, password required for PostgreSQL")
                # Use connection pool for PostgreSQL
                if conn_key not in self.pools:
                    self.pools[conn_key] = pool.SimpleConnectionPool(
                        1, 10,
                        host=host, port=port, user=user, password=password, database=db_name
                    )
                conn = self.pools[conn_key].getconn()
            elif db_type == 'mysql':
                if not all([host, port, user, password]):
                    return ToolResult(success=False, error="host, port, user, password required for MySQL")
                # Use connection pool for MySQL
                if conn_key not in self.pools:
                    self.pools[conn_key] = pool.ConnectionPool(
                        host=host, port=port, user=user, password=password, database=db_name,
                        autocommit=False
                    )
                conn = self.pools[conn_key].get_connection()

            self.connections[conn_key] = conn
            return ToolResult(success=True, data=f"Connected to {db_type} database: {db_name}")

        except Exception as e:
            return ToolResult(success=False, error=f"Failed to connect: {e}")

    def _disconnect(self, db_type: str, db_name: str) -> ToolResult:
        """Close database connection."""
        if not db_name:
            return ToolResult(success=False, error="db_name is required for disconnect operation")

        conn_key = self._get_connection_key(db_type, db_name)

        try:
            if conn_key in self.connections:
                conn = self.connections[conn_key]
                if db_type == 'postgresql' and conn_key in self.pools:
                    self.pools[conn_key].putconn(conn)
                elif db_type == 'mysql' and conn_key in self.pools:
                    conn.close()
                else:
                    conn.close()
                del self.connections[conn_key]
                return ToolResult(success=True, data=f"Disconnected from {db_type} database: {db_name}")
            else:
                return ToolResult(success=False, error=f"No active connection for {conn_key}")

        except Exception as e:
            return ToolResult(success=False, error=f"Failed to disconnect: {e}")

    @contextmanager
    def _get_connection(self, db_type: str, db_name: str):
        """Context manager for getting database connection."""
        conn_key = self._get_connection_key(db_type, db_name)
        if conn_key not in self.connections:
            raise Exception(f"No active connection for {conn_key}")

        conn = self.connections[conn_key]
        try:
            yield conn
        finally:
            pass  # Connection remains open

    def _execute_sql(self, operation: str, db_type: str, db_name: str, sql: str,
                     params: List[Any] = None, output_format: str = "table") -> ToolResult:
        """Execute SQL query or statement."""
        if not sql:
            return ToolResult(success=False, error="sql is required")

        try:
            with self._get_connection(db_type, db_name) as conn:
                cursor = conn.cursor()

                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                if operation == 'query':
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    cursor.close()

                    # Format results
                    if output_format == 'json':
                        result = [dict(zip(columns, row)) for row in rows] if columns else rows
                        return ToolResult(success=True, data=json.dumps(result, indent=2, default=str))
                    elif output_format == 'csv':
                        import csv
                        import io
                        output = io.StringIO()
                        writer = csv.writer(output)
                        writer.writerow(columns)
                        writer.writerows(rows)
                        return ToolResult(success=True, data=output.getvalue())
                    else:  # table format
                        return ToolResult(success=True, data=self._format_table(columns, rows))
                else:  # execute
                    conn.commit()
                    cursor.close()
                    return ToolResult(success=True, data=f"Executed successfully. Rows affected: {cursor.rowcount}")

        except Exception as e:
            return ToolResult(success=False, error=f"SQL execution failed: {e}")

    def _list_tables(self, db_type: str, db_name: str, schema: str = None) -> ToolResult:
        """List all tables in the database."""
        try:
            with self._get_connection(db_type, db_name) as conn:
                cursor = conn.cursor()

                if db_type == 'sqlite':
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                elif db_type == 'postgresql':
                    schema_clause = f"AND schemaname = '{schema}'" if schema else "AND schemaname NOT IN ('pg_catalog', 'information_schema')"
                    cursor.execute(f"SELECT tablename FROM pg_tables WHERE schemaname <> 'pg_catalog' AND schemaname <> 'information_schema' {schema_clause}")
                elif db_type == 'mysql':
                    cursor.execute("SHOW TABLES")

                tables = [row[0] for row in cursor.fetchall()]
                cursor.close()

                return ToolResult(success=True, data="\n".join(tables))

        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list tables: {e}")

    def _describe_table(self, db_type: str, db_name: str, table_name: str,
                       schema: str = None, output_format: str = "table") -> ToolResult:
        """Describe table structure."""
        if not table_name:
            return ToolResult(success=False, error="table_name is required")

        try:
            with self._get_connection(db_type, db_name) as conn:
                cursor = conn.cursor()

                if db_type == 'sqlite':
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = ['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk']
                elif db_type == 'postgresql':
                    schema_prefix = f"{schema}." if schema else ""
                    cursor.execute(f"SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = '{table_name}'" + (f" AND table_schema = '{schema}'" if schema else ""))
                    columns = ['column_name', 'data_type', 'is_nullable', 'column_default']
                elif db_type == 'mysql':
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = ['Field', 'Type', 'Null', 'Key', 'Default', 'Extra']

                rows = cursor.fetchall()
                cursor.close()

                if output_format == 'json':
                    result = [dict(zip(columns, row)) for row in rows]
                    return ToolResult(success=True, data=json.dumps(result, indent=2, default=str))
                else:
                    return ToolResult(success=True, data=self._format_table(columns, rows))

        except Exception as e:
            return ToolResult(success=False, error=f"Failed to describe table: {e}")

    def _table_operation(self, operation: str, db_type: str, db_name: str,
                        sql: str = None, params: List[Any] = None) -> ToolResult:
        """Perform table operations (create, drop, alter)."""
        if not sql:
            return ToolResult(success=False, error="sql is required for table operations")

        try:
            with self._get_connection(db_type, db_name) as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                conn.commit()
                cursor.close()
                return ToolResult(success=True, data=f"Table operation '{operation}' completed successfully")

        except Exception as e:
            return ToolResult(success=False, error=f"Table operation failed: {e}")

    def _transaction_operation(self, operation: str, db_type: str, db_name: str) -> ToolResult:
        """Handle transaction operations."""
        try:
            with self._get_connection(db_type, db_name) as conn:
                if operation == 'begin_transaction':
                    conn.autocommit = False
                    return ToolResult(success=True, data="Transaction started")
                elif operation == 'commit':
                    conn.commit()
                    conn.autocommit = True
                    return ToolResult(success=True, data="Transaction committed")
                elif operation == 'rollback':
                    conn.rollback()
                    conn.autocommit = True
                    return ToolResult(success=True, data="Transaction rolled back")

        except Exception as e:
            return ToolResult(success=False, error=f"Transaction operation failed: {e}")

    def _format_table(self, columns: List[str], rows: List[tuple]) -> str:
        """Format results as a simple table."""
        if not rows:
            return "No results"

        # Calculate column widths
        widths = []
        for i, col in enumerate(columns):
            width = len(str(col))
            for row in rows:
                width = max(width, len(str(row[i])))
            widths.append(width)

        # Create header
        header = " | ".join(str(col).ljust(widths[i]) for i, col in enumerate(columns))
        separator = "-+-".join("-" * widths[i] for i in range(len(widths)))

        # Create rows
        table_rows = []
        for row in rows:
            table_rows.append(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))

        return "\n".join([header, separator] + table_rows)