// app/forgot-password/page.tsx
'use client';

import { BookOpenCheck, ArrowLeft, Mail, CheckCircle2 } from 'lucide-react';
import { useState } from 'react';
import Link from 'next/link';
import { supabase } from '@/lib/supabase/client';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      setError('Please enter your email address');
      return;
    }

    setLoading(true);
    setError('');

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/password/reset`,
    });

    setLoading(false);

    if (error) {
      setError(error.message);
    } else {
      setSent(true);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-blue-50/30 flex flex-col items-center justify-center p-4">
      {/* Main Card */}
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="p-8">
          {/* Header */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center mb-4 shadow-lg shadow-blue-200">
              <BookOpenCheck className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-blue-700">Lumen</h1>
            <p className="text-sm text-gray-500 mt-1">The Academic Curator</p>
          </div>

          {!sent ? (
            <>
              {/* Instructions */}
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-800 text-center">
                  Reset Your Password
                </h2>
                <p className="text-sm text-gray-500 mt-2 text-center leading-relaxed">
                  Enter your email address and we&apos;ll send you a link to reset your password.
                </p>
              </div>

              {/* Form */}
              <form onSubmit={handleResetPassword} className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                    Email Address
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        setError('');
                      }}
                      placeholder="researcher@university.edu"
                      className="w-full pl-4 pr-4 py-3 bg-gray-50 border-none rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all placeholder:text-gray-400"
                      autoFocus
                    />
                  </div>
                </div>

                {/* Error Message */}
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-200 transition-all transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                          fill="none"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      Sending...
                    </span>
                  ) : (
                    'Send Reset Link'
                  )}
                </button>
              </form>
            </>
          ) : (
            /* Success State */
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <CheckCircle2 className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-800">Check Your Email</h2>
              <p className="text-sm text-gray-500 mt-2 leading-relaxed">
                We&apos;ve sent a password reset link to{' '}
                <span className="font-medium text-gray-700">{email}</span>.
                Please check your inbox and follow the instructions.
              </p>
              <p className="text-xs text-gray-400 mt-3">
                Didn&apos;t receive the email? Check your spam folder or{' '}
                <button
                  onClick={() => setSent(false)}
                  className="text-blue-600 hover:text-blue-700 font-medium underline"
                >
                  try again
                </button>
              </p>
            </div>
          )}

          {/* Back to Login */}
          <div className="mt-6 text-center">
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-700 hover:text-blue-800 transition-colors"
            >
              <ArrowLeft size={16} />
              Back to Log In
            </Link>
          </div>
        </div>
      </div>

      {/* Bottom Footer */}
      <div className="mt-8 flex gap-6 text-xs text-gray-400 font-medium uppercase tracking-wider">
        <a href="#" className="hover:text-gray-600">Terms</a>
        <span>•</span>
        <a href="#" className="hover:text-gray-600">Privacy</a>
        <span>•</span>
        <a href="#" className="hover:text-gray-600">Security</a>
      </div>
      <div className="mt-2 text-xs text-gray-300">
        © 2026 LUMEN ACADEMIC CURATOR
      </div>
    </div>
  );
}