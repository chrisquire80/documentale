import { describe, it, expect, vi, beforeEach } from 'vitest';
import api from './api';

// No axios mock — we test the real interceptors on the real api instance.
// localStorage is already mocked globally in src/test/setup.ts.

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create axios instance with correct baseURL', () => {
    expect(api.defaults.baseURL).toBe('http://localhost:8000');
  });

  it('should add authorization header when token exists', () => {
    vi.mocked(localStorage.getItem).mockReturnValue('test-token-123');

    const config = { headers: {} as Record<string, string> };
    const result = (api.interceptors.request as any).handlers[0].fulfilled(config);

    expect(result.headers.Authorization).toBe('Bearer test-token-123');
  });

  it('should not add authorization header when token is missing', () => {
    vi.mocked(localStorage.getItem).mockReturnValue(null);

    const config = { headers: {} as Record<string, string> };
    const result = (api.interceptors.request as any).handlers[0].fulfilled(config);

    expect(result.headers.Authorization).toBeUndefined();
  });

  it('should have a response interceptor registered', () => {
    const handler = (api.interceptors.response as any).handlers[0];
    expect(handler).toBeDefined();
    expect(handler.rejected).toBeDefined();
  });

  it('should pass through successful responses unchanged', () => {
    const response = { data: { test: 'data' }, status: 200 };
    const handler = (api.interceptors.response as any).handlers[0];
    const result = handler.fulfilled(response);
    expect(result).toEqual(response);
  });

  it('should have a request interceptor registered', () => {
    const handler = (api.interceptors.request as any).handlers[0];
    expect(handler).toBeDefined();
    expect(handler.fulfilled).toBeDefined();
  });

  it('should return the same config object from request interceptor', () => {
    vi.mocked(localStorage.getItem).mockReturnValue('tok');
    const config = { headers: {} as Record<string, string>, url: '/test' };
    const result = (api.interceptors.request as any).handlers[0].fulfilled(config);
    expect(result.url).toBe('/test');
  });
});
