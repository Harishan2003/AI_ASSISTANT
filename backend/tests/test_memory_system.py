# Module: backend.tests.test_memory_system
import asyncio
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.memory.embeddings import HashEmbedder
from app.memory.vector_store import MemoryVectorStore, VectorDocument, cosine_similarity
from app.memory.conversation_memory import MemoryJobStore, JobStatus, stable_hash
from app.memory.long_term_memory import LongTermMemory
from app.memory.profile_memory import ProfileMemory
from app.memory.memory_manager import FridayMemoryManager
from app.agents.memory_agent import MemoryAgent
from app.services.conversation_memory_service import ConversationMemoryService
from main import app


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


def test_hash_embedder():
    embedder = HashEmbedder(dimension=64)
    vec1 = embedder.embed("Artificial intelligence neural network")
    vec2 = embedder.embed("Artificial intelligence neural network")
    vec3 = embedder.embed("Recipe for baking chocolate cake")

    assert len(vec1) == 64
    assert len(vec2) == 64
    assert vec1 == vec2  # Deterministic

    # Cosine similarity between identical text should be ~1.0
    sim_same = cosine_similarity(vec1, vec2)
    assert sim_same > 0.99

    # Cosine similarity between unrelated text should be significantly lower
    sim_diff = cosine_similarity(vec1, vec3)
    assert sim_same > sim_diff


def test_memory_vector_store(temp_dir):
    store_file = temp_dir / "test_store.json"
    vector_store = MemoryVectorStore(persist_path=store_file, auto_persist=True)
    vector_store.clear()

    docs = [
        VectorDocument(text="Friday is my personal AI assistant", metadata={"category": "ai", "user_id": "test_user"}),
        VectorDocument(text="My favorite programming language is Python", metadata={"category": "tech", "user_id": "test_user"}),
        VectorDocument(text="I enjoy playing chess on weekends", metadata={"category": "hobbies", "user_id": "test_user"}),
    ]

    ids = vector_store.add(docs)
    assert len(ids) == 3
    assert vector_store.count() == 3

    # Test search by text
    results = vector_store.search_by_text("What coding language do I like?", top_k=2)
    assert len(results) > 0
    assert "Python" in results[0].content

    # Test metadata filtering
    ai_results = vector_store.search_by_text("assistant", top_k=5, filters={"category": "ai"})
    assert len(ai_results) == 1
    assert "Friday" in ai_results[0].content

    # Test reload from disk
    reloaded_store = MemoryVectorStore(persist_path=store_file, auto_persist=False)
    assert reloaded_store.count() == 3
    assert reloaded_store.get(ids[0]) is not None

    # Test delete
    vector_store.delete([ids[0]])
    assert vector_store.count() == 2


def test_memory_job_store():
    job_store = MemoryJobStore()
    payload = {"user_query": "Hello Friday", "agent_response": "Hello boss"}
    idemp_fields = {"content": "Hello Friday"}

    job1, created1 = job_store.enqueue(
        job_type="memory_ingest",
        payload=payload,
        idempotency_fields=idemp_fields,
        user_id="user_1",
    )
    assert created1 is True
    assert job1.status == JobStatus.QUEUED

    # Duplicate enqueue should return existing job with created=False
    job2, created2 = job_store.enqueue(
        job_type="memory_ingest",
        payload=payload,
        idempotency_fields=idemp_fields,
        user_id="user_1",
    )
    assert created2 is False
    assert job2.job_id == job1.job_id

    # Claim for run
    claimed_job, claimed = job_store.claim_for_run(job1.job_id)
    assert claimed is True
    assert claimed_job.status == JobStatus.RUNNING

    # Mark succeeded
    success = job_store.mark_succeeded(job1.job_id, {"turn_id": "turn_123"})
    assert success is True
    assert job_store.get(job1.job_id).status == JobStatus.SUCCEEDED


def test_long_term_memory(temp_dir):
    facts_file = temp_dir / "facts.json"
    ltm = LongTermMemory(storage_path=facts_file)
    ltm.clear()

    fact_id = ltm.remember_fact("The server SSH port is 2222", category="infra", user_id="admin")
    assert fact_id.startswith("fact_")

    facts = ltm.list_facts(user_id="admin")
    assert len(facts) == 1
    assert facts[0]["fact"] == "The server SSH port is 2222"

    # Recall
    recalled = ltm.recall_facts("What is the server SSH port?", user_id="admin")
    assert len(recalled) > 0
    assert "2222" in recalled[0].content

    # Forget
    forgotten = ltm.forget_fact(fact_id)
    assert forgotten is True
    assert len(ltm.list_facts(user_id="admin")) == 0


