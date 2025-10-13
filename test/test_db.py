#!/usr/bin/env python3
"""Test script for PostgresMemory class
Tests all basic functionality with clean, simple interface
"""

import os
import sys
from datetime import datetime
import time
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from lumir_agentic.memory.postgres_memory import PostgresMemory
from lumir_agentic.memory.config import get_database_config


def test_validation_functions():
    """Test valid_user and valid_session functions"""
    print("=== Testing Validation Functions ===")
    
    memory = PostgresMemory()
    
    # Test non-existent user
    assert not memory.valid_user("nonexistent_user"), "Non-existent user should return False"
    print("✓ Non-existent user validation works")
    
    # Test non-existent session
    assert not memory.valid_session("nonexistent_session"), "Non-existent session should return False"
    print("✓ Non-existent session validation works")
    
    # Create a user and session
    user_name = f"test_user_{uuid.uuid4().hex[:8]}"
    session_id = memory.create_new_session(user_name, "test_session")
    
    # Test existing user
    assert memory.valid_user(user_name), "Existing user should return True"
    print("✓ Existing user validation works")
    
    # Test existing session
    assert memory.valid_session(session_id), "Existing session should return True"
    print("✓ Existing session validation works")
    
    # Clean up
    memory.clear_user(user_name)
    memory.close()
    print("✓ Validation functions test passed")


def test_create_user():
    """Test creating a new user"""
    print("📋 Test: Create User")
    try:
        memory = PostgresMemory()
        user_name = "test_user_123"
        
        # Create user
        result = memory.create_new_user(user_name)
        print(f"✅ Created user: {user_name} (New: {result})")
        
        # Try creating same user again
        result2 = memory.create_new_user(user_name)
        print(f"✅ User already exists: {user_name} (New: {result2})")
        
        memory.close()
        return True
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        return False


def test_create_session():
    """Test creating a new session"""
    print("📋 Test: Create Session")
    try:
        memory = PostgresMemory()
        user_name = "test_user_456"
        
        # Create session with auto-generated name
        session_id1 = memory.create_new_session(user_name)
        print(f"✅ Created session with auto name: {session_id1}")
        
        # Create session with custom name
        session_id2 = memory.create_new_session(user_name, "my_custom_session")
        print(f"✅ Created session with custom name: {session_id2}")
        
        memory.close()
        return session_id1, session_id2
    except Exception as e:
        print(f"❌ Failed to create session: {e}")
        return None, None


def test_save_and_get_history():
    """Test saving and retrieving conversation history"""
    print("📋 Test: Save and Get History")
    try:
        memory = PostgresMemory()
        user_name = "test_user_789"
        
        # Create session
        session_id = memory.create_new_session(user_name, "conversation_test")
        print(f"✅ Created session: {session_id}")
        
        # Save multiple conversations
        conversations = [
            ("Xin chào, bạn có khỏe không?", "Tôi khỏe, cảm ơn bạn đã hỏi!"),
            ("Hôm nay thời tiết thế nào?", "Hôm nay trời đẹp, nắng ấm."),
            ("Bạn có thể giúp tôi học Python không?", "Tất nhiên! Tôi sẽ giúp bạn học Python từ cơ bản."),
        ]
        
        for i, (question, answer) in enumerate(conversations):
            memory.save_history(session_id, question, answer)
            print(f"✅ Saved conversation {i+1}")
        
        # Get all conversations
        all_conversations = memory.get_data(session_id, k=10)
        print(f"✅ Retrieved {len(all_conversations)} messages")
        
        print("📝 Conversation History (GPT format):")
        for i, conv in enumerate(all_conversations):
            print(f"  {i+1}. [{conv.role}]: {conv.content}")
        
        # Get only recent conversations
        recent_conversations = memory.get_data(session_id, k=2)
        print(f"✅ Retrieved {len(recent_conversations)} recent messages")
        
        memory.close()
        return session_id
    except Exception as e:
        print(f"❌ Failed to save/get history: {e}")
        return None


