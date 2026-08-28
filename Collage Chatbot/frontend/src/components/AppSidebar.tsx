import React, { useState } from 'react';
import {
  Archive, BookOpen, ChevronLeft, ChevronRight, CircleHelp, Image,
  LayoutDashboard, MessageSquare, Plus, Search, Settings, Sparkles, X, ShieldAlert
} from 'lucide-react';
import { User } from '../types';

interface AppSidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onNewChat: () => void;
  currentUser?: User | null;
}

const navItems = [
  { id: 'chat', label: 'AI Assistant', icon: MessageSquare },
  { id: 'academic', label: 'Academic Data', icon: LayoutDashboard },
  { id: 'gallery', label: 'Official Gallery', icon: Image },
  { id: 'study', label: 'Study Center', icon: BookOpen },
];

export const AppSidebar: React.FC<AppSidebarProps> = ({
  activeTab, setActiveTab, collapsed, onToggle, mobileOpen, onCloseMobile, onNewChat, currentUser
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const isAdmin = currentUser?.roles?.some(r => ['ADMIN', 'SUPER_ADMIN'].includes(r));

  const conversations = [
    'Getting started with AIT',
    'BCA academic planning',
    'DBMS course syllabus',
    'Campus sports facilities'
  ].filter(c => c.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <>
      {mobileOpen && <button aria-label="Close navigation" className="sidebar-backdrop" onClick={onCloseMobile} />}
      <aside className={`app-sidebar ${collapsed ? 'is-collapsed' : ''} ${mobileOpen ? 'is-mobile-open' : ''}`}>
        <div className="sidebar-brand">
          <img src="/assets/ait/ait-logo.webp" alt="Ahmedabad Institute of Technology" />
          {!collapsed && <div><strong>AIT AI Assistant</strong><span>Ahmedabad Institute of Technology</span></div>}
          <button className="icon-button sidebar-close" aria-label="Close navigation" onClick={onCloseMobile}><X size={18} /></button>
        </div>
        <button className="new-chat-button" onClick={onNewChat} title="Start a new chat">
          <Plus size={18} /> {!collapsed && <span>New chat</span>}
        </button>
        {!collapsed && (
          <label className="sidebar-search">
            <Search size={16} />
            <input
              aria-label="Search conversations"
              placeholder="Search conversations"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </label>
        )}
        <nav className="sidebar-nav" aria-label="Main navigation">
          {!collapsed && <p className="sidebar-label">Workspace</p>}
          {navItems.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`sidebar-link ${activeTab === id ? 'is-active' : ''}`}
              onClick={() => { setActiveTab(id); onCloseMobile(); }}
              title={label}
            >
              <Icon size={18} /><span>{!collapsed && label}</span>
            </button>
          ))}

          {isAdmin && (
            <button
              className={`sidebar-link ${activeTab === 'admin' ? 'is-active text-amber-300' : 'text-amber-400 hover:text-amber-300'}`}
              onClick={() => { setActiveTab('admin'); onCloseMobile(); }}
              title="Admin Control Center"
            >
              <ShieldAlert size={18} /><span>{!collapsed && 'Admin Control'}</span>
            </button>
          )}

          {!collapsed && <p className="sidebar-label history-label">Conversations</p>}
          <button
            className="sidebar-link"
            title="Saved answers"
            onClick={() => { setActiveTab('chat'); onCloseMobile(); }}
          >
            <Archive size={18} /><span>{!collapsed && 'Saved answers'}</span>
          </button>
          {!collapsed && (
            <div className="conversation-list">
              {conversations.map((title, i) => (
                <button
                  key={i}
                  className="conversation-item"
                  onClick={() => {
                    setActiveTab('chat');
                    onCloseMobile();
                  }}
                >
                  <span className="conversation-dot" />
                  <span className="truncate">{title}</span>
                </button>
              ))}
            </div>
          )}
        </nav>
        <div className="sidebar-footer">
          <button className="sidebar-link" title="Help & Support" onClick={() => { setActiveTab('chat'); onCloseMobile(); }}>
            <CircleHelp size={18} /><span>{!collapsed && 'Help & support'}</span>
          </button>
          <button className="collapse-button" onClick={onToggle} aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}>
            {collapsed ? <ChevronRight size={18} /> : <><ChevronLeft size={18} /><span>Collapse sidebar</span></>}
          </button>
        </div>
      </aside>
    </>
  );
};
