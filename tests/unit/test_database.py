"""Unit tests for DatabaseTool."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from grok_py.tools.database import DatabaseTool
from grok_py.tools.base import ToolResult


class TestDatabaseTool:
    """Test DatabaseTool class."""

    def setup_method(self):
        """Set up test method."""
        self.tool = DatabaseTool()

    def test_init(self):
        """Test DatabaseTool initialization."""
        assert self.tool.name == "database"
        assert self.tool.description == "Database operations for SQLite, PostgreSQL, and MySQL (query, schema inspection, table operations)"
        assert self.tool.connections == {}
        assert self.tool.pools == {}

    def test_execute_sync_invalid_db_type(self):
        """Test execute_sync with invalid database type."""
        result = self.tool.execute_sync("connect", db_type="invalid")

        assert result.success is False
        assert "Invalid db_type" in result.error

    @patch('grok_py.tools.database.HAS_POSTGRES', False)
    def test_execute_sync_postgres_not_installed(self):
        """Test execute_sync with PostgreSQL when not installed."""
        result = self.tool.execute_sync("connect", db_type="postgresql", db_name="test")

        assert result.success is False
        assert "psycopg2 not installed" in result.error

    @patch('grok_py.tools.database.HAS_MYSQL', False)
    def test_execute_sync_mysql_not_installed(self):
        """Test execute_sync with MySQL when not installed."""
        result = self.tool.execute_sync("connect", db_type="mysql", db_name="test")

        assert result.success is False
        assert "PyMySQL not installed" in result.error

    def test_execute_sync_invalid_operation(self):
        """Test execute_sync with invalid operation."""
        result = self.tool.execute_sync("invalid_op", db_type="sqlite", db_name="test.db")

        assert result.success is False
        assert "Invalid operation" in result.error

    def test_get_connection_key(self):
        """Test _get_connection_key method."""
        key = self.tool._get_connection_key("sqlite", "test.db")
        assert key == "sqlite:test.db"

    @patch('sqlite3.connect')
    def test_connect_sqlite_success(self, mock_connect):
        """Test _connect with SQLite success."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        result = self.tool._connect("sqlite", "test.db")

        assert result.success is True
        assert "Connected to sqlite database: test.db" in result.data
        assert self.tool.connections["sqlite:test.db"] == mock_conn
        mock_connect.assert_called_once_with("test.db")

    def test_connect_sqlite_no_db_name(self):
        """Test _connect with SQLite without db_name."""
        result = self.tool._connect("sqlite", None)

        assert result.success is False
        assert "db_name is required" in result.error

    @patch('grok_py.tools.database.pool.SimpleConnectionPool')
    def test_connect_postgresql_success(self, mock_pool_class):
        """Test _connect with PostgreSQL success."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool_class.return_value = mock_pool
        mock_pool.getconn.return_value = mock_conn

        result = self.tool._connect("postgresql", "testdb", "localhost", 5432, "user", "pass")

        assert result.success is True
        assert "Connected to postgresql database: testdb" in result.data
        assert self.tool.connections["postgresql:testdb"] == mock_conn
        mock_pool_class.assert_called_once()

    def test_connect_postgresql_missing_params(self):
        """Test _connect with PostgreSQL missing parameters."""
        result = self.tool._connect("postgresql", "testdb")

        assert result.success is False
        assert "host, port, user, password required" in result.error

    @patch('grok_py.tools.database.pool.ConnectionPool')
    def test_connect_mysql_success(self, mock_pool_class):
        """Test _connect with MySQL success."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool_class.return_value = mock_pool
        mock_pool.get_connection.return_value = mock_conn

        result = self.tool._connect("mysql", "testdb", "localhost", 3306, "user", "pass")

        assert result.success is True
        assert "Connected to mysql database: testdb" in result.data
        assert self.tool.connections["mysql:testdb"] == mock_conn

    def test_disconnect_success(self):
        """Test _disconnect success."""
        mock_conn = MagicMock()
        self.tool.connections["sqlite:test.db"] = mock_conn

        result = self.tool._disconnect("sqlite", "test.db")

        assert result.success is True
        assert "Disconnected from sqlite database: test.db" in result.data
        mock_conn.close.assert_called_once()
        assert "sqlite:test.db" not in self.tool.connections

    def test_disconnect_no_connection(self):
        """Test _disconnect with no active connection."""
        result = self.tool._disconnect("sqlite", "test.db")

        assert result.success is False
        assert "No active connection" in result.error

    def test_get_connection_no_connection(self):
        """Test _get_connection with no active connection."""
        with pytest.raises(Exception, match="No active connection"):
            with self.tool._get_connection("sqlite", "test.db"):
                pass

    def test_execute_sql_no_sql(self):
        """Test _execute_sql without SQL."""
        result = self.tool._execute_sql("query", "sqlite", "test.db", None)

        assert result.success is False
        assert "sql is required" in result.error

    @patch.object(DatabaseTool, '_get_connection')
    def test_execute_sql_query_success(self, mock_get_conn):
        """Test _execute_sql query success."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("value1", "value2")]
        mock_cursor.description = [("col1",), ("col2",)]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._execute_sql("query", "sqlite", "test.db", "SELECT * FROM test")

        assert result.success is True
        assert "col1" in result.data
        assert "col2" in result.data
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test")

    @patch.object(DatabaseTool, '_get_connection')
    def test_execute_sql_execute_success(self, mock_get_conn):
        """Test _execute_sql execute success."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 5
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._execute_sql("execute", "sqlite", "test.db", "INSERT INTO test VALUES (1)")

        assert result.success is True
        assert "Rows affected: 5" in result.data
        mock_conn.commit.assert_called_once()

    @patch.object(DatabaseTool, '_get_connection')
    def test_execute_sql_json_format(self, mock_get_conn):
        """Test _execute_sql with JSON output format."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("value1", "value2")]
        mock_cursor.description = [("col1",), ("col2",)]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._execute_sql("query", "sqlite", "test.db", "SELECT * FROM test", output_format="json")

        assert result.success is True
        assert isinstance(result.data, str)  # JSON string

    @patch.object(DatabaseTool, '_get_connection')
    def test_execute_sql_csv_format(self, mock_get_conn):
        """Test _execute_sql with CSV output format."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("value1", "value2")]
        mock_cursor.description = [("col1",), ("col2",)]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._execute_sql("query", "sqlite", "test.db", "SELECT * FROM test", output_format="csv")

        assert result.success is True
        assert "col1,col2" in result.data
        assert "value1,value2" in result.data

    @patch.object(DatabaseTool, '_get_connection')
    def test_list_tables_sqlite(self, mock_get_conn):
        """Test _list_tables with SQLite."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("table1",), ("table2",)]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._list_tables("sqlite", "test.db")

        assert result.success is True
        assert "table1\ntable2" == result.data
        mock_cursor.execute.assert_called_once_with("SELECT name FROM sqlite_master WHERE type='table'")

    @patch.object(DatabaseTool, '_get_connection')
    def test_list_tables_postgresql(self, mock_get_conn):
        """Test _list_tables with PostgreSQL."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("table1",), ("table2",)]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._list_tables("postgresql", "testdb")

        assert result.success is True
        mock_cursor.execute.assert_called_once_with("SELECT tablename FROM pg_tables WHERE schemaname <> 'pg_catalog' AND schemaname <> 'information_schema' AND schemaname NOT IN ('pg_catalog', 'information_schema')")

    @patch.object(DatabaseTool, '_get_connection')
    def test_describe_table_sqlite(self, mock_get_conn):
        """Test _describe_table with SQLite."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(0, "id", "INTEGER", 1, None, 1), (1, "name", "TEXT", 0, None, 0)]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._describe_table("sqlite", "test.db", "users")

        assert result.success is True
        assert "cid" in result.data
        assert "name" in result.data
        mock_cursor.execute.assert_called_once_with("PRAGMA table_info(users)")

    def test_describe_table_no_table_name(self):
        """Test _describe_table without table name."""
        result = self.tool._describe_table("sqlite", "test.db", None)

        assert result.success is False
        assert "table_name is required" in result.error

    @patch.object(DatabaseTool, '_get_connection')
    def test_table_operation_success(self, mock_get_conn):
        """Test _table_operation success."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._table_operation("create_table", "sqlite", "test.db", "CREATE TABLE test (id INTEGER)")

        assert result.success is True
        assert "completed successfully" in result.data
        mock_conn.commit.assert_called_once()

    def test_table_operation_no_sql(self):
        """Test _table_operation without SQL."""
        result = self.tool._table_operation("create_table", "sqlite", "test.db", None)

        assert result.success is False
        assert "sql is required" in result.error

    @patch.object(DatabaseTool, '_get_connection')
    def test_transaction_operation_begin(self, mock_get_conn):
        """Test _transaction_operation begin."""
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._transaction_operation("begin_transaction", "sqlite", "test.db")

        assert result.success is True
        assert result.data == "Transaction started"

    @patch.object(DatabaseTool, '_get_connection')
    def test_transaction_operation_commit(self, mock_get_conn):
        """Test _transaction_operation commit."""
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._transaction_operation("commit", "sqlite", "test.db")

        assert result.success is True
        assert result.data == "Transaction committed"
        mock_conn.commit.assert_called_once()

    @patch.object(DatabaseTool, '_get_connection')
    def test_transaction_operation_rollback(self, mock_get_conn):
        """Test _transaction_operation rollback."""
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = self.tool._transaction_operation("rollback", "sqlite", "test.db")

        assert result.success is True
        assert result.data == "Transaction rolled back"
        mock_conn.rollback.assert_called_once()

    def test_format_table_no_results(self):
        """Test _format_table with no results."""
        result = self.tool._format_table(["col1", "col2"], [])

        assert result == "No results"

    def test_format_table_with_results(self):
        """Test _format_table with results."""
        columns = ["id", "name"]
        rows = [(1, "Alice"), (2, "Bob")]

        result = self.tool._format_table(columns, rows)

        assert "id" in result
        assert "name" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "|" in result  # Table separator