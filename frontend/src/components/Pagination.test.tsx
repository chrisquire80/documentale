import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Pagination from './Pagination';

describe('Pagination Component', () => {
  let mockOnPageChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnPageChange = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render null when total is 0', () => {
    const { container } = render(
      <Pagination
        currentPage={1}
        totalPages={0}
        total={0}
        onPageChange={mockOnPageChange}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('should display document count', () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={3}
        total={25}
        onPageChange={mockOnPageChange}
      />
    );
    expect(screen.getByText('25 documenti')).toBeInTheDocument();
  });

  it('should display singular form for single document', () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={1}
        total={1}
        onPageChange={mockOnPageChange}
      />
    );
    expect(screen.getByText('1 documento')).toBeInTheDocument();
  });

  it('should disable previous button on first page', () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={3}
        total={25}
        onPageChange={mockOnPageChange}
      />
    );
    const prevButton = screen.getByLabelText('Pagina precedente');
    expect(prevButton).toBeDisabled();
  });

  it('should disable next button on last page', () => {
    render(
      <Pagination
        currentPage={3}
        totalPages={3}
        total={25}
        onPageChange={mockOnPageChange}
      />
    );
    const nextButton = screen.getByLabelText('Pagina successiva');
    expect(nextButton).toBeDisabled();
  });

  it('should call onPageChange with correct page number', () => {
    render(
      <Pagination
        currentPage={1}
        totalPages={3}
        total={25}
        onPageChange={mockOnPageChange}
      />
    );

    const page2Button = screen.getByRole('button', { name: '2' });
    fireEvent.click(page2Button);

    expect(mockOnPageChange).toHaveBeenCalledWith(2);
  });

  it('should handle previous button click', () => {
    render(
      <Pagination
        currentPage={2}
        totalPages={3}
        total={25}
        onPageChange={mockOnPageChange}
      />
    );

    const prevButton = screen.getByLabelText('Pagina precedente');
    fireEvent.click(prevButton);

    expect(mockOnPageChange).toHaveBeenCalledWith(1);
  });

  it('should handle next button click', () => {
    render(
      <Pagination
        currentPage={2}
        totalPages={3}
        total={25}
        onPageChange={mockOnPageChange}
      />
    );

    const nextButton = screen.getByLabelText('Pagina successiva');
    fireEvent.click(nextButton);

    expect(mockOnPageChange).toHaveBeenCalledWith(3);
  });

  it('should highlight current page', () => {
    render(
      <Pagination
        currentPage={2}
        totalPages={3}
        total={25}
        onPageChange={mockOnPageChange}
      />
    );

    const currentPageButton = screen.getByRole('button', { name: '2' });
    expect(currentPageButton).toHaveAttribute('aria-current', 'page');
    expect(currentPageButton).toHaveClass('pagination-btn--active');
  });

  it('should render all pages for small total', () => {
    render(
      <Pagination
        currentPage={3}
        totalPages={5}
        total={25}
        onPageChange={mockOnPageChange}
      />
    );

    for (let i = 1; i <= 5; i++) {
      expect(screen.getByRole('button', { name: i.toString() })).toBeInTheDocument();
    }
  });

  it('should render ellipsis for large page numbers', () => {
    render(
      <Pagination
        currentPage={5}
        totalPages={10}
        total={100}
        onPageChange={mockOnPageChange}
      />
    );

    const ellipsisElements = screen.getAllByText('…');
    expect(ellipsisElements.length).toBeGreaterThan(0);
  });
});
