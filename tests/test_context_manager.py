import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from src.context.manager import ContextManager
from src.context.base import BaseContext, ContextType, Priority
from src.context.memory import WorkingMemory, LongTermMemory # For spec
from datetime import datetime, timedelta, timezone # Added timezone for tz-aware datetimes

@pytest.fixture
def mock_working_memory_instance():
    mem = MagicMock(spec=WorkingMemory)
    mem.add = AsyncMock()
    mem.get = AsyncMock(return_value=None)
    mem.search = AsyncMock(return_value=[])
    mem.get_all = AsyncMock(return_value=[])
    mem.remove = AsyncMock() # Added for potential future tests
    mem.compress = AsyncMock(return_value=None) # Added for potential future tests
    mem.size = MagicMock(return_value=0) # Mock as a callable method
    mem.limit = 50
    return mem

@pytest.fixture
def mock_long_term_memory_instance():
    ltm = MagicMock(spec=LongTermMemory)
    ltm.store = AsyncMock()
    ltm.retrieve_related = AsyncMock(return_value=[])
    return ltm

@pytest.fixture
def context_manager_instance(mock_working_memory_instance, mock_long_term_memory_instance):
    # Patching where WorkingMemory and LongTermMemory are looked up by ContextManager
    with patch("src.context.manager.WorkingMemory", return_value=mock_working_memory_instance) as patched_wm, \
         patch("src.context.manager.LongTermMemory", return_value=mock_long_term_memory_instance) as patched_ltm:
        manager = ContextManager(working_memory_limit=77, auto_compress=True, compression_threshold=150)
        # Attach mocks to the manager instance for easier access in tests
        manager.mock_wm_inst = mock_working_memory_instance
        manager.mock_ltm_inst = mock_long_term_memory_instance
        manager.PatchedWM_cls = patched_wm
        manager.PatchedLTM_cls = patched_ltm
        return manager

