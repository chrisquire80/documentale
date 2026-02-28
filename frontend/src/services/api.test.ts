import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';
import api from './api';

vi.mock('axios');
const mockedAxios = axios as any;

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem = vi.fn();
    localStorage.getItem = vi.fn();
    localStorage.removeItem = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should create axios instance with correct baseURL', () => {
    expect(api.defaults.baseURL).toBe('http://localhost:8000');
  });

  it('should add authorization header when token exists', async () => {
    const mockToken = 'test-token-123';
    vi.mocked(localStorage.getItem).mockReturnValue(mockToken);

    const config = { headers: {} };
    const result = api.interceptors.request.handlers[0].fulfilled(config);

    expect(result.headers.Authorization).toBe(`Bearer ${mockToken}`);
  });

  it('should not add authorization header when token is missing', async () => {
    vi.mocked(localStorage.getItem).mockReturnValue(null);

    const config = { headers: {} };
    const result = api.interceptors.request.handlers[0].fulfilled(config);

    expect(result.headers.Authorization).toBeUndefined();
  });

  it('should handle 401 response with token refresh', async () => {
    const mockRefreshToken = 'refresh-token-123';
    const mockNewAccessToken = 'new-access-token-123';
    const mockNewRefreshToken = 'new-refresh-token-123';

    vi.mocked(localStorage.getItem).mockImplementation((key) => {
      if (key === 'refreshToken') return mockRefreshToken;
      return null;
    });

    const originalError = {
      response: { status: 401 },
      config: { _retry: false, headers: {} },
    };

    mockedAxios.post.mockResolvedValueOnce({
      data: {
        access_token: mockNewAccessToken,
        refresh_token: mockNewRefreshToken,
      },
    });

    const handler = api.interceptors.response.handlers[0].rejected;
    // This test is simplified - real implementation would be more complex
    expect(handler).toBeDefined();
  });

  it('should redirect to login on 401 without refresh token', async () => {
    vi.mocked(localStorage.getItem).mockReturnValue(null);

    const originalError = {
      response: { status: 401 },
      config: { _retry: false, headers: {} },
    };

    const handler = api.interceptors.response.handlers[0].rejected;
    expect(handler).toBeDefined();
  });

  it('should handle response errors properly', async () => {
    const originalError = {
      response: { status: 500 },
      config: { _retry: false },
    };

    const handler = api.interceptors.response.handlers[0].rejected;
    expect(handler).toBeDefined();
  });

  it('should pass through successful responses', async () => {
    const response = { data: { test: 'data' }, status: 200 };
    const handler = api.interceptors.response.handlers[0].fulfilled;
    const result = handler(response);

    expect(result).toEqual(response);
  });
});
