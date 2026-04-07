import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  InlineLoader,
  LoadingSpinner,
  PageLoader,
  SkeletonCard,
  SkeletonTable,
} from './LoadingSpinner';

describe('LoadingSpinner', () => {
  it('should render with default props', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('should render with custom label', () => {
    render(<LoadingSpinner label="Please wait..." />);
    expect(screen.getByText('Please wait...')).toBeInTheDocument();
  });

  it('should render with empty label', () => {
    render(<LoadingSpinner label="" />);
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  });

  it('should have correct aria-label', () => {
    render(<LoadingSpinner label="Custom loading" />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Custom loading');
  });

  it('should apply custom className', () => {
    render(<LoadingSpinner className="custom-class" />);
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('custom-class');
  });
});

describe('PageLoader', () => {
  it('should render with page loading message', () => {
    render(<PageLoader />);
    expect(screen.getByText('Loading page...')).toBeInTheDocument();
  });

  it('should render a spinner element', () => {
    render(<PageLoader />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});

describe('InlineLoader', () => {
  it('should render loading text', () => {
    render(<InlineLoader />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = render(<InlineLoader className="custom-inline" />);
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('custom-inline');
  });
});

describe('SkeletonCard', () => {
  it('should render skeleton elements', () => {
    const { container } = render(<SkeletonCard />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(container.querySelectorAll('.bg-muted').length).toBeGreaterThan(0);
  });
});

describe('SkeletonTable', () => {
  it('should render default number of rows', () => {
    const { container } = render(<SkeletonTable />);
    const rows = container.querySelectorAll('.divide-y > div');
    expect(rows.length).toBe(5);
  });

  it('should render custom number of rows', () => {
    const { container } = render(<SkeletonTable rows={3} />);
    const rows = container.querySelectorAll('.divide-y > div');
    expect(rows.length).toBe(3);
  });
});
