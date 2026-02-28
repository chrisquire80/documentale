# Documentale - Test Coverage Analysis & Improvement Recommendations

## Executive Summary

This codebase has **very limited test coverage** with significant gaps across both backend and frontend. Current status:

- **Backend**: ~3,253 lines of code | ~346 lines of tests (~10% coverage ratio)
- **Frontend**: ~3,926 lines of TypeScript/React code | **0 tests (0% coverage)**
- **Test Files**: Only 3 test modules covering specific features
- **Testing Framework**: Backend uses pytest; Frontend has no testing setup

---

## Current Test Coverage (Backend Only)

### Existing Tests

#### 1. **test_cache.py** (128 lines)
- **Coverage**: Redis cache behavior
- **Tests**: 8 test cases
- **What's tested**:
  - Cache storage and retrieval
  - Cache misses
  - TTL (Time-To-Live) management
  - Cache invalidation on file upload
  - Cache key generation for different parameters
  - Deterministic cache key behavior

#### 2. **test_fts_search.py** (146 lines)
- **Coverage**: Full-Text Search (FTS) and pagination logic
- **Tests**: 11 test cases (2 marked as skipped integration tests)
- **What's tested**:
  - Pydantic schema validation (empty responses, field requirements)
  - Pagination logic (offset, total pages calculations)
  - FTS corpus builder (combining title, tags, metadata)
  - Integration tests (skipped - require PostgreSQL)

#### 3. **test_security.py** (46 lines)
- **Coverage**: JWT token creation
- **Tests**: 3 test cases
- **What's tested**:
  - Access token generation with default expiration
  - Custom token expiration
  - Token subject handling (string/integer conversion)

### Testing Infrastructure
- **Framework**: pytest with pytest-asyncio
- **Fake data**: fakeredis for Redis testing
- **Config**: pytest.ini with asyncio_mode = auto
- **Fixtures**: Minimal conftest.py with fake_redis fixture

---

## Critical Gaps in Test Coverage

### ⚠️ Backend API Endpoints (Mostly Untested)

#### **documents.py** (1,099 lines) - CRITICAL
- Document upload/retrieval
- Document search with caching
- Bulk operations (export, delete)
- Document versioning
- Document sharing/access control
- Background tasks (OCR, LLM tagging)
- Document metadata management
- Trash/soft delete functionality
- **Current tests**: None for endpoints
- **Risk Level**: 🔴 CRITICAL

#### **auth.py** (139 lines) - HIGH
- User login
- Token refresh
- Current user validation
- Token blacklisting (logout)
- **Current tests**: Only JWT creation tested
- **Missing**: Login flow, token validation, refresh token logic
- **Risk Level**: 🔴 HIGH

#### **admin.py** (327 lines) - HIGH
- User management (create, update, delete)
- Admin role verification
- Settings management
- User activity logs
- **Current tests**: None
- **Risk Level**: 🔴 HIGH

#### **comments.py** (95 lines) - MEDIUM
- Add/edit/delete comments on documents
- **Current tests**: None
- **Risk Level**: 🟡 MEDIUM

#### **shares.py** (129 lines) - MEDIUM
- Document sharing logic
- Share permission management
- **Current tests**: None (though documents.py tests indirectly cover some)
- **Risk Level**: 🟡 MEDIUM

#### **ai.py** (124 lines) - HIGH
- Gemini AI interactions
- Tagging and metadata extraction
- Embeddings generation
- **Current tests**: None
- **Risk Level**: 🔴 HIGH (external API dependency)

#### **ws.py** (87 lines) - MEDIUM
- WebSocket connections
- Real-time notifications
- **Current tests**: None
- **Risk Level**: 🟡 MEDIUM

### ⚠️ Backend Services (Untested)

#### **ocr.py** (135 lines)
- Text extraction from PDF, images, text files
- Multi-format support (PDF, TXT, IMG, DOCX)
- Error handling and fallbacks
- **Tests needed**: Unit tests for each format, error cases

#### **llm_metadata.py** (58 lines)
- Metadata extraction via LLM
- **Tests needed**: Happy path and error cases

#### **gemini_tagger.py** (67 lines)
- Automatic document tagging
- **Tests needed**: Tag extraction logic, validation

#### **embeddings.py** (54 lines)
- Vector embeddings generation
- **Tests needed**: Embedding creation, caching

#### **gemini.py** (48 lines)
- Google Generative AI integration
- **Tests needed**: API interactions

#### **trash_cleanup.py** (64 lines)
- Soft delete and permanent deletion
- TTL-based cleanup
- **Tests needed**: Cleanup logic, edge cases

