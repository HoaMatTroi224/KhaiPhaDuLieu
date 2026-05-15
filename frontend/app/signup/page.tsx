'use client';

import { BookOpenCheck, Eye, EyeOff, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { supabase } from '@/lib/supabase/client';

// Helper: evaluate password strength
const getPasswordStrength = (password: string) => {
  let strength = 0;
  const checks = {
    length: password.length >= 8,
    lowercase: /[a-z]/.test(password),
    uppercase: /[A-Z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  };

  strength = Object.values(checks).filter(Boolean).length;

  return {
    strength, // 0-5
    label: strength <= 2 ? 'Weak' : strength <= 4 ? 'Medium' : 'Strong',
    color: strength <= 2 ? 'bg-red-500' : strength <= 4 ? 'bg-yellow-500' : 'bg-green-500',
    checks,
  };
};

export default function SignupPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [warning, setWarning] = useState(''); // Cho warning như weakPassword
  const [loading, setLoading] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState(getPasswordStrength(''));

  // Update password strength
  useEffect(() => {
    setPasswordStrength(getPasswordStrength(password));
  }, [password]);

  // Helper: Validate email format
  const isValidEmail = (email: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  // Helper: Map Supabase error to message
  const getErrorMessage = (supabaseError: any): string => {
    const message = supabaseError?.message || '';
    return 'Can not signup. Please try again later!';
  };

  const handleSignup = async () => {
    setLoading(true);
    setError('');
    setWarning('');

    // Validate required fields
    if (!fullName || !email || !password) {
      setError('Please enter your information.');
      setLoading(false);
      return;
    }

    if (!isValidEmail(email)) {
      setError('Your email is invalid. Please check again!');
      setLoading(false);
      return;
    }

    if (password.length < 8) {
      setError('Password must contain at least 8 symbols. Please check again!');
      setLoading(false);
      return;
    }

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName },
          emailRedirectTo: `${window.location.origin}/login`,
        },
      });

      if (error) {
        setError(getErrorMessage(error));
        return;
      }

      alert('Signup successful. Please check and confirm your email!');
      
      window.location.href = '/login';
      
    } catch (err: any) {
      console.error('Unexpected signup error:', err);
      setError('Errors exist. Please try again later!');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignup = async () => {
    try {
      await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/dashboard`,
        },
      });
    } catch (err) {
      setError('Can not signup with Google. Please try again later!');
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

          {/* Tabs */}
          <div className="flex bg-gray-100 p-1 rounded-xl mb-8">
            <Link href="/login" className="flex-1 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 rounded-lg transition-all text-center">
              Log In
            </Link>
            <button className="flex-1 py-2 text-sm font-medium text-blue-700 bg-white rounded-lg shadow-sm transition-all">
              Sign Up
            </button>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Warning Alert (for weakPassword) */}
          {warning && (
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-xl flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-yellow-800">{warning}</p>
            </div>
          )}

          {/* Form */}
          <form 
            className="space-y-5"
            onSubmit={(e) => {
              e.preventDefault();
              handleSignup();
            }}
          >
            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your full name"
                className="w-full px-4 py-3 bg-gray-50 border-none rounded-xl text-sm focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all placeholder:text-gray-400"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@university.edu"
                className="w-full px-4 py-3 bg-gray-50 border-none rounded-xl text-sm focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all placeholder:text-gray-400"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  className="w-full px-4 py-3 bg-gray-50 border-none rounded-xl text-sm focus:ring-2 focus:ring-blue-600 focus:bg-white transition-all placeholder:text-gray-400"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  disabled={loading}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              {/* Password Strength Indicator */}
              {password.length > 0 && (
                <div className="mt-2 space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div 
                        className={`h-full ${passwordStrength.color} transition-all duration-300`}
                        style={{ width: `${(passwordStrength.strength / 5) * 100}%` }}
                      />
                    </div>
                    <span className={`text-xs font-medium ${
                      passwordStrength.strength <= 2 ? 'text-red-600' : 
                      passwordStrength.strength <= 4 ? 'text-yellow-600' : 'text-green-600'
                    }`}>
                      {passwordStrength.label}
                    </span>
                  </div>
                  
                  {/* Password requirements checklist */}
                  <div className="grid grid-cols-2 gap-1 text-xs text-gray-600">
                    <div className="flex items-center gap-1">
                      {passwordStrength.checks.length ? <CheckCircle2 className="w-3 h-3 text-green-500" /> : <XCircle className="w-3 h-3 text-gray-400" />}
                      <span>8+ ký tự</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {passwordStrength.checks.lowercase ? <CheckCircle2 className="w-3 h-3 text-green-500" /> : <XCircle className="w-3 h-3 text-gray-400" />}
                      <span>Chữ thường</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {passwordStrength.checks.uppercase ? <CheckCircle2 className="w-3 h-3 text-green-500" /> : <XCircle className="w-3 h-3 text-gray-400" />}
                      <span>Chữ hoa</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {passwordStrength.checks.number ? <CheckCircle2 className="w-3 h-3 text-green-500" /> : <XCircle className="w-3 h-3 text-gray-400" />}
                      <span>Số</span>
                    </div>
                    <div className="flex items-center gap-1 col-span-2">
                      {passwordStrength.checks.special ? <CheckCircle2 className="w-3 h-3 text-green-500" /> : <XCircle className="w-3 h-3 text-gray-400" />}
                      <span>Ký tự đặc biệt (!@#$...)</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold rounded-xl shadow-lg shadow-blue-200 transition-all transform active:scale-[0.98] disabled:cursor-not-allowed disabled:transform-none"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Đang tạo tài khoản...
                </span>
              ) : 'Create Account'}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-400">or</span>
            </div>
          </div>

          {/* Google Signup */}
          <button
            onClick={handleGoogleSignup}
            disabled={loading}
            className="w-full py-3 px-4 bg-white border border-gray-200 text-gray-700 font-medium rounded-xl hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-3 shadow-sm"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Continue with Google
          </button>

          {/* Footer */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link href="/login" className="font-semibold text-blue-700 hover:text-blue-800">
                Log in
              </Link>
            </p>
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