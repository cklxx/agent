import pytest
import asyncio
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock, call
from collections import OrderedDict

from src.context.memory import WorkingMemory, SQLiteStorage, LongTermMemory
from src.context.base import BaseContext, ContextType, Priority

# Helper to create BaseContext mocks easily
def create_mock_context(id_val, content_val="content", type_val=ContextType.GENERIC, priority_val=Priority.MEDIUM, tags_val=None, last_access_val=None, timestamp_val=None):
    ctx = MagicMock(spec=BaseContext)
    ctx.id = id_val
    ctx.content = content_val
    ctx.context_type = type_val
    ctx.priority = priority_val
    ctx.tags = tags_val if tags_val is not None else []
    ctx.metadata = {}
    ctx.related_ids = []
    ctx.parent_id = None
    ctx.is_active = True
    ctx.is_compressed = False
    ctx.access_count = 0
    ctx.timestamp = timestamp_val if timestamp_val else datetime.now(timezone.utc)
    ctx.last_access = last_access_val if last_access_val else datetime.now(timezone.utc)

    # Make update_access an AsyncMock if it's awaited anywhere, otherwise MagicMock is fine
    # Based on WorkingMemory.get, it's not awaited.
    ctx.update_access = MagicMock()

    # Helper for serializable content for SQLiteStorage tests
    ctx.get_serializable_content = lambda: json.dumps(ctx.content) if isinstance(ctx.content, (dict, list)) else str(ctx.content)

    # Add other attributes that are accessed by the classes under test
    ctx.summary = None # Assuming BaseContext might have this
    ctx.embedding = None # Assuming BaseContext might have this
    return ctx

class TestWorkingMemory:
    @pytest.mark.asyncio
    async def test_add_and_get_context(self):
        wm = WorkingMemory(limit=2)
        ctx1_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        ctx2_time = datetime.now(timezone.utc) - timedelta(seconds=5)
        ctx1 = create_mock_context("id1", last_access_val=ctx1_time, timestamp_val=ctx1_time)
        ctx2 = create_mock_context("id2", last_access_val=ctx2_time, timestamp_val=ctx2_time)

        await wm.add(ctx1) # Added first, should be at the "cold" end initially
        await wm.add(ctx2) # Added second, should be at the "hot" end initially

        # Initial order should be id1, id2 (oldest to newest based on add order)
        assert list(wm._contexts.keys()) == ["id1", "id2"]

        ret_ctx2 = await wm.get("id2")
        assert ret_ctx2 == ctx2
        ret_ctx2.update_access.assert_called_once()
        # Accessing id2 moves it to the end (most recent)
        assert list(wm._contexts.keys()) == ["id1", "id2"] # Order unchanged as id2 was already at end

        ret_ctx1 = await wm.get("id1")
        assert ret_ctx1 == ctx1
        ret_ctx1.update_access.assert_called_once()
        # Accessing id1 moves it to the end
        assert list(wm._contexts.keys()) == ["id2", "id1"]

    @pytest.mark.asyncio
    async def test_add_eviction(self):
        wm = WorkingMemory(limit=1)
        ctx1 = create_mock_context("id1")
        ctx2 = create_mock_context("id2")

        await wm.add(ctx1)
        assert wm.size() == 1

        await wm.add(ctx2) # This should evict ctx1
        assert wm.size() == 1

        assert await wm.get("id1") is None
        ret_ctx2 = await wm.get("id2")
        assert ret_ctx2 is not None
        assert ret_ctx2.id == "id2"


    @pytest.mark.asyncio
    async def test_remove_context(self):
        wm = WorkingMemory(limit=2)
        ctx1 = create_mock_context("id1")
        await wm.add(ctx1)
        assert wm.size() == 1

        removed_ctx = await wm.remove("id1")
        assert removed_ctx == ctx1
        assert wm.size() == 0
        assert await wm.get("id1") is None

        removed_ctx_non_existent = await wm.remove("non_id")
        assert removed_ctx_non_existent is None

    @pytest.mark.asyncio
    async def test_get_all_contexts(self):
        wm = WorkingMemory(limit=2)
        ctx1 = create_mock_context("id1")
        ctx2 = create_mock_context("id2")
        await wm.add(ctx1)
        await wm.add(ctx2)

        all_ctx = await wm.get_all()
        assert len(all_ctx) == 2
        assert ctx1 in all_ctx
        assert ctx2 in all_ctx

    @pytest.mark.asyncio
    async def test_search_contexts(self):
        wm = WorkingMemory(limit=3)
        now = datetime.now(timezone.utc)
        ctx1 = create_mock_context("id1", content_val="apple banana", tags_val=["fruit"], last_access_val=now - timedelta(minutes=10))
        ctx2 = create_mock_context("id2", content_val="apple pie", tags_val=["dessert"], last_access_val=now)
        ctx3 = create_mock_context("id3", content_val="banana smoothie", tags_val=["fruit", "drink"], last_access_val=now - timedelta(minutes=5))

        await wm.add(ctx1)
        await wm.add(ctx2)
        await wm.add(ctx3)

        # Search by keyword "apple"
        results_apple = await wm.search("apple", limit=2)
        assert len(results_apple) == 2
        # Results should be ctx2 (most recent access containing "apple") then ctx1
        assert results_apple[0].id == "id2"
        assert results_apple[1].id == "id1"

        # Search by tag "fruit"
        results_fruit = await wm.search(tags=["fruit"], limit=2)
        assert len(results_fruit) == 2
        # Results should be ctx3 then ctx1 (most recent access with tag "fruit")
        assert results_fruit[0].id == "id3"
        assert results_fruit[1].id == "id1"

        # Search by keyword and tag
        results_banana_drink = await wm.search(query="banana", tags=["drink"], limit=1)
        assert len(results_banana_drink) == 1
        assert results_banana_drink[0].id == "id3"

    def test_size_and_limit(self): # Not async
        wm = WorkingMemory(limit=5)
        assert wm.limit == 5
        assert wm.size() == 0


