"""LLM connection test script for Gemini and LM Studio."""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.lmstudio import LMStudioProvider


async def test_gemini_llm():
    """Test Gemini LLM connection."""
    print("\n" + "="*60)
    print("Testing Gemini LLM")
    print("="*60)

    try:
        provider = GeminiProvider()

        # Health check
        print("\n1. Health Check...")
        is_healthy = await provider.health_check()
        print(f"   Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")

        if not is_healthy:
            print("   ⚠️  Gemini is not available. Check your API key and internet connection.")
            return False

        # Get available models
        print("\n2. Available Models...")
        models = await provider.get_available_models()
        for model in models:
            print(f"   - {model}")

        # Test generation
        print("\n3. Text Generation Test...")
        prompt = "삼성전자의 2024년 실적을 한 문장으로 요약해주세요."
        print(f"   Prompt: {prompt}")

        response = await provider.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=200
        )
        print(f"   Response: {response[:200]}...")

        # Test structured output
        print("\n4. Structured Output Test...")
        schema = {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "year": {"type": "integer"},
                "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]}
            },
            "required": ["company", "year", "sentiment"]
        }

        structured_response = await provider.generate_structured(
            prompt="삼성전자 2024년 실적 분석: 매출 증가, 영업이익 개선",
            schema=schema
        )
        print(f"   Structured Response: {structured_response}")

        print("\n✅ Gemini LLM test completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Gemini LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_gemini_embedding():
    """Test Gemini Embedding connection."""
    print("\n" + "="*60)
    print("Testing Gemini Embedding")
    print("="*60)
    print("   ⚠️  Gemini embedding not implemented in current version")
    return False


async def test_lmstudio_llm():
    """Test LM Studio LLM connection."""
    print("\n" + "="*60)
    print("Testing LM Studio LLM")
    print("="*60)

    try:
        provider = LMStudioProvider()

        # Health check
        print("\n1. Health Check...")
        is_healthy = await provider.health_check()
        print(f"   Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")

        if not is_healthy:
            print("   ⚠️  LM Studio is not available. Make sure LM Studio is running on localhost:1234")
            return False

        # Get available models
        print("\n2. Available Models...")
        models = await provider.get_available_models()
        if models:
            for model in models:
                print(f"   - {model}")
        else:
            print("   ⚠️  No models loaded in LM Studio")
            return False

        # Test generation
        print("\n3. Text Generation Test...")
        prompt = "삼성전자의 2024년 실적을 한 문장으로 요약해주세요."
        print(f"   Prompt: {prompt}")

        response = await provider.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=200
        )
        print(f"   Response: {response[:200]}...")

        # Test structured output (skip for LM Studio - not fully compatible)
        print("\n4. Structured Output Test...")
        print("   ⚠️  Skipped - LM Studio doesn't fully support OpenAI's response_format")

        print("\n✅ LM Studio LLM test completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ LM Studio LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_lmstudio_embedding():
    """Test LM Studio Embedding connection."""
    print("\n" + "="*60)
    print("Testing LM Studio Embedding")
    print("="*60)
    print("   ⚠️  Testing with LM Studio LLM provider (no separate embedding provider)")
    return False


async def main():
    """Run all LLM tests."""
    print("\n" + "="*60)
    print("LLM Connection Test Suite")
    print("="*60)

    results = {
        "Gemini LLM": await test_gemini_llm(),
        "Gemini Embedding": await test_gemini_embedding(),
        "LM Studio LLM": await test_lmstudio_llm(),
        "LM Studio Embedding": await test_lmstudio_embedding(),
    }

    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")

    return all(results.values())


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
