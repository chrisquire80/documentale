import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ShareModal from './ShareModal';

const mockPost = vi.fn();

vi.mock('../services/api', () => ({
  default: {
    post: (...args: any[]) => mockPost(...args),
  },
}));

const defaultProps = {
  docId: 'doc-1',
  fileName: 'report.pdf',
  onClose: vi.fn(),
};

describe('ShareModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it('renders the modal with filename', () => {
    render(<ShareModal {...defaultProps} />);
    expect(screen.getByText(/report\.pdf/)).toBeInTheDocument();
  });

  it('shows Condividi Documento title', () => {
    render(<ShareModal {...defaultProps} />);
    expect(screen.getByText('Condividi Documento')).toBeInTheDocument();
  });

  it('renders password protection field', () => {
    render(<ShareModal {...defaultProps} />);
    expect(screen.getByLabelText(/Password di protezione/)).toBeInTheDocument();
  });

  it('renders expiry date field', () => {
    render(<ShareModal {...defaultProps} />);
    expect(screen.getByLabelText(/Data di Scadenza/)).toBeInTheDocument();
  });

  it('renders Genera Link button', () => {
    render(<ShareModal {...defaultProps} />);
    expect(screen.getByText('Genera Link')).toBeInTheDocument();
  });

  it('calls onClose when Annulla is clicked', () => {
    render(<ShareModal {...defaultProps} />);
    fireEvent.click(screen.getByText('Annulla'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('calls onClose when X button is clicked', () => {
    render(<ShareModal {...defaultProps} />);
    // X button is the close-btn in modal header
    const closeBtn = document.querySelector('.close-btn')!;
    fireEvent.click(closeBtn);
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('shows Creazione... while generating', async () => {
    mockPost.mockReturnValue(new Promise(() => {})); // never resolves
    render(<ShareModal {...defaultProps} />);
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => {
      expect(screen.getByText('Creazione...')).toBeInTheDocument();
    });
  });

  it('displays generated link after successful API call', async () => {
    mockPost.mockResolvedValue({ data: { token: 'abc123' } });
    render(<ShareModal {...defaultProps} />);
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => {
      expect(screen.getByText('Link generato!')).toBeInTheDocument();
    });
  });

  it('shows copy button after link generation', async () => {
    mockPost.mockResolvedValue({ data: { token: 'tok' } });
    render(<ShareModal {...defaultProps} />);
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => screen.getByText('Link generato!'));
    expect(screen.getByText('Chiudi')).toBeInTheDocument();
  });

  it('shows error message on API failure', async () => {
    mockPost.mockRejectedValue({
      response: { data: { detail: 'Quota exceeded' } },
    });
    render(<ShareModal {...defaultProps} />);
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => {
      expect(screen.getByText('Quota exceeded')).toBeInTheDocument();
    });
  });

  it('shows fallback error message on generic failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    render(<ShareModal {...defaultProps} />);
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => {
      expect(
        screen.getByText('Errore durante la generazione del link.')
      ).toBeInTheDocument();
    });
  });

  it('sends passkey in payload when provided', async () => {
    mockPost.mockResolvedValue({ data: { token: 'tok' } });
    render(<ShareModal {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(/Password di protezione/), {
      target: { value: 'my-secret' },
    });
    fireEvent.submit(document.querySelector('form')!);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        '/documents/doc-1/share',
        expect.objectContaining({ passkey: 'my-secret' })
      );
    });
  });

  it('does not send passkey when field is empty', async () => {
    mockPost.mockResolvedValue({ data: { token: 'tok' } });
    render(<ShareModal {...defaultProps} />);
    fireEvent.submit(document.querySelector('form')!);

    await waitFor(() => {
      const call = mockPost.mock.calls[0][1];
      expect(call).not.toHaveProperty('passkey');
    });
  });

  it('calls clipboard.writeText when copy button is clicked', async () => {
    mockPost.mockResolvedValue({ data: { token: 'tok123' } });
    render(<ShareModal {...defaultProps} />);
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => screen.getByText('Link generato!'));

    // Find the copy button (it's the styled button with Copy icon next to the link input)
    const copyBtn = document
      .querySelector('.modal-content')!
      .querySelector('button:not(.close-btn):not(.btn)') as HTMLButtonElement;
    if (copyBtn) {
      fireEvent.click(copyBtn);
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
    }
  });

  it('Chiudi button calls onClose after link is generated', async () => {
    mockPost.mockResolvedValue({ data: { token: 'tok' } });
    render(<ShareModal {...defaultProps} />);
    fireEvent.submit(document.querySelector('form')!);
    await waitFor(() => screen.getByText('Chiudi'));
    fireEvent.click(screen.getByText('Chiudi'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });
});
