import { describe, it, expect, vi } from 'vitest';

// Mock utility functions for testing
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
};

const formatDate = (date: Date | string): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('it-IT', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

describe('Utility Functions', () => {
  describe('formatFileSize', () => {
    it('should format zero bytes', () => {
      expect(formatFileSize(0)).toBe('0 Bytes');
    });

    it('should format bytes correctly', () => {
      expect(formatFileSize(1024)).toBe('1 KB');
      expect(formatFileSize(1024 * 1024)).toBe('1 MB');
      expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB');
    });

    it('should round to 2 decimal places', () => {
      expect(formatFileSize(1536)).toBe('1.5 KB');
      expect(formatFileSize(1024 * 1024 * 1.5)).toBe('1.5 MB');
    });

    it('should handle large files', () => {
      const largeFile = 1024 * 1024 * 1024 * 5; // 5 GB
      expect(formatFileSize(largeFile)).toBe('5 GB');
    });
  });

  describe('formatDate', () => {
    it('should format date object', () => {
      const date = new Date('2026-02-28');
      const result = formatDate(date);
      expect(result).toContain('28');
      expect(result).toContain('febbraio');
      expect(result).toContain('2026');
    });

    it('should format ISO date string', () => {
      const result = formatDate('2026-02-28');
      expect(result).toContain('28');
      expect(result).toContain('2026');
    });

    it('should use Italian locale', () => {
      const date = new Date('2026-01-15');
      const result = formatDate(date);
      expect(result).toContain('gennaio');
    });
  });

  describe('debounce', () => {
    it('should call function after delay', async () => {
      const mockFn = vi.fn();
      const debouncedFn = debounce(mockFn, 100);

      debouncedFn();
      debouncedFn();
      debouncedFn();

      expect(mockFn).not.toHaveBeenCalled();

      await new Promise(resolve => setTimeout(resolve, 150));

      expect(mockFn).toHaveBeenCalledTimes(1);
    });

    it('should reset timer on subsequent calls', async () => {
      const mockFn = vi.fn();
      const debouncedFn = debounce(mockFn, 100);

      debouncedFn('first');
      await new Promise(resolve => setTimeout(resolve, 50));
      debouncedFn('second');
      await new Promise(resolve => setTimeout(resolve, 150));

      expect(mockFn).toHaveBeenCalledTimes(1);
      expect(mockFn).toHaveBeenCalledWith('second');
    });

    it('should pass arguments correctly', async () => {
      const mockFn = vi.fn();
      const debouncedFn = debounce(mockFn, 100);

      debouncedFn('arg1', 'arg2', 'arg3');
      await new Promise(resolve => setTimeout(resolve, 150));

      expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2', 'arg3');
    });
  });

  describe('truncateText', () => {
    it('should not truncate short text', () => {
      expect(truncateText('Hello', 10)).toBe('Hello');
    });

    it('should truncate long text', () => {
      expect(truncateText('Hello World', 5)).toBe('Hello...');
    });

    it('should add ellipsis only when truncating', () => {
      expect(truncateText('Test', 4)).toBe('Test');
      expect(truncateText('Test', 3)).toBe('Tes...');
    });

    it('should handle exact length', () => {
      const text = 'Exactly10';
      expect(truncateText(text, 10)).toBe(text);
    });

    it('should handle very short max length', () => {
      expect(truncateText('Hello', 1)).toBe('H...');
    });

    it('should handle empty strings', () => {
      expect(truncateText('', 10)).toBe('');
    });
  });
});

// Add this import at the top if not already present
import { vi } from 'vitest';
