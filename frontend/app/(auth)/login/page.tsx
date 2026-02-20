/**
 * Login Page
 *
 * Handles user authentication via Google OAuth or email/password.
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Mail, Lock, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '@/lib/auth/auth-context';
import { useFormValidation, EMAIL_PATTERN } from '@/hooks/useFormValidation';

export default function LoginPage() {
  const router = useRouter();
  const { signInWithEmail, signInWithGoogle } = useAuth();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { getFieldProps, getFieldError, validateAll, formState } = useFormValidation({
    email: {
      rules: { required: true, pattern: EMAIL_PATTERN },
      errorMessage: 'Please enter a valid email address',
    },
    password: {
      rules: { required: true, minLength: 1 },
      errorMessage: 'Password is required',
    },
  });

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateAll()) return;

    setLoading(true);
    setError('');

    try {
      await signInWithEmail(formState.email.value, formState.password.value);
      router.push('/dashboard');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to sign in';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError('');

    try {
      await signInWithGoogle();
      router.push('/dashboard');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to sign in with Google';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-900">Welcome back</h2>
        <p className="text-sm text-slate-600 mt-1">Sign in to your account</p>
      </div>

      {error && (
        <div role="alert" className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Google Sign In */}
      <button
        onClick={handleGoogleLogin}
        disabled={loading}
        className="w-full flex items-center justify-center gap-3 px-4 py-3 border-2 border-slate-300 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          />
        </svg>
        {loading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <span className="font-medium text-slate-700">Continue with Google</span>
        )}
      </button>

      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-slate-300"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-2 bg-white text-slate-500">Or continue with email</span>
        </div>
      </div>

      {/* Email/Password Form */}
      <form onSubmit={handleEmailLogin} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
            Email
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 z-10" />
            <input
              id="email"
              type="email"
              {...getFieldProps('email')}
              aria-required="true"
              aria-invalid={!!getFieldError('email')}
              aria-describedby={getFieldError('email') ? 'email-error' : undefined}
              className={`w-full pl-10 pr-4 py-3 border rounded-lg transition-all ${
                getFieldError('email')
                  ? 'border-red-300 focus:ring-2 focus:ring-red-100 focus:border-red-500 bg-red-50'
                  : 'border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'
              }`}
              placeholder="you@law.com"
            />
          </div>
          {getFieldError('email') && (
            <p id="email-error" role="alert" className="mt-1.5 text-sm text-red-600 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
              {getFieldError('email')}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 z-10" />
            <input
              id="password"
              type="password"
              {...getFieldProps('password')}
              aria-required="true"
              aria-invalid={!!getFieldError('password')}
              aria-describedby={getFieldError('password') ? 'password-error' : undefined}
              className={`w-full pl-10 pr-4 py-3 border rounded-lg transition-all ${
                getFieldError('password')
                  ? 'border-red-300 focus:ring-2 focus:ring-red-100 focus:border-red-500 bg-red-50'
                  : 'border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'
              }`}
              placeholder="••••••••"
            />
          </div>
          {getFieldError('password') && (
            <p id="password-error" role="alert" className="mt-1.5 text-sm text-red-600 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
              {getFieldError('password')}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg font-medium hover:from-blue-700 hover:to-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Signing in...
            </>
          ) : (
            'Sign in'
          )}
        </button>
      </form>

      {/* Sign up link */}
      <p className="text-center text-sm text-slate-600">
        Don&apos;t have an account?{' '}
        <Link href="/signup" className="text-blue-600 hover:text-blue-700 font-medium">
          Sign up
        </Link>
      </p>
    </div>
  );
}
