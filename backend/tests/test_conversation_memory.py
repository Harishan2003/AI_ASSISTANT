# Module: backend.tests.test_conversation_memory
import asyncio
import time
from app.services.conversation_memory_service import ConversationMemoryService


def test_conversation_crud_and_isolation(tmp_path):
    async def _run():
        service = ConversationMemoryService(storage_dir=tmp_path / "convs", ttl_days=15)
        
        conv1 = await service.create_conversation("Chat 1")
        conv2 = await service.create_conversation("Chat 2")
        
        await service.add_message(conv1["conversation_id"], "user", "Message in Chat 1")
        
        msgs1 = await service.get_messages(conv1["conversation_id"])
        msgs2 = await service.get_messages(conv2["conversation_id"])
        
        assert len(msgs1) == 1
        assert msgs1[0]["content"] == "Message in Chat 1"
        assert len(msgs2) == 0

    asyncio.run(_run())


def test_sliding_expiration(tmp_path):
    async def _run():
        service = ConversationMemoryService(storage_dir=tmp_path / "exp_convs", ttl_days=0)
        conv = await service.create_conversation("Expiring Chat")
        
        # Backdate expiration
        file_path = service._get_file_path(conv["conversation_id"])
        data = service._load_json(file_path)
        data["expires_at"] = time.time() - 5
        service._save_json(file_path, data)
        
        removed = service.cleanup_expired_conversations()
        assert removed == 1
        assert await service.get_conversation(conv["conversation_id"]) is None

    asyncio.run(_run())