"""
Locust performance testing script for Documentale API

Run with:
    locust -f performance/locustfile.py --host=http://localhost:8000

Web UI:
    Open http://localhost:8089 in browser
"""

import logging
import random
from datetime import datetime

from locust import HttpUser, between, events, task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
API_TOKEN = "test-token"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


class DocumentAPIUser(HttpUser):
    """
    Simulates a user interacting with the Documentale API
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Called when a user starts"""
        logger.info(f"User {self.client.base_url} started")
        self.doc_ids = []
        self.search_queries = [
            "test",
            "document",
            "important",
            "pdf",
            "report",
        ]

    def on_stop(self):
        """Called when a user stops"""
        logger.info(f"User {self.client.base_url} stopped")

    # Task 1: List documents (20% weight)
    @task(2)
    def list_documents(self):
        """List documents with pagination"""
        page = random.randint(1, 5)
        limit = random.choice([10, 20, 50])

        with self.client.get(
            f"/api/documents?page={page}&limit={limit}",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.doc_ids = [doc["id"] for doc in data.get("data", [])]
                response.success()
            else:
                response.failure(f"Expected 200, got {response.status_code}")

    # Task 2: Search documents (35% weight)
    @task(3.5)
    def search_documents(self):
        """Search for documents"""
        query = random.choice(self.search_queries)

        with self.client.get(
            f"/api/documents/search?q={query}&limit=20",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 400:
                # Bad request is acceptable
                response.success()
            else:
                response.failure(f"Expected 200 or 400, got {response.status_code}")

    # Task 3: Full-text search (20% weight)
    @task(2)
    def fts_search(self):
        """Perform full-text search"""
        queries = [
            "keyword search",
            "text extraction",
            "document classification",
        ]
        query = random.choice(queries)

        with self.client.get(
            f"/api/documents/fts?q={query}&limit=20",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 400]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    # Task 4: Get document details (15% weight)
    @task(1.5)
    def get_document(self):
        """Get specific document metadata"""
        if not self.doc_ids:
            self.list_documents()

        if self.doc_ids:
            doc_id = random.choice(self.doc_ids)
        else:
            doc_id = random.randint(1, 100)

        with self.client.get(
            f"/api/documents/{doc_id}",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    # Task 5: Filter documents (10% weight)
    @task(1)
    def filter_documents(self):
        """Filter documents by status"""
        statuses = ["active", "archived", "pending"]
        status = random.choice(statuses)

        with self.client.get(
            f"/api/documents?status={status}&limit=50",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Expected 200, got {response.status_code}")

    # Task 6: Test cache performance (10% weight)
    @task(1)
    def test_cache(self):
        """Test cache hit/miss performance"""
        cache_id = "test-cache-1"

        with self.client.get(
            f"/api/documents/cache/{cache_id}",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Cache test failed: {response.status_code}")

    # Task 7: Analytics check (5% weight)
    @task(0.5)
    def check_analytics(self):
        """Check analytics endpoint"""
        with self.client.get(
            "/api/analytics/stats",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 401, 403]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class AdminUser(HttpUser):
    """
    Simulates an admin user with higher API usage
    """

    weight = 25  # This user type is 25% of total users
    wait_time = between(0.5, 2)  # Shorter wait time for admin

    def on_start(self):
        logger.info(f"Admin user {self.client.base_url} started")

    # Admin task 1: Bulk document operations
    @task(2)
    def bulk_list(self):
        """Admin: List with large limit"""
        with self.client.get(
            "/api/documents?limit=500&offset=0",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Bulk list failed: {response.status_code}")

    # Admin task 2: Export data
    @task(1)
    def export_data(self):
        """Admin: Export documents"""
        with self.client.get(
            "/api/documents/export?format=csv&limit=1000",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Export failed: {response.status_code}")

    # Admin task 3: System stats
    @task(1)
    def system_stats(self):
        """Admin: Get system statistics"""
        with self.client.get(
            "/api/admin/stats",
            headers=HEADERS,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"Stats failed: {response.status_code}")


# Event handlers for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    logger.info("=" * 60)
    logger.info("Load Test Started")
    logger.info(f"Host: {environment.host}")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    logger.info("=" * 60)
    logger.info("Load Test Stopped")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 60)

    # Print statistics
    logger.info("\nResponse Time Statistics:")
    for name, stats in environment.stats.entries.items():
        logger.info(
            f"  {name}: "
            f"avg={stats.avg_response_time:.0f}ms, "
            f"min={stats.min_response_time:.0f}ms, "
            f"max={stats.max_response_time:.0f}ms"
        )


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, **kwargs):
    """Custom handling of each request"""
    if response_time > 1000:
        logger.warning(f"Slow request: {name} took {response_time}ms")
