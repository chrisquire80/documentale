/**
 * k6 Performance Testing Script
 *
 * Run with:
 *   k6 run performance/k6-tests.js
 *
 * With specific options:
 *   k6 run -u 100 -d 30s performance/k6-tests.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiDuration = new Trend('api_duration');
const failedRequests = new Counter('failed_requests');
const activeUsers = new Gauge('active_users');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-token';

// Load test configuration
export const options = {
  stages: [
    { duration: '30s', target: 20 },   // Ramp up to 20 users
    { duration: '1m30s', target: 20 }, // Stay at 20 users
    { duration: '30s', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95th and 99th percentile
    http_req_failed: ['rate<0.1'],                   // 10% error rate
    errors: ['rate<0.05'],                           // Custom error rate
  },
};

// Setup function
export function setup() {
  console.log('Starting performance tests...');
  return {
    tokens: {
      user1: API_KEY,
    },
  };
}

// Main test function
export default function (data) {
  const token = data.tokens.user1;
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  // Update active users gauge
  activeUsers.add(__VU);

  group('Document API Performance', () => {
    // Test 1: List documents
    group('GET /documents', () => {
      const response = http.get(`${BASE_URL}/api/documents`, { headers });

      check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 500ms': (r) => r.timings.duration < 500,
        'has documents': (r) => r.json('total') !== undefined,
      });

      apiDuration.add(response.timings.duration, { name: 'list_documents' });
      errorRate.add(response.status !== 200);
    });

    sleep(1);

    // Test 2: Search documents
    group('GET /documents/search', () => {
      const params = {
        q: 'test',
        limit: 10,
        offset: 0,
      };

      const response = http.get(
        `${BASE_URL}/api/documents/search?${new URLSearchParams(params).toString()}`,
        { headers }
      );

      check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 1s': (r) => r.timings.duration < 1000,
        'has results': (r) => r.json('results') !== undefined,
      });

      apiDuration.add(response.timings.duration, { name: 'search' });
      errorRate.add(response.status !== 200);

      if (response.status !== 200) {
        failedRequests.add(1);
      }
    });

    sleep(1);

    // Test 3: Full-text search
    group('GET /documents/fts', () => {
      const params = {
        q: 'important document',
        limit: 20,
      };

      const response = http.get(
        `${BASE_URL}/api/documents/fts?${new URLSearchParams(params).toString()}`,
        { headers }
      );

      check(response, {
        'status is 200 or 400': (r) => r.status === 200 || r.status === 400,
        'response time < 2s': (r) => r.timings.duration < 2000,
      });

      apiDuration.add(response.timings.duration, { name: 'fts' });
    });

    sleep(1);

    // Test 4: Get document metadata
    group('GET /documents/:id', () => {
      const docId = Math.floor(Math.random() * 1000) + 1;
      const response = http.get(
        `${BASE_URL}/api/documents/${docId}`,
        { headers }
      );

      check(response, {
        'status is 200 or 404': (r) => r.status === 200 || r.status === 404,
        'response time < 300ms': (r) => r.timings.duration < 300,
      });

      apiDuration.add(response.timings.duration, { name: 'get_document' });
    });

    sleep(1);

    // Test 5: Document filtering
    group('GET /documents with filters', () => {
      const params = {
        status: 'active',
        limit: 50,
        sort: '-created_at',
      };

      const response = http.get(
        `${BASE_URL}/api/documents?${new URLSearchParams(params).toString()}`,
        { headers }
      );

      check(response, {
        'status is 200': (r) => r.status === 200,
        'response time < 750ms': (r) => r.timings.duration < 750,
      });

      apiDuration.add(response.timings.duration, { name: 'filter_documents' });
    });

    sleep(1);

    // Test 6: Cache performance
    group('Cache Hit Test', () => {
      const cacheId = 'test-cache-1';

      // First request (cache miss)
      const req1 = http.get(`${BASE_URL}/api/documents/cache/${cacheId}`, { headers });
      const duration1 = req1.timings.duration;

      sleep(0.5);

      // Second request (cache hit)
      const req2 = http.get(`${BASE_URL}/api/documents/cache/${cacheId}`, { headers });
      const duration2 = req2.timings.duration;

      check({}, {
        'cache hit is faster': () => duration2 < duration1,
        'cache miss < 1s': () => duration1 < 1000,
        'cache hit < 100ms': () => duration2 < 100,
      });

      apiDuration.add(duration2, { name: 'cache_hit' });
    });

    sleep(1);

    // Test 7: Pagination performance
    group('Pagination Performance', () => {
      for (let page = 1; page <= 3; page++) {
        const response = http.get(
          `${BASE_URL}/api/documents?page=${page}&limit=20`,
          { headers }
        );

        check(response, {
          'status is 200': (r) => r.status === 200,
          'response time < 500ms': (r) => r.timings.duration < 500,
        });

        apiDuration.add(response.timings.duration, { name: 'pagination' });
        sleep(0.5);
      }
    });
  });

  // Cleanup
  group('Analytics Check', () => {
    const response = http.get(
      `${BASE_URL}/api/analytics/stats`,
      { headers }
    );

    check(response, {
      'status is 200 or 401': (r) => r.status === 200 || r.status === 401,
    });
  });
}

// Teardown function
export function teardown() {
  console.log('Performance tests completed');
  console.log(`Total errors: ${failedRequests.value}`);
}

// Helper function to simulate real user behavior
function simulateUserBehavior() {
  const probability = Math.random();

  if (probability < 0.7) {
    // Most users search
    return 'search';
  } else if (probability < 0.9) {
    // Some filter
    return 'filter';
  } else {
    // Few browse
    return 'browse';
  }
}