#### **watcher.py** (172 lines)
- File system watching for document changes
- **Tests needed**: Event handling, file monitoring

### ⚠️ Backend Core Modules (Minimal Testing)

#### **security.py** (30 lines)
- Password hashing and verification
- Token creation/validation
- **Tests**: Only token creation tested
- **Missing**: Password hashing verification

#### **storage.py** (66 lines)
- File storage abstraction (local/cloud)
- File operations (save, retrieve, delete)
- **Tests**: None
- **Risk**: File handling, I/O operations

#### **rate_limit.py** (16 lines)
- Request rate limiting configuration
- **Tests**: None needed (configuration only)

#### **cache.py** (35 lines)
- Redis client initialization
- **Tests**: Partially covered by test_cache.py

#### **config.py** (25 lines)
- Environment configuration
- **Tests**: None (validation only)

### ⚠️ Frontend (React/TypeScript) - NO TESTS

The entire frontend codebase (**3,926 lines**) has **zero test coverage**:

#### **Components** (No tests)
- 20+ React components (Modals, Cards, Panels, Widgets)
- State management (AuthContext)
- No unit or integration tests

#### **Pages** (No tests)
- Dashboard, Login, Admin, Trash, PublicDownload pages
- Routing and page-level logic untested

#### **Services** (No tests)
- **api.ts**: API client and HTTP request handling
- No API response handling tests
- No error handling tests

#### **Testing Infrastructure Needed**
- No test framework installed (Vitest, Jest)
- No component testing library (React Testing Library)
- No mocking utilities
- No fixtures or test data

---

## Risk Assessment Matrix

| Module | Lines | Tests | Coverage % | Risk | Impact |
|--------|-------|-------|-----------|------|--------|
| documents.py | 1,099 | 0 | 0% | 🔴 CRITICAL | Core feature |
| admin.py | 327 | 0 | 0% | 🔴 HIGH | User mgmt, security |
| auth.py | 139 | 3 | ~2% | 🔴 HIGH | Authentication |
| ai.py | 124 | 0 | 0% | 🔴 HIGH | External API |
| watcher.py | 172 | 0 | 0% | 🟡 MEDIUM | Background task |
| comments.py | 95 | 0 | 0% | 🟡 MEDIUM | Comments |
| shares.py | 129 | 0 | 0% | 🟡 MEDIUM | Sharing |
| ws.py | 87 | 0 | 0% | 🟡 MEDIUM | Real-time |
| ocr.py | 135 | 0 | 0% | 🟡 MEDIUM | Text extraction |
| storage.py | 66 | 0 | 0% | 🟡 MEDIUM | File operations |
| **Frontend** | **3,926** | **0** | **0%** | 🔴 CRITICAL | All UI |
| **TOTAL** | **~7,000** | **346** | **~5%** | 🔴 CRITICAL | - |

---

## Recommended Priority Improvements

### Phase 1: High-Priority Backend Tests (Foundation)
**Estimated effort**: 2-3 weeks | **Impact**: Covers ~60% of critical paths

1. **Authentication & Authorization** (10-15 tests)
   - Login endpoint with valid/invalid credentials
   - Token refresh flow
   - Token expiration and blacklist
   - Access control (public/restricted documents)
   - Admin role checks

2. **Document CRUD Operations** (15-20 tests)
   - Create/upload documents
   - Retrieve documents (single, list, search)
   - Update document metadata
   - Delete documents (soft delete, permanent)
   - Version management

3. **File Upload & Storage** (8-12 tests)
   - File validation (type, size)
   - Storage layer operations
   - File retrieval
   - Error handling (corrupted files, disk full)

4. **Search & Pagination** (5-8 tests)
   - Search with filters
   - Pagination edge cases
   - FTS with special characters
   - Empty result sets

### Phase 2: API Integration Tests (Medium Priority)
**Estimated effort**: 2-3 weeks | **Impact**: Covers ~30% of remaining paths

5. **User Management (Admin)** (8-10 tests)
   - Create user
   - Update user roles
   - Disable/enable users
   - User list and search

6. **Document Sharing** (6-8 tests)
   - Share document with users
   - Permission verification
   - Share revocation
   - Public documents

7. **Comments & Collaboration** (5-6 tests)
   - Add comments
   - Edit comments
   - Delete comments
   - Comment retrieval

8. **Rate Limiting** (3-4 tests)
   - Request rate limits
   - IP-based blocking
   - Limit reset after TTL

### Phase 3: Service & Utility Tests (Medium Priority)
**Estimated effort**: 2 weeks | **Impact**: Covers ~20% of edge cases

