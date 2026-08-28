import React from 'react';
import { User, UserRole } from '../types';
import { Bot, GraduationCap, Image, BookOpen, ShieldAlert, Sparkles, LogIn, LogOut, Volume2 } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  currentUser: User | null;
  onOpenAuth: () => void;
  onLogout: () => void;
  onOpenVoiceModal: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  currentUser,
  onOpenAuth,
  onLogout,
  onOpenVoiceModal,
}) => {
  const isAdmin = currentUser?.roles.some(r => ['ADMIN', 'SUPER_ADMIN'].includes(r));

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand / Logo */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('chat')}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-ait-600 to-blue-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <GraduationCap className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-heading font-extrabold text-lg text-white tracking-tight">AIT ASSISTANT</span>
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-ait-500/20 text-ait-200 border border-ait-500/30 rounded-full">AI-NATIVE</span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">Ahmedabad Institute of Technology</p>
          </div>
        </div>

        {/* Center: Navigation Links */}
        <nav className="hidden md:flex items-center space-x-1">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
              activeTab === 'chat'
                ? 'bg-ait-600 text-white shadow-md shadow-ait-600/30'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Bot className="w-4 h-4" />
            <span>AI Assistant</span>
          </button>

          <button
            onClick={() => setActiveTab('academic')}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
              activeTab === 'academic'
                ? 'bg-ait-600 text-white shadow-md shadow-ait-600/30'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <GraduationCap className="w-4 h-4" />
            <span>Academic Data</span>
          </button>

          <button
            onClick={() => setActiveTab('gallery')}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
              activeTab === 'gallery'
                ? 'bg-ait-600 text-white shadow-md shadow-ait-600/30'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Image className="w-4 h-4" />
            <span>Official Gallery</span>
          </button>

          <button
            onClick={() => setActiveTab('study')}
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
              activeTab === 'study'
                ? 'bg-ait-600 text-white shadow-md shadow-ait-600/30'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Study Center</span>
          </button>

          {isAdmin && (
            <button
              onClick={() => setActiveTab('admin')}
              className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
                activeTab === 'admin'
                  ? 'bg-amber-600 text-white shadow-md shadow-amber-600/30'
                  : 'text-amber-400 hover:text-amber-300 hover:bg-amber-950/40'
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Admin Panel</span>
            </button>
          )}
        </nav>

        {/* Right: Voice Chat & Auth */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={onOpenVoiceModal}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-blue-400 border border-blue-500/30 flex items-center space-x-1.5 text-xs font-semibold transition-all hover:scale-105"
            title="Launch Real-time Voice Chat"
          >
            <Volume2 className="w-4 h-4 animate-pulse text-blue-400" />
            <span className="hidden sm:inline">Voice Mode</span>
          </button>

          {currentUser ? (
            <div className="flex items-center space-x-3">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-semibold text-white">{currentUser.full_name}</div>
                <div className="text-[10px] text-ait-200 uppercase font-mono tracking-wider">
                  {currentUser.roles[0] || 'STUDENT'}
                </div>
              </div>
              <button
                onClick={onLogout}
                className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-950/30 transition-all"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="px-3.5 py-1.5 rounded-lg bg-ait-600 hover:bg-ait-500 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-md shadow-ait-600/30 transition-all hover:scale-105"
            >
              <LogIn className="w-4 h-4" />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
