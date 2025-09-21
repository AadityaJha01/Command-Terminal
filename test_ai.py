#!/usr/bin/env python3
"""
Test script for AI command interpretation features
"""

from ai_service import ai_service

def test_ai_interpretation():
    """Test various natural language commands"""
    
    test_cases = [
        "create a folder called test 2",
        "list all files in detail",
        "go to the documents folder",
        "delete the test folder",
        "show me what's in file.txt",
        "what processes are running?",
        "show system information",
        "create directories for my project",
        "remove the old backup files",
        "navigate to the desktop"
    ]
    
    print("🤖 AI Command Interpretation Test")
    print("=" * 50)
    
    for i, natural_language in enumerate(test_cases, 1):
        print(f"\n{i}. Input: '{natural_language}'")
        
        result = ai_service.interpret_command(natural_language)
        
        print(f"   Command: {result['command']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Method: {result['method']}")
        
        if result['confidence'] > 0.5:
            print("   ✅ High confidence interpretation")
        else:
            print("   ⚠️  Low confidence - may need clarification")

def test_suggestions():
    """Test command suggestions"""
    
    print("\n\n🔍 Command Suggestions Test")
    print("=" * 50)
    
    test_inputs = [
        "",
        "cre",
        "list",
        "delete",
        "show",
        "go to",
        "system"
    ]
    
    for partial in test_inputs:
        suggestions = ai_service.get_suggestions(partial)
        print(f"\nInput: '{partial}'")
        print(f"Suggestions: {suggestions}")

if __name__ == "__main__":
    test_ai_interpretation()
    test_suggestions()
    
    print("\n\n✨ Test completed! The AI service is working.")
    print("Note: For full AI features, set OPENAI_API_KEY environment variable.")