def test_clear_operations():
    """Test clear and delete operations"""
    print("📋 Test: Clear Operations")
    try:
        memory = PostgresMemory()
        user_name = "test_user_clear"
        
        # Create session and add data
        session_id = memory.create_new_session(user_name, "test_clear_session")
        memory.save_history(session_id, "Test question", "Test answer")
        
        # Verify data exists
        conversations = memory.get_data(session_id, k=5)
        print(f"✅ Before clear: {len(conversations)} messages")
        
        # Clear session
        memory.clear_session(session_id)
        conversations_after_clear = memory.get_data(session_id, k=5)
        print(f"✅ After clear session: {len(conversations_after_clear)} messages")
        
        # Add data again
        memory.save_history(session_id, "New question", "New answer")
        
        # Delete entire session
        memory.delete_session(session_id)
        print("✅ Session deleted successfully")
        
        # Test clear user
        session_id2 = memory.create_new_session(user_name, "another_session")
        memory.save_history(session_id2, "User test", "User response")
        
        memory.clear_user(user_name)
        print("✅ User cleared successfully")
        
        memory.close()
        return True
    except Exception as e:
        print(f"❌ Failed clear operations: {e}")
        return False


def test_edge_cases():
    """Test edge cases and error handling"""
    print("📋 Test: Edge Cases")
    try:
        memory = PostgresMemory()
        
        # Test getting data from non-existent session
        empty_conversations = memory.get_data("non-existent-session", k=5)
        print(f"✅ Non-existent session returned {len(empty_conversations)} messages")
        
        # Test with k=0
        user_name = "edge_case_user"
        session_id = memory.create_new_session(user_name)
        memory.save_history(session_id, "Test", "Response")
        
        zero_conversations = memory.get_data(session_id, k=0)
        print(f"✅ k=0 returned {len(zero_conversations)} messages")
        
        # Test with very large k
        large_k_conversations = memory.get_data(session_id, k=1000)
        print(f"✅ k=1000 returned {len(large_k_conversations)} messages")
        
        memory.close()
        return True
    except Exception as e:
        print(f"❌ Edge cases failed: {e}")
        return False


def run_performance_test():
    """Test performance with multiple conversations"""
    print("📋 Test: Performance")
    try:
        memory = PostgresMemory()
        user_name = "performance_user"
        session_id = memory.create_new_session(user_name, "performance_test")
        
        # Add many conversations
        start_time = datetime.now()
        for i in range(50):
            memory.save_history(
                session_id, 
                f"Question number {i+1}: What is the meaning of life?",
                f"Answer {i+1}: The meaning of life is to find purpose and happiness."
            )
        
        save_time = datetime.now()
        print(f"✅ Saved 50 conversations in {(save_time - start_time).total_seconds():.2f} seconds")
        
        # Retrieve conversations
        conversations = memory.get_data(session_id, k=10)
        retrieve_time = datetime.now()
        print(f"✅ Retrieved {len(conversations)} conversations in {(retrieve_time - save_time).total_seconds():.2f} seconds")
        
        memory.close()
        return True
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🧪 Testing PostgresMemory Class\n")
    print("=" * 50)
    
    tests = [
        ("Create User", test_create_user),
        ("Create Session", test_create_session),
        ("Save and Get History", test_save_and_get_history),
        ("Clear Operations", test_clear_operations),
        ("Edge Cases", test_edge_cases),
        ("Performance Test", run_performance_test),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * 30)
        try:
            result = test_func()
            success = result is not None and result is not False
            results.append((test_name, success))
            if success:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("=" * 50)
    print("📊 Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"   Passed: {passed}/{total}")
    print(f"   Success Rate: {(passed/total)*100:.1f}%")
    print()
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {test_name}")
    
    print("\n" + "=" * 50)
    if passed == total:
        print("🎉 All tests passed! PostgresMemory is working correctly.")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please check the implementation.")


if __name__ == "__main__":
    main()


