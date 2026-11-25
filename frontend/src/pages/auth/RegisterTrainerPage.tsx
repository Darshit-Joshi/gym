import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, CheckCircle2, AlertCircle, ArrowLeft } from 'lucide-react';
import { authService } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { Input } from '../../components/common/Input';
import { Button } from '../../components/common/Button';
import { ThemeToggle } from '../../components/common/ThemeToggle';

export const RegisterTrainerPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Form Fields - strictly empty without any default values
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Field validation errors
  const [errors, setErrors] = useState<{
    name?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
  }>({});

  useEffect(() => {
    // If already authenticated, go to dashboard
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const validateForm = (): boolean => {
    const newErrors: {
      name?: string;
      email?: string;
      password?: string;
      confirmPassword?: string;
    } = {};

    if (!name.trim()) {
      newErrors.name = 'Full name is required.';
    } else if (name.trim().length < 2) {
      newErrors.name = 'Name must be at least 2 characters long.';
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim()) {
      newErrors.email = 'Email address is required.';
    } else if (!emailRegex.test(email.trim())) {
      newErrors.email = 'Please enter a valid email address.';
    }

    if (!password) {
      newErrors.password = 'Password is required.';
    } else if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters long.';
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = 'Confirmation password is required.';
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await authService.registerTrainer({
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password,
        phone: phone.trim() || undefined,
      });

      // Securely store credentials and authenticate session
      localStorage.setItem('gym_auth_token', response.access_token);
      localStorage.setItem(
        'gym_user',
        JSON.stringify({
          id: response.user_id,
          role: response.role,
          name: response.name,
          trainer_id: response.trainer_id,
        })
      );

      setSuccessMessage('Trainer account created successfully! Initializing workspace...');

      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 1200);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setErrorMessage(detail || 'Failed to create trainer account. Please review your information.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-background)] text-[var(--color-text)] flex flex-col justify-center items-center p-4 relative isolate transition-colors">
      <div className="fx-ambient" aria-hidden="true" />
      <div className="absolute top-5 right-5 z-10">
        <ThemeToggle size="md" />
      </div>

      <div className="fx-page relative z-10 w-full max-w-lg">
        {/* App Branding */}
        <div className="text-center mb-4">
          <div className="inline-flex items-center justify-center p-1.5 rounded-full bg-white shadow-md border border-[var(--color-border)] hover:scale-105 transition-transform duration-200">
            <img
              src="/logo-circle.png"
              alt="1 ONE Country Fitness n spa"
              className="w-18 h-18 sm:w-22 sm:h-22 rounded-full object-contain"
            />
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-[var(--color-text)] tracking-wider mt-1.5">
            ONECOUNTRY <span className="text-[var(--color-primary)]">FITNESS</span>
          </h1>
          <p className="text-[11px] sm:text-xs text-[var(--color-text-secondary)] font-medium tracking-wide uppercase mt-0.5">
            Trainer Self-Registration & Management Platform
          </p>
        </div>

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 sm:p-8 shadow-[var(--shadow-dropdown)]">
          <div className="mb-6 flex items-start space-x-3">
            <div className="p-2.5 rounded-xl bg-[var(--color-primary)]/10 text-[var(--color-primary)] shrink-0 mt-0.5">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[var(--color-text)]">
                Create Trainer Account
              </h2>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Register as an independent trainer. You will manage your client roster, custom workouts, and session history privately.
              </p>
            </div>
          </div>

            {errorMessage && (
              <div className="mb-5 p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs font-medium flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {successMessage && (
              <div className="mb-5 p-3.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-xs font-medium flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{successMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Input
                  label="Full Name"
                  required
                  placeholder="e.g. Marcus Vance"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }));
                  }}
                  error={errors.name}
                />
                {errors.name && (
                  <p className="text-[11px] text-rose-500 mt-1 font-medium">{errors.name}</p>
                )}
              </div>

              <div>
                <Input
                  label="Email Address"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="name@onecountryfitness.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errors.email) setErrors((prev) => ({ ...prev, email: undefined }));
                  }}
                  error={errors.email}
                />
                {errors.email && (
                  <p className="text-[11px] text-rose-500 mt-1 font-medium">{errors.email}</p>
                )}
              </div>

              <div>
                <Input
                  label="Contact Phone Number (Optional)"
                  type="tel"
                  placeholder="+1 (555) 000-0000"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Input
                    label="Password"
                    isPassword
                    required
                    placeholder="Min. 8 characters"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }));
                    }}
                    error={errors.password}
                  />
                  {errors.password && (
                    <p className="text-[11px] text-rose-500 mt-1 font-medium">{errors.password}</p>
                  )}
                </div>

                <div>
                  <Input
                    label="Confirm Password"
                    isPassword
                    required
                    placeholder="Re-enter password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (errors.confirmPassword)
                        setErrors((prev) => ({ ...prev, confirmPassword: undefined }));
                    }}
                    error={errors.confirmPassword}
                  />
                  {errors.confirmPassword && (
                    <p className="text-[11px] text-rose-500 mt-1 font-medium">{errors.confirmPassword}</p>
                  )}
                </div>
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  isLoading={isLoading}
                  disabled={isLoading}
                  className="w-full"
                >
                  Create Trainer Account
                </Button>
              </div>
            </form>

            <div className="mt-5 pt-4 border-t border-[var(--color-border)] text-center">
              <Link
                to="/login"
                className="inline-flex items-center space-x-1.5 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Already registered? Return to Sign In</span>
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  };
