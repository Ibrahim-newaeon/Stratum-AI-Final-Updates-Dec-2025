/**
 * Login Page Tests
 *
 * Tests for the Login view including form rendering, validation,
 * submit behavior, lockout state, and navigation links.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();
const mockLogin = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: '/login', state: null }),
  Link: ({ children, to }: any) => <a href={to}>{children}</a>,
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

vi.mock('@/components/common/SEO', () => ({
  SEO: () => null,
  pageSEO: { login: { title: 'Login' } },
}));

vi.mock('@/components/auth/AuthLeftPanel', () => ({
  default: () => <div data-testid="auth-left-panel" />,
}));

vi.mock('@/components/auth/authStyles', () => ({
  authStyles: '',
}));

// Mock heroicons
vi.mock('@heroicons/react/24/outline', () => ({
  ClockIcon: (props: any) => <svg data-testid="clock-icon" {...props} />,
  EnvelopeIcon: (props: any) => <svg data-testid="envelope-icon" {...props} />,
  ExclamationCircleIcon: (props: any) => <svg data-testid="error-icon" {...props} />,
  EyeIcon: (props: any) => <svg data-testid="eye-icon" {...props} />,
  EyeSlashIcon: (props: any) => <svg data-testid="eye-slash-icon" {...props} />,
  FingerPrintIcon: (props: any) => <svg data-testid="fingerprint-icon" {...props} />,
  LockClosedIcon: (props: any) => <svg data-testid="lock-icon" {...props} />,
}));

import Login from './Login';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders the login form with email and password fields', () => {
    render(<Login />);

    expect(screen.getByText('Dashboard Access')).toBeInTheDocument();
    expect(screen.getByLabelText(/neural identifier/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/security key/i)).toBeInTheDocument();
  });

  it('renders the submit button with default text', () => {
    render(<Login />);

    expect(screen.getByRole('button', { name: /initialize session/i })).toBeInTheDocument();
  });

  it('renders signup and forgot password links', () => {
    render(<Login />);

    const signupLink = screen.getByText('Request access');
    expect(signupLink).toBeInTheDocument();
    expect(signupLink.closest('a')).toHaveAttribute('href', '/signup');

    const resetLink = screen.getByText('Reset Key');
    expect(resetLink.closest('a')).toHaveAttribute('href', '/forgot-password');
  });

  it('renders footer links (Privacy, Terms, Support)', () => {
    render(<Login />);

    expect(screen.getByText('Privacy Protocol')).toBeInTheDocument();
    expect(screen.getByText('Legal Core')).toBeInTheDocument();
    expect(screen.getByText('Support')).toBeInTheDocument();
  });

  it('renders the remember me checkbox', () => {
    render(<Login />);

    const checkbox = screen.getByLabelText(/keep session active/i);
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).not.toBeChecked();
  });

  it('restores remember me state from localStorage', () => {
    localStorage.setItem('stratum_remember_me', 'true');
    render(<Login />);

    const checkbox = screen.getByLabelText(/keep session active/i);
    expect(checkbox).toBeChecked();
  });

  it('toggles password visibility when eye icon is clicked', () => {
    render(<Login />);

    const passwordInput = screen.getByLabelText(/security key/i);
    expect(passwordInput).toHaveAttribute('type', 'password');

    const toggleButton = screen.getByRole('button', { name: /show password/i });
    fireEvent.click(toggleButton);

    expect(passwordInput).toHaveAttribute('type', 'text');
  });

  it('updates email and password state on input', () => {
    render(<Login />);

    const emailInput = screen.getByLabelText(/neural identifier/i);
    const passwordInput = screen.getByLabelText(/security key/i);

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect(emailInput).toHaveValue('test@example.com');
    expect(passwordInput).toHaveValue('password123');
  });

  it('shows validation errors on empty form submission', async () => {
    render(<Login />);

    const submitButton = screen.getByRole('button', { name: /initialize session/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Please fill in all fields')).toBeInTheDocument();
    });

    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('calls login on valid form submission and navigates on success', async () => {
    mockLogin.mockResolvedValue({ success: true });

    render(<Login />);

    const emailInput = screen.getByLabelText(/neural identifier/i);
    const passwordInput = screen.getByLabelText(/security key/i);

    fireEvent.change(emailInput, { target: { value: 'user@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'securepass' } });

    const submitButton = screen.getByRole('button', { name: /initialize session/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('user@example.com', 'securepass');
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard/overview', { replace: true });
    });
  });

  it('displays error message when login fails', async () => {
    mockLogin.mockResolvedValue({ success: false, error: 'Invalid credentials' });

    render(<Login />);

    fireEvent.change(screen.getByLabelText(/neural identifier/i), {
      target: { value: 'bad@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/security key/i), {
      target: { value: 'wrongpass' },
    });

    fireEvent.click(screen.getByRole('button', { name: /initialize session/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('displays lockout state with countdown on HTTP 429', async () => {
    mockLogin.mockResolvedValue({ success: false, lockoutSeconds: 60 });

    render(<Login />);

    fireEvent.change(screen.getByLabelText(/neural identifier/i), {
      target: { value: 'user@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/security key/i), {
      target: { value: 'password' },
    });

    fireEvent.click(screen.getByRole('button', { name: /initialize session/i }));

    await waitFor(() => {
      expect(screen.getByText('Too many failed login attempts.')).toBeInTheDocument();
      expect(screen.getByText('Account temporarily locked')).toBeInTheDocument();
    });
  });

  it('disables submit button while loading', async () => {
    mockLogin.mockImplementation(() => new Promise(() => {})); // never resolves

    render(<Login />);

    fireEvent.change(screen.getByLabelText(/neural identifier/i), {
      target: { value: 'user@example.com' },
    });
    fireEvent.change(screen.getByLabelText(/security key/i), {
      target: { value: 'password' },
    });

    const submitButton = screen.getByRole('button', { name: /initialize session/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('INITIALIZING...')).toBeInTheDocument();
    });
  });

  it('shows inline email validation error on blur', () => {
    render(<Login />);

    const emailInput = screen.getByLabelText(/neural identifier/i);
    fireEvent.change(emailInput, { target: { value: 'notanemail' } });
    fireEvent.blur(emailInput);

    expect(screen.getByText('Please enter a valid email')).toBeInTheDocument();
  });

  it('renders the AuthLeftPanel component', () => {
    render(<Login />);

    expect(screen.getByTestId('auth-left-panel')).toBeInTheDocument();
  });
});
