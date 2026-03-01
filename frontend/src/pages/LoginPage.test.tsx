import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from './LoginPage';

const mockPost = vi.fn();
const mockLogin = vi.fn();
const mockNavigate = vi.fn();

vi.mock('../services/api', () => ({
  default: {
    post: (...args: any[]) => mockPost(...args),
  },
}));

vi.mock('../store/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...(actual as object),
    useNavigate: () => mockNavigate,
  };
});

const renderLogin = () =>
  render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );

describe('LoginPage', () => {
  it('renders email, password fields and submit button', () => {
    renderLogin();
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Accedi' })).toBeInTheDocument();
  });

  it('updates email field on change', () => {
    renderLogin();
    const input = screen.getByPlaceholderText('Email');
    fireEvent.change(input, { target: { value: 'user@example.com' } });
    expect(input).toHaveValue('user@example.com');
  });

  it('updates password field on change', () => {
    renderLogin();
    const input = screen.getByPlaceholderText('Password');
    fireEvent.change(input, { target: { value: 'secret123' } });
    expect(input).toHaveValue('secret123');
  });

  it('calls api.post with credentials on submit', async () => {
    mockPost.mockResolvedValue({
      data: { access_token: 'tok', refresh_token: 'ref' },
    });
    renderLogin();

    fireEvent.change(screen.getByPlaceholderText('Email'), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'password123' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Accedi' }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/auth/login', {
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });

  it('calls login and navigates to / on success', async () => {
    mockPost.mockResolvedValue({
      data: { access_token: 'token123', refresh_token: 'refresh123' },
    });
    renderLogin();

    fireEvent.change(screen.getByPlaceholderText('Email'), {
      target: { value: 'test@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'pass' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Accedi' }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('token123', 'refresh123');
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('shows error message on login failure', async () => {
    mockPost.mockRejectedValue(new Error('Unauthorized'));
    renderLogin();

    fireEvent.change(screen.getByPlaceholderText('Email'), {
      target: { value: 'bad@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('Password'), {
      target: { value: 'wrongpass' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Accedi' }));

    await waitFor(() => {
      expect(screen.getByText('Credenziali non valide')).toBeInTheDocument();
    });
  });

  it('does not show error initially', () => {
    renderLogin();
    expect(screen.queryByText('Credenziali non valide')).not.toBeInTheDocument();
  });

  it('email input has correct type', () => {
    renderLogin();
    expect(screen.getByPlaceholderText('Email')).toHaveAttribute('type', 'email');
  });

  it('password input has correct type', () => {
    renderLogin();
    expect(screen.getByPlaceholderText('Password')).toHaveAttribute('type', 'password');
  });
});