9. **OCR Service** (10-15 tests)
   - Text extraction from PDFs
   - Image OCR (requires tesseract)
   - Text file reading
   - Error handling (corrupted files)
   - Format-specific edge cases

10. **LLM & AI Services** (8-12 tests)
    - Metadata extraction
    - Tagging logic
    - Embedding generation
    - API error handling (rate limits, timeouts)

11. **Trash & Cleanup** (5-8 tests)
    - Soft delete behavior
    - Cleanup scheduling
    - Permanent deletion
    - Recovery from trash

12. **Cache Invalidation** (4-6 tests)
    - Upload invalidates cache
    - Search uses cache properly
    - Cache TTL compliance

### Phase 4: Frontend Tests (Critical - Currently 0%)
**Estimated effort**: 3-4 weeks | **Impact**: Covers all UI

13. **Frontend Setup** (1 week)
    - Install testing framework (Vitest or Jest)
    - Install React Testing Library
    - Setup test utilities and fixtures
    - Configure coverage reporting

14. **Component Tests** (2 weeks)
    - Login/Auth components
    - Document list and card rendering
    - Modal dialogs (Upload, Preview, Share, etc.)
    - Filters and search UI
    - Error and loading states

15. **Page-level Tests** (1 week)
    - Dashboard page
    - Admin page
    - Trash page
    - URL routing and redirects

16. **API Service Tests** (1 week)
    - HTTP request mocking
    - Response handling
    - Error handling
    - Token management

---

## Quick Wins (Low Effort, High Value)

1. **Add password verification tests** (5 min)
   - Test `verify_password()` in security.py

2. **Add storage layer tests** (2-4 hours)
   - File save/retrieve/delete
   - Error cases

3. **Add config validation tests** (1-2 hours)
   - Environment variable loading
   - Config defaults

4. **Add rate limiting tests** (2-3 hours)
   - Endpoint limits
   - IP-based blocking

5. **Add WebSocket connection tests** (3-4 hours)
   - Connection establishment
   - Message delivery
   - Disconnect handling

---

## Testing Tools & Framework Recommendations

### Backend
- ✅ **Currently**: pytest + pytest-asyncio + fakeredis
- 📦 **Add**:
  - `pytest-cov` - Coverage reporting
  - `httpx` - Already in requirements (HTTP testing)
  - `freezegun` - Time mocking (for TTL tests)
  - `unittest.mock` - Better mocking (stdlib)

### Frontend
- 📦 **Install**:
  - `vitest` - Fast unit testing (recommended for Vite)
  - `@testing-library/react` - Component testing
  - `@testing-library/user-event` - User interaction simulation
  - `msw` (Mock Service Worker) - API mocking
  - `@vitest/ui` - Visual test reporting

---

## Implementation Strategy

1. **Start with backend core paths** (auth, documents, storage)
2. **Use test doubles** (mocks, fakes) to avoid external dependencies
3. **Separate unit and integration tests** (already configured in pytest.ini)
4. **Create test fixtures** for common data (documents, users)
5. **Frontend tests once backend stabilizes**
6. **Set up CI/CD coverage checks** (add pytest-cov to backend)

---

## Coverage Goals

| Phase | Target | Timeline |
|-------|--------|----------|
| **Current** | ~5% | Now |
| **Phase 1** | 30-40% (Backend core) | Week 1-3 |
| **Phase 2** | 50-60% (APIs) | Week 4-6 |
| **Phase 3** | 65-75% (Services) | Week 7-9 |
| **Phase 4** | 85%+ (Frontend added) | Week 10-13 |

---

## Metrics to Track

1. **Code Coverage %** → Target: 80%+
2. **Test Count** → Target: 100+ tests
3. **Critical Path Coverage** → Target: 100%
4. **API Endpoint Coverage** → Target: Every endpoint has ≥2 tests
5. **Error Handling Coverage** → Target: Every error path tested

---

## Conclusion

The codebase is at **significant risk** due to minimal test coverage. Recommended approach:

1. **Start immediately** with Phase 1 (auth, documents, storage)
2. **Automate coverage checks** in CI/CD pipeline
3. **Require tests for new features** (policy)
4. **Refactor for testability** where needed (dependency injection)
5. **Allocate 20-30% of sprint time** to test implementation

**Current state**: 🔴 **CRITICAL** - Heavy technical debt
**After Phase 1**: 🟡 **ACCEPTABLE** - Core paths covered
**After Phase 4**: 🟢 **HEALTHY** - Production-ready coverage