@patch("src.context.memory.os.makedirs")
class TestSQLiteStorage:
    @pytest.fixture
    def db_path(self, tmp_path):
        return str(tmp_path / "test_contexts.db")

    @patch("sqlite3.connect")
    def test_init_db(self, mock_sql_connect, mock_makedirs_in_class, db_path): # Renamed mock_makedirs
        mock_conn = MagicMock(spec=sqlite3.Connection)
        # Configure the context manager __enter__ to return the mock connection
        mock_sql_connect.return_value.__enter__.return_value = mock_conn

        storage = SQLiteStorage(db_path=db_path)
        # _init_db is called in constructor, so check effects after instantiation

        mock_makedirs_in_class.assert_called_once_with(os.path.dirname(db_path), exist_ok=True)
        mock_sql_connect.assert_called_once_with(db_path)

        # Check for CREATE TABLE statements (order might vary due to set iteration in _init_db)
        executed_sqls = [c[0][0] for c in mock_conn.execute.call_args_list]
        assert any("CREATE TABLE IF NOT EXISTS contexts" in sql for sql in executed_sqls)
        assert any("CREATE INDEX IF NOT EXISTS idx_contexts_type" in sql for sql in executed_sqls)
        assert any("CREATE INDEX IF NOT EXISTS idx_contexts_priority" in sql for sql in executed_sqls)
        assert any("CREATE INDEX IF NOT EXISTS idx_contexts_last_access" in sql for sql in executed_sqls)

    def test_row_to_context(self, db_path): # Not async, direct method test
        storage = SQLiteStorage(db_path=db_path) # Instantiation for method access
        now_iso = datetime.now(timezone.utc).isoformat()
        row_data = (
            "test_id", ContextType.KNOWLEDGE.value, '{"data": "content"}', '{"meta": "data"}',
            now_iso, Priority.HIGH.value, '["tag1", "tag2"]', "parent_id_val", '["rel1", "rel2"]',
            1, True, False, now_iso, "summary_val", '[0.1, 0.2]'
        )

        ctx = storage._row_to_context(row_data)

        assert isinstance(ctx, BaseContext)
        assert ctx.id == "test_id"
        assert ctx.context_type == ContextType.KNOWLEDGE
        assert ctx.content == {"data": "content"} # Deserialized JSON
        assert ctx.metadata == {"meta": "data"}
        assert ctx.timestamp == datetime.fromisoformat(now_iso)
        assert ctx.priority == Priority.HIGH
        assert ctx.tags == ["tag1", "tag2"]
        assert ctx.parent_id == "parent_id_val"
        assert ctx.related_ids == ["rel1", "rel2"]
        assert ctx.access_count == 1
        assert ctx.is_active == True
        assert ctx.is_compressed == False
        assert ctx.last_access == datetime.fromisoformat(now_iso)
        assert ctx.summary == "summary_val"
        assert ctx.embedding == [0.1, 0.2]

    @pytest.mark.asyncio
    @patch("sqlite3.connect")
    async def test_save_context_sql(self, mock_sql_connect, mock_makedirs_in_class, db_path):
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock(spec=sqlite3.Cursor)
        mock_conn.cursor.return_value = mock_cursor
        mock_sql_connect.return_value.__aenter__.return_value = mock_conn # For async context manager

        storage = SQLiteStorage(db_path=db_path)

        now = datetime.now(timezone.utc)
        ctx_to_save = BaseContext(
            id="test_id_save", content={"key": "value"}, context_type=ContextType.KNOWLEDGE,
            priority=Priority.HIGH, tags=["t1", "t2"], metadata={"m_key": "m_val"},
            related_ids=["r1"], parent_id="p1", timestamp=now, last_access=now,
            access_count=5, is_active=True, is_compressed=False,
            summary="A summary", embedding=[0.1, 0.2, 0.3]
        )

        success = await storage.save(ctx_to_save)
        assert success == True

        expected_sql_start = "INSERT OR REPLACE INTO contexts"
        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        assert args[0].startswith(expected_sql_start)

        params = args[1]
        assert params[0] == "test_id_save"
        assert params[1] == ContextType.KNOWLEDGE.value
        assert params[2] == json.dumps({"key": "value"})
        assert params[3] == json.dumps({"m_key": "m_val"})
        assert params[4] == now.isoformat()
        assert params[5] == Priority.HIGH.value
        assert params[6] == json.dumps(["t1", "t2"])
        assert params[7] == "p1"
        assert params[8] == json.dumps(["r1"])
        assert params[9] == 5 # access_count
        assert params[10] == True # is_active
        assert params[11] == False # is_compressed
        assert params[12] == now.isoformat() # last_access
        assert params[13] == "A summary" # summary
        assert params[14] == json.dumps([0.1, 0.2, 0.3]) # embedding
        mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("sqlite3.connect")
    async def test_load_context(self, mock_sql_connect, mock_makedirs_in_class, db_path):
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock(spec=sqlite3.Cursor)
        mock_conn.cursor.return_value = mock_cursor
        mock_sql_connect.return_value.__aenter__.return_value = mock_conn

        storage = SQLiteStorage(db_path=db_path)
        now_iso = datetime.now(timezone.utc).isoformat()
        # Sample row data that _row_to_context would process
        row_data = (
            "load_id", ContextType.CONVERSATION.value, "text content", "{}",
            now_iso, Priority.LOW.value, "[]", None, "[]",
            0, True, False, now_iso, None, None
        )
        mock_cursor.fetchone.return_value = row_data

        loaded_ctx = await storage.load("load_id")

        mock_cursor.execute.assert_called_once_with("SELECT * FROM contexts WHERE id = ?", ("load_id",))
        assert loaded_ctx is not None
        assert loaded_ctx.id == "load_id"
        assert loaded_ctx.content == "text content"

    @pytest.mark.asyncio
    @patch("sqlite3.connect")
    async def test_delete_context(self, mock_sql_connect, mock_makedirs_in_class, db_path):
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock(spec=sqlite3.Cursor)
        mock_conn.cursor.return_value = mock_cursor
        mock_sql_connect.return_value.__aenter__.return_value = mock_conn

        storage = SQLiteStorage(db_path=db_path)
        success = await storage.delete("delete_id")

        assert success == True
        mock_cursor.execute.assert_called_once_with("DELETE FROM contexts WHERE id = ?", ("delete_id",))
        mock_conn.commit.assert_called_once()

    # TODO: More tests for SQLiteStorage: search, list_by_type, handling of DB errors, etc.

