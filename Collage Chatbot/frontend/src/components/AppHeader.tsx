import React from 'react';
import { Menu, Moon, Sun, UserCircle, Volume2, LogOut, LogIn } from 'lucide-react';
import { User } from '../types';

interface AppHeaderProps {
  currentUser: User | null;
  activeTab: string;
  onOpenMenu: () => void;
  onOpenAuth: () => void;
  onLogout: () => void;
  onOpenVoiceModal: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  currentUser,
  activeTab,
  onOpenMenu,
  onOpenAuth,
  onLogout,
  onOpenVoiceModal,
  theme,
  onToggleTheme,
}) => (
  <header className="app-header">
    <div className="header-title-group">
      <button className="icon-button mobile-menu-button" aria-label="Open navigation" onClick={onOpenMenu}>
        <Menu size={20} />
      </button>
      <div>
        <span className="header-kicker">Ahmedabad Institute of Technology</span>
        <h1>
          {activeTab === 'chat'
            ? 'AIT AI Assistant'
            : activeTab === 'academic'
            ? 'Academic Master Data'
            : activeTab === 'gallery'
            ? 'Official Visual Gallery'
            : activeTab === 'study'
            ? 'Study & Exam Center'
            : 'Admin Control Center'}
        </h1>
      </div>
    </div>
    <div className="header-actions">
      <button className="header-action voice-action" onClick={onOpenVoiceModal} title="Launch Voice Assistant">
        <Volume2 size={17} />
        <span>Voice mode</span>
      </button>
      <button
        className="icon-button"
        onClick={onToggleTheme}
        aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>
      {currentUser ? (
        <div className="flex items-center space-x-2">
          <div className="profile-chip" title={currentUser.email}>
            <UserCircle size={20} />
            <span>{currentUser.full_name}</span>
          </div>
          <button
            onClick={onLogout}
            className="icon-button hover:text-red-400"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      ) : (
        <button className="header-action sign-in-action" onClick={onOpenAuth}>
          <LogIn size={15} />
          <span>Sign In</span>
        </button>
      )}
    </div>
  </header>
);
