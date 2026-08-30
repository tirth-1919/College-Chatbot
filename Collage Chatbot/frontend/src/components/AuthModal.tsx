import React, { useState } from 'react';
import { api } from '../services/api';
import { User } from '../types';
import { X, Lock, Mail, UserCheck, ShieldCheck, UserPlus, Chrome, ArrowLeft, Eye, EyeOff } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoginSuccess: (user: User) => void;
}

type AuthView = 'login' | 'signup' | 'forgot-password' | 'reset-password';

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onLoginSuccess }) => {
  const [view, setView] = useState<AuthView>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.login(email, password);
      onLoginSuccess(res.user);
      onClose();
    } catch (err: any) {
      const msg = err?.message || '';
      if (msg.toLowerCase().includes('incorrect') || msg.toLowerCase().includes('invalid') || msg.toLowerCase().includes('password')) {
        setError('Invalid email or password.');
      } else {
        setError('Unable to sign in right now. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    // Password validation
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    if (!/[A-Z]/.test(password)) {
      setError('Password must contain at least one uppercase letter');
      return;
    }
    if (!/[a-z]/.test(password)) {
      setError('Password must contain at least one lowercase letter');
      return;
    }
    if (!/[0-9]/.test(password)) {
      setError('Password must contain at least one digit');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const res = await api.enhancedRegister({
        full_name: fullName,
        email,
        password,
        confirm_password: confirmPassword,
        role: 'STUDENT'
      });
      onLoginSuccess(res.user);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);
    try {
      const res = await api.forgotPassword(email);
      setMessage(res.message);
    } catch (err: any) {
      setError(err?.message || 'Failed to send reset instructions');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    try {
      // For now, just show that Google OAuth would be triggered
      // In production, this would redirect to Google OAuth flow
      setError('Google OAuth requires configuration. Please use email/password for now.');
    } catch (err: any) {
      setError('Google login failed. Please try again.');
    }
  };

  const resetForm = () => {
    setEmail('');
    setPassword('');
    setFullName('');
    setConfirmPassword('');
    setError(null);
    setMessage(null);
  };

  const switchView = (newView: AuthView) => {
    resetForm();
    setView(newView);
  };

  const renderAuthTabs = () => (
    <div className="flex mb-6 bg-slate-800/50 rounded-xl p-1">
      <button
        type="button"
        onClick={() => switchView('login')}
        className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${
          view === 'login' 
            ? 'bg-[#0066cc] text-white' 
            : 'text-slate-400 hover:text-slate-200'
        }`}
      >
        Log in
      </button>
      <button
        type="button"
        onClick={() => switchView('signup')}
        className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${
          view === 'signup' 
            ? 'bg-[#0066cc] text-white' 
            : 'text-slate-400 hover:text-slate-200'
        }`}
      >
        Sign up
      </button>
    </div>
  );

  const renderLogin = () => (
    <form onSubmit={handleLogin} className="space-y-4">
      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">Email address</label>
        <div className="relative">
          <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
          <input
            type="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full glass-input pl-10 pr-3 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-[#0066cc]"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">Password</label>
        <div className="relative">
          <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
          <input
            type={showPassword ? 'text' : 'password'}
            placeholder="•••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full glass-input pl-10 pr-10 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-[#0066cc]"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="text-right">
        <button
          type="button"
          onClick={() => switchView('forgot-password')}
          className="text-xs text-[#0088ff] hover:text-[#00a0ff] transition-colors"
        >
          Forgot password?
        </button>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 rounded-xl bg-[#0066cc] hover:bg-[#0052a3] text-white font-semibold text-sm shadow-xl shadow-[#0066cc]/30 transition-all hover:scale-[1.02] flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <UserCheck className="w-4 h-4" />
        <span>{loading ? 'Continuing...' : 'Continue'}</span>
      </button>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-slate-700"></div>
        </div>
        <div className="relative flex justify-center text-xs">
          <span className="px-2 bg-slate-900 text-slate-400">OR</span>
        </div>
      </div>

      <button
        type="button"
        onClick={handleGoogleLogin}
        className="w-full py-3 rounded-xl bg-white hover:bg-slate-100 text-slate-900 font-semibold text-sm transition-all hover:scale-[1.02] flex items-center justify-center space-x-2"
      >
        <Chrome className="w-4 h-4" />
        <span>Continue with Google</span>
      </button>
    </form>
  );

  const renderSignup = () => (
    <form onSubmit={handleSignup} className="space-y-4">
      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">Full name</label>
        <input
          type="text"
          placeholder="John Doe"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
          className="w-full glass-input px-3 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-[#0066cc]"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">Email address</label>
        <div className="relative">
          <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
          <input
            type="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full glass-input pl-10 pr-3 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-[#0066cc]"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">Password</label>
        <div className="relative">
          <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
          <input
            type={showPassword ? 'text' : 'password'}
            placeholder="•••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full glass-input pl-10 pr-10 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-[#0066cc]"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        <div className="mt-1 text-[10px] text-slate-500">
          Must be 8+ chars with uppercase, lowercase, and number
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">Confirm password</label>
        <div className="relative">
          <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
          <input
            type={showConfirmPassword ? 'text' : 'password'}
            placeholder="•••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            className="w-full glass-input pl-10 pr-10 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-[#0066cc]"
          />
          <button
            type="button"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
          >
            {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 rounded-xl bg-[#0066cc] hover:bg-[#0052a3] text-white font-semibold text-sm shadow-xl shadow-[#0066cc]/30 transition-all hover:scale-[1.02] flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <UserPlus className="w-4 h-4" />
        <span>{loading ? 'Creating account...' : 'Continue'}</span>
      </button>
    </form>
  );

  const renderForgotPassword = () => (
    <form onSubmit={handleForgotPassword} className="space-y-4">
      <button
        type="button"
        onClick={() => switchView('login')}
        className="flex items-center text-xs text-slate-400 hover:text-slate-200 transition-colors mb-2"
      >
        <ArrowLeft className="w-3 h-3 mr-1" />
        Back to login
      </button>

      <div className="text-center mb-4">
        <p className="text-sm text-slate-300">
          Enter your email and we'll send you instructions to reset your password.
        </p>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">Email address</label>
        <div className="relative">
          <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
          <input
            type="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full glass-input pl-10 pr-3 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-[#0066cc]"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 rounded-xl bg-[#0066cc] hover:bg-[#0052a3] text-white font-semibold text-sm shadow-xl shadow-[#0066cc]/30 transition-all hover:scale-[1.02] flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Mail className="w-4 h-4" />
        <span>{loading ? 'Sending...' : 'Send Reset Link'}</span>
      </button>
    </form>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="relative w-full max-w-md glass-panel rounded-3xl p-6 sm:p-8 border border-slate-700/80 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center mb-4">
          <h3 className="font-heading text-2xl font-bold text-white mb-1">
            {view === 'forgot-password' ? 'Reset Password' : 'Welcome to AIT Assistant'}
          </h3>
          <p className="text-sm text-slate-400">
            {view === 'login' ? 'Log in to continue' : 
             view === 'signup' ? 'Create your account' : 
             'Recover your account access'}
          </p>
        </div>

        {view !== 'forgot-password' && renderAuthTabs()}

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-950/50 border border-red-500/30 text-xs text-red-300">
            {error}
          </div>
        )}

        {message && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-950/50 border border-emerald-500/30 text-xs text-emerald-300">
            {message}
          </div>
        )}

        {view === 'login' && renderLogin()}
        {view === 'signup' && renderSignup()}
        {view === 'forgot-password' && renderForgotPassword()}
      </div>
    </div>
  );
};
