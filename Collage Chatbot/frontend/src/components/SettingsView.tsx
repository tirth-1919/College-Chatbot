import React, { useState } from 'react';
import { Settings, Bell, Lock, Eye, EyeOff, Save, RefreshCw } from 'lucide-react';

interface SettingsViewProps {
  currentUser?: any;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ currentUser }) => {
  const [showPassword, setShowPassword] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'Passwords do not match' });
      return;
    }

    if (newPassword.length < 8) {
      setMessage({ type: 'error', text: 'Password must be at least 8 characters' });
      return;
    }

    setSaving(true);
    try {
      // This would call the password reset API in production
      // For now, just show a success message
      setTimeout(() => {
        setMessage({ type: 'success', text: 'Password updated successfully' });
        setNewPassword('');
        setConfirmPassword('');
        setSaving(false);
      }, 1000);
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to update password' });
      setSaving(false);
    }
  };

  if (!currentUser) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Settings className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Authentication Required</h2>
          <p className="text-slate-400">Please sign in to access settings</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="glass-panel rounded-3xl p-8 border border-slate-700/80">
        <div className="flex items-center space-x-3 mb-8">
          <Settings className="w-6 h-6 text-ait-400" />
          <h2 className="text-2xl font-bold text-white">Account Settings</h2>
        </div>

        {message && (
          <div className={`mb-6 p-4 rounded-xl ${
            message.type === 'success' 
              ? 'bg-emerald-950/50 border border-emerald-500/30 text-emerald-300' 
              : 'bg-red-950/50 border border-red-500/30 text-red-300'
          }`}>
            {message.text}
          </div>
        )}

        <div className="space-y-6">
          {/* Account Information */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">Account Information</h3>
            <div className="space-y-3">
              <div className="p-4 bg-slate-900/50 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">Email</p>
                <p className="text-sm text-white">{currentUser.email}</p>
              </div>
              <div className="p-4 bg-slate-900/50 rounded-xl">
                <p className="text-xs text-slate-500 mb-1">Full Name</p>
                <p className="text-sm text-white">{currentUser.full_name}</p>
              </div>
              {currentUser.enrollment_number && (
                <div className="p-4 bg-slate-900/50 rounded-xl">
                  <p className="text-xs text-slate-500 mb-1">Enrollment Number</p>
                  <p className="text-sm text-white">{currentUser.enrollment_number}</p>
                </div>
              )}
            </div>
          </div>

          {/* Change Password */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">Change Password</h3>
            <form onSubmit={handlePasswordChange} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">New Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full glass-input pl-10 pr-10 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-ait-500"
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

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Confirm New Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full glass-input pl-10 pr-10 py-2.5 rounded-xl text-sm text-white focus:outline-none focus:border-ait-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={saving}
                className="w-full py-3 rounded-xl bg-ait-600 hover:bg-ait-500 text-white font-semibold text-sm shadow-xl shadow-ait-600/30 transition-all hover:scale-[1.02] flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Updating...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    <span>Update Password</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Notification Settings */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">Notification Preferences</h3>
            <div className="space-y-3">
              <label className="flex items-center justify-between p-4 bg-slate-900/50 rounded-xl cursor-pointer">
                <div className="flex items-center space-x-3">
                  <Bell className="w-5 h-5 text-slate-400" />
                  <div>
                    <p className="text-sm text-white">Email Notifications</p>
                    <p className="text-xs text-slate-500">Receive updates via email</p>
                  </div>
                </div>
                <input type="checkbox" className="w-5 h-5 rounded accent-ait-600" defaultChecked />
              </label>
              <label className="flex items-center justify-between p-4 bg-slate-900/50 rounded-xl cursor-pointer">
                <div className="flex items-center space-x-3">
                  <Bell className="w-5 h-5 text-slate-400" />
                  <div>
                    <p className="text-sm text-white">Academic Reminders</p>
                    <p className="text-xs text-slate-500">Exam and assignment reminders</p>
                  </div>
                </div>
                <input type="checkbox" className="w-5 h-5 rounded accent-ait-600" defaultChecked />
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};