class TestContextManager:
    def test_init(self, context_manager_instance): # No asyncio needed for init test
        manager = context_manager_instance
        manager.PatchedWM_cls.assert_called_once_with(limit=77)
        manager.PatchedLTM_cls.assert_called_once()

        assert manager.auto_compress == True
        assert manager.compression_threshold == 150
        assert manager.stats["total_contexts_added"] == 0 # Corrected stat name based on add_context
        assert manager.stats["active_contexts"] == 0
        assert manager.stats["retrievals"] == 0
        assert manager.stats["compressions"] == 0


    @pytest.mark.asyncio
    async def test_add_context_basic(self, context_manager_instance):
        manager = context_manager_instance
        content = "Test content for add"
        context_type = ContextType.CONVERSATION
        priority = Priority.HIGH
        tags = ["test", "add"]
        related_ids = ["id1", "id2"]

        context_id = await manager.add_context(content, context_type, priority=priority, tags=tags, related_ids=related_ids)

        assert context_id is not None
        manager.mock_wm_inst.add.assert_called_once()
        added_context_arg = manager.mock_wm_inst.add.call_args[0][0]

        assert isinstance(added_context_arg, BaseContext)
        assert added_context_arg.id == context_id
        assert added_context_arg.content == content
        assert added_context_arg.context_type == context_type
        assert added_context_arg.priority == priority
        assert added_context_arg.tags == tags
        assert added_context_arg.related_ids == related_ids

        assert manager.stats["total_contexts_added"] == 1
        assert manager.stats["active_contexts"] == 1 # Based on current WM size mock
        manager.mock_wm_inst.size.assert_called_once() # To update active_contexts


    @pytest.mark.asyncio
    async def test_get_context_found(self, context_manager_instance):
        manager = context_manager_instance
        mock_ctx = MagicMock(spec=BaseContext)
        mock_ctx.id = "test_id_found"
        mock_ctx.update_access = MagicMock() # Method on the instance
        manager.mock_wm_inst.get.return_value = mock_ctx

        retrieved_ctx = await manager.get_context("test_id_found")

        manager.mock_wm_inst.get.assert_called_once_with("test_id_found")
        assert retrieved_ctx == mock_ctx
        mock_ctx.update_access.assert_called_once()
        assert manager.stats["retrievals"] == 1

    @pytest.mark.asyncio
    async def test_get_context_not_found(self, context_manager_instance):
        manager = context_manager_instance
        manager.mock_wm_inst.get.return_value = None # Default, but explicit

        retrieved_ctx = await manager.get_context("test_id_not_found")

        manager.mock_wm_inst.get.assert_called_once_with("test_id_not_found")
        assert retrieved_ctx is None
        assert manager.stats["retrievals"] == 0 # Not incremented if not found

    @pytest.mark.asyncio
    async def test_search_contexts_basic(self, context_manager_instance):
        manager = context_manager_instance
        mock_ctx1 = MagicMock(spec=BaseContext, id="s_id1")
        mock_ctx1.update_access = MagicMock()
        mock_ctx2 = MagicMock(spec=BaseContext, id="s_id2")
        mock_ctx2.update_access = MagicMock()

        manager.mock_wm_inst.search.return_value = [mock_ctx1, mock_ctx2]

        query = "search query"
        results = await manager.search_contexts(query, limit=5)

        manager.mock_wm_inst.search.assert_called_once_with(query, 5)
        assert len(results) == 2
        assert results[0] == mock_ctx1
        assert results[1] == mock_ctx2
        mock_ctx1.update_access.assert_called_once()
        mock_ctx2.update_access.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_contexts_with_filters(self, context_manager_instance):
        manager = context_manager_instance

        # Mock contexts with properties needed for filtering
        # All times are timezone-aware (UTC)
        now = datetime.now(timezone.utc)
        ctx1 = BaseContext(id="f_id1", content="content1", context_type=ContextType.KNOWLEDGE, tags=["A", "B"], priority=Priority.HIGH, last_access=now - timedelta(minutes=10))
        ctx1.update_access = MagicMock() # Mock this method for each instance
        ctx2 = BaseContext(id="f_id2", content="content2", context_type=ContextType.CONVERSATION, tags=["B", "C"], priority=Priority.MEDIUM, last_access=now - timedelta(minutes=5))
        ctx2.update_access = MagicMock()
        ctx3 = BaseContext(id="f_id3", content="content3", context_type=ContextType.KNOWLEDGE, tags=["A", "D"], priority=Priority.HIGH, last_access=now)
        ctx3.update_access = MagicMock()

        manager.mock_wm_inst.search.return_value = [ctx1, ctx2, ctx3] # Assume search returns all for this test

        # Filter by type
        results = await manager.search_contexts("query", context_type=ContextType.KNOWLEDGE)
        assert len(results) == 2
        assert all(r.context_type == ContextType.KNOWLEDGE for r in results)
        assert ctx1 in results and ctx3 in results
        ctx1.update_access.assert_called() # Check if called at least once
        ctx3.update_access.assert_called()

        # Filter by tags (all_tags)
        ctx1.update_access.reset_mock() # Reset for next check
        ctx3.update_access.reset_mock()
        results = await manager.search_contexts("query", tags=["A", "B"], match_all_tags=True)
        assert len(results) == 1
        assert results[0].id == "f_id1"
        results[0].update_access.assert_called_once()

        # Filter by priority
        results = await manager.search_contexts("query", priority=Priority.MEDIUM)
        assert len(results) == 1
        assert results[0].id == "f_id2"

        # Filter by date range (after)
        results = await manager.search_contexts("query", after_date=now - timedelta(minutes=7))
        assert len(results) == 2
        assert ctx2 in results and ctx3 in results

        # Filter by date range (before)
        results = await manager.search_contexts("query", before_date=now - timedelta(minutes=7))
        assert len(results) == 1
        assert ctx1 in results


    @pytest.mark.asyncio
    async def test_get_recent_contexts(self, context_manager_instance):
        manager = context_manager_instance
        now = datetime.now(timezone.utc)
        ctx1 = BaseContext(id="r_id1", content="c1", context_type=ContextType.KNOWLEDGE, last_access=now - timedelta(days=1))
        ctx2 = BaseContext(id="r_id2", content="c2", context_type=ContextType.CONVERSATION, last_access=now)
        ctx3 = BaseContext(id="r_id3", content="c3", context_type=ContextType.KNOWLEDGE, last_access=now - timedelta(hours=1))

        manager.mock_wm_inst.get_all.return_value = [ctx1, ctx2, ctx3]

        # Get 2 most recent
        recent = await manager.get_recent_contexts(limit=2)
        assert len(recent) == 2
        assert recent[0].id == "r_id2" # Most recent
        assert recent[1].id == "r_id3"

        # Get recent of specific type
        recent_knowledge = await manager.get_recent_contexts(limit=1, context_type=ContextType.KNOWLEDGE)
        assert len(recent_knowledge) == 1
        assert recent_knowledge[0].id == "r_id3"

    def test_calculate_similarity_direct(self, context_manager_instance):
        manager = context_manager_instance
        now = datetime.now(timezone.utc)
        ctx1 = BaseContext(id="sim1", content="The quick brown fox", context_type=ContextType.KNOWLEDGE,
                           tags=["animal", "sentence"], priority=Priority.HIGH, last_access=now,
                           related_ids=["sim0"], parent_id=None)
        ctx2 = BaseContext(id="sim2", content="A quick brown dog", context_type=ContextType.KNOWLEDGE,
                           tags=["animal", "pet"], priority=Priority.MEDIUM, last_access=now - timedelta(minutes=1),
                           related_ids=["sim3"], parent_id=None)
        ctx3 = BaseContext(id="sim3", content="Lazy dog jumps over", context_type=ContextType.KNOWLEDGE,
                           tags=["animal", "pet"], priority=Priority.LOW, last_access=now - timedelta(minutes=2),
                           related_ids=["sim2"], parent_id="sim_parent") # parent_id shared with ctx2 if it was sim_parent
        ctx4 = BaseContext(id="sim4", content="Hello world", context_type=ContextType.CONVERSATION,
                           tags=["greeting"], priority=Priority.NORMAL, last_access=now - timedelta(days=1))
        ctx5 = BaseContext(id="sim5", content="The quick brown fox", context_type=ContextType.KNOWLEDGE,
                           tags=["animal", "sentence"], priority=Priority.HIGH, last_access=now,
                           related_ids=["sim0"], parent_id=None) # Identical to ctx1 (except ID)

        sim_1_2 = manager._calculate_similarity(ctx1, ctx2) # Same type, 1 common tag, 3 common words, different priority
        assert sim_1_2 > 0.5 and sim_1_2 < 1.0 # Should be reasonably high

        sim_1_3 = manager._calculate_similarity(ctx1, ctx3) # Same type, 1 common tag, 0 common words
        assert sim_1_3 > 0.1 and sim_1_3 < 0.5

        sim_1_4 = manager._calculate_similarity(ctx1, ctx4) # Different type, no common tags, no common words
        assert sim_1_4 < 0.1 # Should be very low (only time proximity might add a tiny bit if recent)

        sim_2_3 = manager._calculate_similarity(ctx2, ctx3) # Same type, 2 common tags, 1 common word ("dog"), related_ids link
        assert sim_2_3 > 0.6 # Should be high due to tags and related_ids link

        sim_1_5 = manager._calculate_similarity(ctx1, ctx5) # Identical content, type, tags, priority
        assert sim_1_5 == 1.0


    @pytest.mark.asyncio
    async def test_get_related_contexts_logic(self, context_manager_instance):
        manager = context_manager_instance
        now = datetime.now(timezone.utc)

        target_ctx = BaseContext(id="target", content="target content about cats", context_type=ContextType.KNOWLEDGE,
                                 tags=["animal", "pet"], related_ids=["rel1", "rel2"], parent_id="parent1")

        # Mock for manager.get_context(target_ctx_id)
        manager.mock_wm_inst.get.return_value = target_ctx

        # Other contexts in memory
        ctx_rel1 = BaseContext(id="rel1", content="related by ID", context_type=ContextType.KNOWLEDGE, tags=["animal"])
        ctx_parent1 = BaseContext(id="parent1", content="parent context", context_type=ContextType.KNOWLEDGE, tags=["family"])
        ctx_similar_tag = BaseContext(id="sim_tag", content="another pet", context_type=ContextType.KNOWLEDGE, tags=["pet", "dog"])
        ctx_similar_content = BaseContext(id="sim_content", content="discussion about cats and dogs", context_type=ContextType.CONVERSATION)
        ctx_unrelated = BaseContext(id="unrelated", content="space exploration", context_type=ContextType.ARTICLE)

        all_contexts_in_wm = [target_ctx, ctx_rel1, ctx_parent1, ctx_similar_tag, ctx_similar_content, ctx_unrelated]
        manager.mock_wm_inst.get_all.return_value = all_contexts_in_wm

        # Mock _calculate_similarity to return predictable scores for easier assertion
        def mock_similarity_side_effect(c1, c2):
            if c1.id == "target":
                if c2.id == "rel1": return 0.8 # Explicitly related
                if c2.id == "parent1": return 0.7 # Parent
                if c2.id == "sim_tag": return 0.6 # Shared tag
                if c2.id == "sim_content": return 0.5 # Shared content words
            return 0.1 # Default low similarity

        with patch.object(manager, '_calculate_similarity', side_effect=mock_similarity_side_effect) as mock_calc_sim:
            related_found = await manager.get_related_contexts("target", limit=3)

            assert len(related_found) == 3
            # Order depends on similarity scores: rel1 (0.8), parent1 (0.7), sim_tag (0.6)
            assert related_found[0].id == "rel1"
            assert related_found[1].id == "parent1"
            assert related_found[2].id == "sim_tag"

            # Ensure _calculate_similarity was called for contexts other than target_ctx itself
            assert mock_calc_sim.call_count == len(all_contexts_in_wm) -1


    def test_get_stats(self, context_manager_instance):
        manager = context_manager_instance
        manager.mock_wm_inst.size.return_value = 5 # Mock current size of working memory
        manager.mock_wm_inst.limit = 80 # Ensure limit is what we expect

        # Simulate some operations to populate other stats
        manager.stats["total_contexts_added"] = 10
        manager.stats["retrievals"] = 3
        manager.stats["compressions"] = 1

        stats = manager.get_stats()

        assert stats["active_contexts"] == 5
        assert stats["working_memory_limit"] == 80
        assert stats["total_contexts_added"] == 10
        assert stats["retrievals"] == 3
        assert stats["compressions"] == 1
        manager.mock_wm_inst.size.assert_called_once() # Check .size() was called
```