class TestLongTermMemory:
    @pytest.mark.asyncio
    async def test_default_sqlite_storage_init(self):
        # Test that LongTermMemory instantiates SQLiteStorage by default
        with patch("src.context.memory.SQLiteStorage") as MockSQLiteStorageCls:
            mock_sqlite_instance = AsyncMock(spec=SQLiteStorage) # Use AsyncMock for the instance
            MockSQLiteStorageCls.return_value = mock_sqlite_instance

            ltm = LongTermMemory(db_path=":memory:") # Provide a db_path

            MockSQLiteStorageCls.assert_called_once_with(db_path=":memory:")
            assert ltm.storage == mock_sqlite_instance

    @pytest.mark.asyncio
    async def test_custom_storage_init(self):
        mock_custom_storage = AsyncMock() # A pre-instantiated custom storage object
        ltm = LongTermMemory(storage=mock_custom_storage)
        assert ltm.storage == mock_custom_storage

    @pytest.mark.asyncio
    async def test_save_delegation(self):
        mock_storage_backend = AsyncMock(spec=SQLiteStorage) # So it has async methods
        ltm = LongTermMemory(storage=mock_storage_backend)
        ctx = create_mock_context("id_ltm_save")

        await ltm.save(ctx)
        mock_storage_backend.save.assert_called_once_with(ctx)

    @pytest.mark.asyncio
    async def test_load_delegation(self):
        mock_storage_backend = AsyncMock(spec=SQLiteStorage)
        ltm = LongTermMemory(storage=mock_storage_backend)
        mock_storage_backend.load.return_value = "loaded_context_data" # Example return

        result = await ltm.load("id_ltm_load")
        mock_storage_backend.load.assert_called_once_with("id_ltm_load")
        assert result == "loaded_context_data"

    @pytest.mark.asyncio
    async def test_delete_delegation(self):
        mock_storage_backend = AsyncMock(spec=SQLiteStorage)
        ltm = LongTermMemory(storage=mock_storage_backend)
        mock_storage_backend.delete.return_value = True # Example return

        result = await ltm.delete("id_ltm_delete")
        mock_storage_backend.delete.assert_called_once_with("id_ltm_delete")
        assert result == True

    @pytest.mark.asyncio
    async def test_search_delegation(self):
        mock_storage_backend = AsyncMock(spec=SQLiteStorage)
        ltm = LongTermMemory(storage=mock_storage_backend)
        mock_storage_backend.search.return_value = ["search_result1"]

        results = await ltm.search(query="q", limit=1, context_type=ContextType.KNOWLEDGE, tags=["t"])
        mock_storage_backend.search.assert_called_once_with(
            query="q", limit=1, context_type=ContextType.KNOWLEDGE, tags=["t"],
            priority=None, after_date=None, before_date=None, match_all_tags=False
        )
        assert results == ["search_result1"]

    @pytest.mark.asyncio
    async def test_list_by_type_delegation(self):
        mock_storage_backend = AsyncMock(spec=SQLiteStorage)
        ltm = LongTermMemory(storage=mock_storage_backend)
        mock_storage_backend.list_by_type.return_value = ["list_result1"]

        results = await ltm.list_by_type(context_type=ContextType.CONVERSATION, limit=5)
        mock_storage_backend.list_by_type.assert_called_once_with(
            context_type=ContextType.CONVERSATION, limit=5
        )
        assert results == ["list_result1"]

```
