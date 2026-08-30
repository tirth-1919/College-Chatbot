import React from 'react';
import { User, Mail, Calendar, ShieldCheck, LogOut } from 'lucide-react';

interface ProfileViewProps {
  currentUser?: any;
  onLogout?: () => void;
}

export const ProfileView: React.FC<ProfileViewProps> = ({ currentUser, onLogout }) => {
  if (!currentUser) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <ShieldCheck className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Authentication Required</h2>
          <p className="text-slate-400">Please sign in to view your profile</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="glass-panel rounded-3xl p-8 border border-slate-700/80">
        <div className="flex items-center space-x-6 mb-8">
          <div className="w-20 h-20 rounded-full bg-ait-600 flex items-center justify-center text-white text-2xl font-bold">
            {currentUser.profile_image_url ? (
              <img 
                src={currentUser.profile_image_url} 
                alt={currentUser.full_name} 
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              currentUser.full_name?.charAt(0).toUpperCase() || 'U'
            )}
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">{currentUser.full_name}</h2>
            <p className="text-slate-400">{currentUser.email}</p>
            <div className="flex space-x-2 mt-2">
              {currentUser.roles?.map((role: string) => (
                <span key={role} className="px-2 py-1 bg-ait-600/20 text-ait-400 rounded-full text-xs font-medium">
                  {role}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center space-x-3 p-4 bg-slate-900/50 rounded-xl">
            <Mail className="w-5 h-5 text-slate-400" />
            <div>
              <p className="text-xs text-slate-500">Email</p>
              <p className="text-sm text-white">{currentUser.email}</p>
            </div>
          </div>

          {currentUser.enrollment_number && (
            <div className="flex items-center space-x-3 p-4 bg-slate-900/50 rounded-xl">
              <User className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-xs text-slate-500">Enrollment Number</p>
                <p className="text-sm text-white">{currentUser.enrollment_number}</p>
              </div>
            </div>
          )}

          {currentUser.current_semester && (
            <div className="flex items-center space-x-3 p-4 bg-slate-900/50 rounded-xl">
              <ShieldCheck className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-xs text-slate-500">Current Semester</p>
                <p className="text-sm text-white">Semester {currentUser.current_semester}</p>
              </div>
            </div>
          )}

          {currentUser.created_at && (
            <div className="flex items-center space-x-3 p-4 bg-slate-900/50 rounded-xl">
              <Calendar className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-xs text-slate-500">Account Created</p>
                <p className="text-sm text-white">
                  {new Date(currentUser.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          )}

          {currentUser.is_verified !== undefined && (
            <div className="flex items-center space-x-3 p-4 bg-slate-900/50 rounded-xl">
              <ShieldCheck className={`w-5 h-5 ${currentUser.is_verified ? 'text-emerald-400' : 'text-amber-400'}`} />
              <div>
                <p className="text-xs text-slate-500">Account Status</p>
                <p className={`text-sm ${currentUser.is_verified ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {currentUser.is_verified ? 'Verified' : 'Pending Verification'}
                </p>
              </div>
            </div>
          )}
        </div>

        {onLogout && (
          <button
            onClick={onLogout}
            className="mt-8 w-full py-3 rounded-xl bg-red-600/20 hover:bg-red-600/30 text-red-400 font-semibold text-sm transition-all flex items-center justify-center space-x-2"
          >
            <LogOut className="w-4 h-4" />
            <span>Log Out</span>
          </button>
        )}
      </div>
    </div>
  );
};