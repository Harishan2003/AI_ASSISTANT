# Tests for UserPersonaService and Care System
import os
import sys
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.user_persona_service import UserPersonaService
from app.core.agent_config import agent_config


def test_persona_system():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_persona.json"
        test_db = Path(tmpdir) / "test_persona.db"
        service = UserPersonaService(file_path=test_file, db_path=test_db)

        print("1. Testing initial profile loading...")
        profile = service.get_profile()
        assert profile["user_name"] == "Harishan"
        assert profile["wellbeing"]["current_mood"] == "focused"
        print("   Initial Profile OK:", profile["user_name"], profile["relationship_status"])

        print("\n2. Testing chat analysis (fatigue & mood)...")
        service.analyze_chat_turn("Friday I am feeling so tired and exhausted working on this", session_id="test_session")
        updated = service.get_profile()
        assert updated["wellbeing"]["current_mood"] == "tired"
        print("   Mood updated to:", updated["wellbeing"]["current_mood"])

        print("\n3. Testing inquiry / negation (should NOT remain tired)...")
        service.analyze_chat_turn("y agent always think i am Tired?", session_id="test_session")
        updated_neg = service.get_profile()
        assert updated_neg["wellbeing"]["current_mood"] == "focused"
        print("   Mood reset to focused after question/negation:", updated_neg["wellbeing"]["current_mood"])

        print("\n4. Testing project & preference extraction...")
        service.analyze_chat_turn("I am building an autonomous desktop AI assistant and I prefer dark theme UI", session_id="test_session")
        updated2 = service.get_profile()
        
        projects = [p["title"].lower() for p in updated2.get("active_projects_and_goals", [])]
        print("   Active Projects:", projects)
        print("   Learned habits:", updated2.get("learned_habits_and_preferences", []))
        print("   Insights count:", len(updated2.get("insights_history", [])))

        print("\n5. Testing Care & Wellbeing system prompt generation...")
        care_ctx = service.get_care_and_wellbeing_context()
        print("   Generated Care Context:\n", care_ctx)
        assert "FRIDAY PERSONAL COMPANION & DEEP CARE DIRECTIVE" in care_ctx

        print("\n6. Testing AgentConfig integration...")
        system_inst = agent_config.get_system_instruction(
            agent_name="Friday",
            user_name="Harishan",
            user_age="23",
            user_email="harishan@example.com",
            user_city="Colombo",
            language="english",
            live_web_context=""
        )
        assert "DEEP CARE DIRECTIVE" in system_inst
        assert "WARMTH, CARE & EMPATHY" in system_inst
        print("   AgentConfig System Instruction Verified Successfully!")
        print("\nALL USER PERSONA & CARING COMPANION TESTS PASSED!")


if __name__ == "__main__":
    test_persona_system()
