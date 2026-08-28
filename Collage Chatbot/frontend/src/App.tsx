import React, { useState, useEffect } from 'react';
import { AppHeader } from './components/AppHeader';
import { AppSidebar } from './components/AppSidebar';
import { ChatView } from './components/ChatView';
import { AcademicView } from './components/AcademicView';
import { VisualGalleryView } from './components/VisualGalleryView';
import { StudyCenterView } from './components/StudyCenterView';
import { AdminView } from './components/AdminView';
import { VoiceModal } from './components/VoiceModal';
import { AuthModal } from './components/AuthModal';
import { User } from './types';
import { api, setAuthToken } from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('chat');
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isVoiceOpen, setIsVoiceOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  useEffect(() => {
    // Attempt auto-login with existing session or default to student
    api.getCurrentUser().then(user => {
      if (user) {
        setCurrentUser(user);
      }
    });
  }, []);

  const handleLogout = () => {
    setAuthToken(null);
    setCurrentUser(null);
    setActiveTab('chat');
  };

  useEffect(() => {
    const storedTheme = localStorage.getItem('ait-theme') as 'light' | 'dark' | null;
    if (storedTheme) setTheme(storedTheme);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('ait-theme', nextTheme);
  };

  const startNewChat = () => {
    setActiveTab('chat');
    setMobileSidebarOpen(false);
    window.dispatchEvent(new CustomEvent('ait:new-chat'));
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-ait-600 selection:text-white">
      <AppSidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(value => !value)}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
        onNewChat={startNewChat}
        currentUser={currentUser}
      />
      <div className="app-workspace">
        <AppHeader
          activeTab={activeTab}
          currentUser={currentUser}
          onOpenMenu={() => setMobileSidebarOpen(true)}
          onOpenAuth={() => setIsAuthOpen(true)}
          onLogout={handleLogout}
          onOpenVoiceModal={() => setIsVoiceOpen(true)}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
        <main className="app-main">
          {activeTab === 'chat' && (
            <ChatView onOpenVoiceModal={() => setIsVoiceOpen(true)} />
          )}
        {activeTab === 'academic' && <AcademicView />}
        {activeTab === 'gallery' && <VisualGalleryView />}
        {activeTab === 'study' && <StudyCenterView />}
        {activeTab === 'admin' && <AdminView />}
      </main>
      </div>

      {/* Interactive Voice Conversation Modal */}
      <VoiceModal
        isOpen={isVoiceOpen}
        onClose={() => setIsVoiceOpen(false)}
      />

      {/* Authentication Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onLoginSuccess={(user) => {
          setCurrentUser(user);
        }}
      />
    </div>
  );
};

export default App;