def test_profile_memory(temp_dir):
    profile_file = temp_dir / "profile.json"
    pm = ProfileMemory(file_path=profile_file)

    initial = pm.get_profile()
    assert "name" in initial

    updated = pm.update_profile({"name": "Harishan", "agent_name": "Friday", "city": "Colombo"})
    assert updated["name"] == "Harishan"
    assert updated["agent_name"] == "Friday"
    assert updated["city"] == "Colombo"

    context = pm.get_formatted_context()
    assert "Harishan" in context
    assert "Colombo" in context


def test_friday_memory_manager(temp_dir):
    async def _run():
        store_file = temp_dir / "mm_store.json"
        vec_store = MemoryVectorStore(persist_path=store_file, auto_persist=False)
        vec_store.clear()

        manager = FridayMemoryManager(vector_store=vec_store)

        # Ingest sync
        turn_id = manager.ingest_turn_sync(
            user_query="My secret project codename is Project Jarvis",
            agent_response="Understood boss, Project Jarvis recorded.",
            user_id="test_user",
            session_id="session_1",
        )
        assert turn_id.startswith("turn_")

        # Fetch context
        ctx = await manager.fetch_memory_context("What is my secret project?", user_id="test_user")
        assert len(ctx["sources"]) > 0
        assert "Jarvis" in ctx["context_text"]

        # Ingest async
        job, created = await manager.ingest_turn_async(
            user_query="Remember to backup database at 10 PM",
            agent_response="Acknowledged.",
            user_id="test_user",
            session_id="session_1",
        )
        assert job.job_id.startswith("job_")
        await asyncio.sleep(0.1)  # Allow background task to complete

    asyncio.run(_run())


def test_memory_agent():
    async def _run():
        agent = MemoryAgent()

        # 1. Storing fact with numbers
        res1 = await agent.handle_query("remember the number 5", user_id="test_user")
        assert res1 is not None
        assert "the number 5" in res1

        # 2. Recalling remembered number
        res2 = await agent.handle_query("what is the number I told you to remember", user_id="test_user")
        assert res2 is not None
        assert "5" in res2

        # 3. Recalling last conversation turns
        past_turns = [
            {"role": "user", "content": "remember the number 5"},
            {"role": "assistant", "content": 'I\'ve committed that to memory, boss: "the number 5".'},
        ]
        res3 = await agent.handle_query(
            "what is the last conversation between you and me",
            user_id="test_user",
            past_turns=past_turns,
        )
        assert res3 is not None
        assert "remember the number 5" in res3

        # 4. Forget
        res4 = await agent.handle_query("forget about 5", user_id="test_user")
        assert res4 is not None
        assert "Cleared" in res4

    asyncio.run(_run())


def test_memory_api_endpoints():
    client = TestClient(app)

    # 1. Ingest
    res = client.post("/api/v1/memory/ingest", json={
        "user_query": "I am working on an AI memory system",
        "agent_response": "Sounds fantastic, boss.",
        "user_id": "test_user"
    })
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "accepted"
    job_id = data["job_id"]

    # 2. Status
    res_status = client.get(f"/api/v1/memory/jobs/{job_id}/status")
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "success"

    # 3. Retrieve
    res_ret = client.post("/api/v1/memory/retrieve", json={
        "query": "What system am I working on?",
        "user_id": "test_user"
    })
    assert res_ret.status_code == 200
    assert "data" in res_ret.json()

    # 4. Search
    res_search = client.post("/api/v1/memory/search", json={
        "query": "memory system",
        "top_k": 3
    })
    assert res_search.status_code == 200
    assert res_search.json()["status"] == "success"

    # 5. Facts CRUD
    res_fact = client.post("/api/v1/memory/facts", json={
        "fact": "Friday prefers dark mode UI",
        "category": "preferences",
        "user_id": "test_user"
    })
    assert res_fact.status_code == 200
    fact_id = res_fact.json()["fact_id"]

    res_list = client.get("/api/v1/memory/facts?user_id=test_user")
    assert res_list.status_code == 200
    assert res_list.json()["count"] >= 1

    res_del = client.delete(f"/api/v1/memory/facts/{fact_id}")
    assert res_del.status_code == 200
