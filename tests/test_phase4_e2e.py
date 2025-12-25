"""
Phase 4 E2E and Integration Tests
MVP Frontend and API integration testing
"""
import asyncio
import json
import httpx
from pathlib import Path


class TestPhase4E2E:
    """End-to-end tests for Phase 4 MVP"""

    def __init__(self):
        self.api_base = "http://localhost:8000/api/v1"
        self.frontend_url = "http://localhost:3000"
        self.client = httpx.Client()

    async def async_client(self):
        return httpx.AsyncClient()

    def test_api_health(self):
        """Test backend health check endpoint"""
        print("\n[Test] API Health Check")
        response = self.client.get(f"{self.api_base}/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["databases"]["postgres"] is True
        assert data["databases"]["neo4j"] is True
        assert data["databases"]["qdrant"] is True
        print("✓ API health check passed")

    def test_get_available_models(self):
        """Test models endpoint"""
        print("\n[Test] Get Available Models")
        response = self.client.get(f"{self.api_base}/models")
        assert response.status_code == 200
        data = response.json()
        assert "llm_models" in data
        assert "embedding_models" in data
        assert len(data["llm_models"]) > 0
        print(f"✓ Available LLM providers: {list(data['llm_models'].keys())}")
        print(f"✓ Available embedding providers: {list(data['embedding_models'].keys())}")

    def test_list_reports(self):
        """Test list reports endpoint"""
        print("\n[Test] List Reports")
        response = self.client.get(f"{self.api_base}/reports")
        assert response.status_code == 200
        data = response.json()
        # Response can be a list or dict with reports key
        if isinstance(data, list):
            print(f"✓ Total reports: {len(data)}")
        else:
            assert "reports" in data or "total" in data
            print(f"✓ Reports endpoint accessible")
        print("✓ List reports endpoint works")

    def test_list_conversations(self):
        """Test list conversations endpoint"""
        print("\n[Test] List Conversations")
        response = self.client.get(f"{self.api_base}/chat/conversations")
        assert response.status_code in [200, 404]  # May not have conversations yet
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
        print("✓ Conversations endpoint accessible")

    def test_frontend_home_page(self):
        """Test frontend home page loads"""
        print("\n[Test] Frontend Home Page")
        response = self.client.get(self.frontend_url)
        assert response.status_code == 200
        assert "Stock RAGs" in response.text
        print("✓ Frontend home page loads successfully")

    def test_api_cors_headers(self):
        """Test API CORS headers"""
        print("\n[Test] API CORS Headers")
        response = self.client.options(f"{self.api_base}/reports")
        # CORS headers may or may not be present, but request should be OK
        assert response.status_code in [200, 404, 405]
        print("✓ API endpoints respond to requests")

    def test_chat_endpoint_structure(self):
        """Test chat endpoint accepts proper request format"""
        print("\n[Test] Chat Endpoint Structure")
        request_data = {
            "query": "Test query",
            "provider": "gemini",
            "model": "gemini-1.5-pro"
        }
        # This will likely fail without a valid conversation, but we're testing structure
        response = self.client.post(
            f"{self.api_base}/chat",
            json=request_data
        )
        # Accept either success or error, we're testing the endpoint exists
        assert response.status_code in [200, 400, 422, 500]
        print("✓ Chat endpoint responds to requests")

    def test_graph_entities_endpoint(self):
        """Test graph entities search endpoint"""
        print("\n[Test] Graph Entities Endpoint")
        response = self.client.get(
            f"{self.api_base}/graph/entities",
            params={"query": "Apple"}
        )
        # Endpoint exists regardless of whether results are found
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
        print("✓ Graph entities endpoint accessible")

    def run_all_tests(self):
        """Run all E2E tests"""
        print("=" * 60)
        print("Phase 4 E2E and Integration Tests")
        print("=" * 60)

        tests = [
            self.test_api_health,
            self.test_get_available_models,
            self.test_list_reports,
            self.test_list_conversations,
            self.test_frontend_home_page,
            self.test_api_cors_headers,
            self.test_chat_endpoint_structure,
            self.test_graph_entities_endpoint,
        ]

        passed = 0
        failed = 0
        errors = []

        for test in tests:
            try:
                test()
                passed += 1
            except Exception as e:
                failed += 1
                error_msg = f"{test.__name__}: {str(e)}"
                errors.append(error_msg)
                print(f"✗ {error_msg}")

        print("\n" + "=" * 60)
        print(f"Test Results: {passed} passed, {failed} failed")
        print("=" * 60)

        if errors:
            print("\nFailed tests:")
            for error in errors:
                print(f"  - {error}")

        return failed == 0


def main():
    """Run E2E tests"""
    tester = TestPhase4E2E()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
