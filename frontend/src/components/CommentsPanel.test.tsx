import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CommentsPanel from './CommentsPanel';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('../services/api', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}));

const defaultProps = {
  docId: 'doc-1',
  docTitle: 'Test Document',
  onClose: vi.fn(),
};

const sampleComments = [
  {
    id: 'c1',
    content: 'First comment',
    created_at: '2024-01-15T10:00:00Z',
    parent_id: null,
    user: { id: 'u1', email: 'alice@test.com' },
  },
  {
    id: 'c2',
    content: 'Reply to first',
    created_at: '2024-01-15T11:00:00Z',
    parent_id: 'c1',
    user: { id: 'u2', email: 'bob@test.com' },
  },
];

describe('CommentsPanel', () => {
  it('shows loading state while fetching', () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    render(<CommentsPanel {...defaultProps} />);
    expect(screen.getByText('Caricamento...')).toBeInTheDocument();
  });

  it('shows document title in header', async () => {
    mockGet.mockResolvedValue({ data: [] });
    render(<CommentsPanel {...defaultProps} docTitle="My Document" />);
    await screen.findByText(/Non ci sono ancora/);
    expect(screen.getByText('My Document')).toBeInTheDocument();
  });

  it('shows empty state when no comments', async () => {
    mockGet.mockResolvedValue({ data: [] });
    render(<CommentsPanel {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText(/Non ci sono ancora commenti/)).toBeInTheDocument();
    });
  });

  it('renders comment content and author', async () => {
    mockGet.mockResolvedValue({ data: sampleComments });
    render(<CommentsPanel {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('First comment')).toBeInTheDocument();
      expect(screen.getByText('alice@test.com')).toBeInTheDocument();
    });
  });

  it('renders threaded replies', async () => {
    mockGet.mockResolvedValue({ data: sampleComments });
    render(<CommentsPanel {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('Reply to first')).toBeInTheDocument();
      expect(screen.getByText('bob@test.com')).toBeInTheDocument();
    });
  });

  it('shows error message when fetch fails', async () => {
    mockGet.mockRejectedValue({
      response: { data: { detail: 'Server error' } },
    });
    render(<CommentsPanel {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument();
    });
  });

  it('shows fallback error when no detail in response', async () => {
    mockGet.mockRejectedValue(new Error('Network error'));
    render(<CommentsPanel {...defaultProps} />);
    await waitFor(() => {
      expect(
        screen.getByText('Impossibile caricare i commenti.')
      ).toBeInTheDocument();
    });
  });

  it('renders comment input textarea', async () => {
    mockGet.mockResolvedValue({ data: [] });
    render(<CommentsPanel {...defaultProps} />);
    // findByPlaceholderText = waitFor + getByPlaceholderText combined
    expect(await screen.findByPlaceholderText('Scrivi un commento...')).toBeInTheDocument();
  });

  it('submit button is disabled when textarea is empty', async () => {
    mockGet.mockResolvedValue({ data: [] });
    render(<CommentsPanel {...defaultProps} />);
    await screen.findByPlaceholderText('Scrivi un commento...');
    expect(document.querySelector('button[type="submit"]')).toBeDisabled();
  });

  it('posts comment and shows it in the list', async () => {
    mockGet.mockResolvedValue({ data: [] });
    const newComment = {
      id: 'c3',
      content: 'New comment',
      created_at: '2024-01-16T00:00:00Z',
      parent_id: null,
      user: { id: 'u1', email: 'alice@test.com' },
    };
    mockPost.mockResolvedValue({ data: newComment });

    render(<CommentsPanel {...defaultProps} />);
    await screen.findByPlaceholderText('Scrivi un commento...');

    fireEvent.change(screen.getByPlaceholderText('Scrivi un commento...'), {
      target: { value: 'New comment' },
    });
    fireEvent.submit(document.querySelector('form')!);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/documents/doc-1/comments', {
        content: 'New comment',
      });
      expect(screen.getByText('New comment')).toBeInTheDocument();
    });
  });

  it('clears textarea after successful post', async () => {
    mockGet.mockResolvedValue({ data: [] });
    mockPost.mockResolvedValue({
      data: {
        id: 'c3',
        content: 'Hello',
        created_at: '2024-01-16T00:00:00Z',
        parent_id: null,
        user: { id: 'u1', email: 'alice@test.com' },
      },
    });

    render(<CommentsPanel {...defaultProps} />);
    const textarea = await screen.findByPlaceholderText('Scrivi un commento...');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    fireEvent.submit(document.querySelector('form')!);

    await waitFor(() => {
      expect(textarea).toHaveValue('');
    });
  });

  it('shows reply indicator when Rispondi is clicked', async () => {
    mockGet.mockResolvedValue({ data: [sampleComments[0]] });
    render(<CommentsPanel {...defaultProps} />);
    await screen.findByText('Rispondi');

    fireEvent.click(screen.getByText('Rispondi'));
    expect(screen.getByText(/Stai rispondendo a/)).toBeInTheDocument();
  });

  it('posts reply with parent_id when replying', async () => {
    mockGet.mockResolvedValue({ data: [sampleComments[0]] });
    mockPost.mockResolvedValue({
      data: {
        id: 'c4',
        content: 'My reply',
        created_at: '2024-01-16T00:00:00Z',
        parent_id: 'c1',
        user: { id: 'u2', email: 'bob@test.com' },
      },
    });

    render(<CommentsPanel {...defaultProps} />);
    await screen.findByText('Rispondi');

    fireEvent.click(screen.getByText('Rispondi'));
    fireEvent.change(screen.getByPlaceholderText('Scrivi un commento...'), {
      target: { value: 'My reply' },
    });
    fireEvent.submit(document.querySelector('form')!);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/documents/doc-1/comments', {
        content: 'My reply',
        parent_id: 'c1',
      });
    });
  });

  it('cancels reply when Annulla is clicked', async () => {
    mockGet.mockResolvedValue({ data: [sampleComments[0]] });
    render(<CommentsPanel {...defaultProps} />);
    await screen.findByText('Rispondi');

    fireEvent.click(screen.getByText('Rispondi'));
    expect(screen.getByText(/Stai rispondendo a/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Annulla'));
    expect(screen.queryByText(/Stai rispondendo a/)).not.toBeInTheDocument();
  });
});
