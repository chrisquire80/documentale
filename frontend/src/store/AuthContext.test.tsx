import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import React from 'react';
import { AuthProvider, useAuth } from './AuthContext';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('../services/api', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}));

// WebSocket is mocked globally in setup.ts

const AuthConsumer: React.FC = () => {
  const { isAuthenticated, currentUser, isLoading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="is-authenticated">{String(isAuthenticated)}</span>
      <span data-testid="is-loading">{String(isLoading)}</span>
      <span data-testid="user-email">{currentUser?.email ?? 'none'}</span>
      <button onClick={() => login('token', 'refresh')}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(localStorage.getItem).mockReturnValue(null);
    // mockReset (vitest config) clears mock implementations between tests,
    // so re-establish the WebSocket mock here.
    (global.WebSocket as ReturnType<typeof vi.fn>).mockImplementation(() => ({
      close: vi.fn(),
      onmessage: null,
      onerror: null,
    }));
  });

  it('throws when useAuth is used outside AuthProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<AuthConsumer />)).toThrow(
      'useAuth must be used within an AuthProvider'
    );
    spy.mockRestore();
  });

  it('starts unauthenticated when no token in localStorage', async () => {
    render(<AuthProvider><AuthConsumer /></AuthProvider>);
    await waitFor(() => {
      expect(screen.getByTestId('is-loading').textContent).toBe('false');
    });
    expect(screen.getByTestId('is-authenticated').textContent).toBe('false');
    expect(screen.getByTestId('user-email').textContent).toBe('none');
  });

  it('fetches user when token exists in localStorage', async () => {
    vi.mocked(localStorage.getItem).mockReturnValue('existing-token');
    const mockUser = { id: 'u1', email: 'test@example.com', role: 'reader', is_active: true };
    mockGet.mockResolvedValue({ data: mockUser });

    render(<AuthProvider><AuthConsumer /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId('user-email').textContent).toBe('test@example.com');
    });
    expect(screen.getByTestId('is-authenticated').textContent).toBe('true');
  });

  it('sets unauthenticated when token fetch fails', async () => {
    vi.mocked(localStorage.getItem).mockReturnValue('bad-token');
    mockGet.mockRejectedValue(new Error('Unauthorized'));

    render(<AuthProvider><AuthConsumer /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId('is-loading').textContent).toBe('false');
    });
    expect(screen.getByTestId('is-authenticated').textContent).toBe('false');
    expect(screen.getByTestId('user-email').textContent).toBe('none');
  });

  it('login stores tokens in localStorage', async () => {
    const mockUser = { id: 'u1', email: 'login@example.com', role: 'reader', is_active: true };
    mockGet.mockResolvedValue({ data: mockUser });

    render(<AuthProvider><AuthConsumer /></AuthProvider>);
    await waitFor(() => screen.getByTestId('is-loading').textContent === 'false');

    await act(async () => {
      screen.getByText('Login').click();
    });

    expect(localStorage.setItem).toHaveBeenCalledWith('token', 'token');
    expect(localStorage.setItem).toHaveBeenCalledWith('refreshToken', 'refresh');
  });

  it('login sets authenticated state', async () => {
    const mockUser = { id: 'u1', email: 'login@example.com', role: 'reader', is_active: true };
    mockGet.mockResolvedValue({ data: mockUser });

    render(<AuthProvider><AuthConsumer /></AuthProvider>);
    await waitFor(() => screen.getByTestId('is-loading').textContent === 'false');

    await act(async () => {
      screen.getByText('Login').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated').textContent).toBe('true');
    });
  });

  it('logout clears tokens from localStorage', async () => {
    mockPost.mockResolvedValue({});

    render(<AuthProvider><AuthConsumer /></AuthProvider>);
    await waitFor(() => screen.getByTestId('is-loading').textContent === 'false');

    act(() => {
      screen.getByText('Logout').click();
    });

    expect(localStorage.removeItem).toHaveBeenCalledWith('token');
    expect(localStorage.removeItem).toHaveBeenCalledWith('refreshToken');
  });

  it('logout sets isAuthenticated to false', async () => {
    vi.mocked(localStorage.getItem).mockReturnValue('tok');
    const mockUser = { id: 'u1', email: 'user@test.com', role: 'reader', is_active: true };
    mockGet.mockResolvedValue({ data: mockUser });
    mockPost.mockResolvedValue({});

    render(<AuthProvider><AuthConsumer /></AuthProvider>);
    await waitFor(() => screen.getByTestId('is-authenticated').textContent === 'true');

    act(() => {
      screen.getByText('Logout').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated').textContent).toBe('false');
    });
  });
});
