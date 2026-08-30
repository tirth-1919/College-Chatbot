import React, { useState, useEffect } from 'react';
import {
  Archive, BookOpen, ChevronLeft, ChevronRight, CircleHelp, Image,
  LayoutDashboard, MessageSquare, Plus, Search, Settings, Sparkles, X, ShieldAlert,
  MoreVertical, Trash2, Edit2, LogOut, User as UserIcon, Pin, FolderKanban
} from 'lucide-react';
import { User } from '../types';
import { api } from '../services/api';

interface AppSidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onNewChat: () => void;
  onOpenConversation?: (conversationId: string) => void;
  currentUser?: User | null;
  onLogout?: () => void;
}

interface Conversation {
  id: string;
  title: string;
  mode: string;
  is_pinned: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

const navItems = [
  { id: 'chat', label: 'AI Assistant', icon: MessageSquare },
  { id: 'academic', label: 'Academic Data', icon: LayoutDashboard },
  { id: 'gallery', label: 'Official Gallery', icon: Image },
  { id: 'study', label: 'Study Center', icon: BookOpen },
  { id: 'library', label: 'Library', icon: Archive },
  { id: 'workspace', label: 'Projects', icon: FolderKanban }
];

export const AppSidebar: React.FC<AppSidebarProps> = ({
  activeTab, setActiveTab, collapsed, onToggle, mobileOpen, onCloseMobile, onNewChat, currentUser, onOpenConversation, onLogout
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState<string | null>(null);
  const isAdmin = currentUser?.roles?.some(r => ['ADMIN', 'SUPER_ADMIN'].includes(r));

  useEffect(() => {
    loadConversations();
  }, [searchTerm]);

  const loadConversations = async () => {
    if (!currentUser) return;

    setLoading(true);
    try {
      const data = await api.getConversations(searchTerm, 1, 25);
      setConversations(data.items);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConversationClick = (conv: Conversation) => {
    if (onOpenConversation) {
      onOpenConversation(conv.id);
    }
    setActiveTab('chat');
    onCloseMobile();
  };

  const handleRenameConversation = async (convId: string, newTitle: string) => {
    try {
      await api.renameConversation(convId, newTitle);
      loadConversations();
      setMenuOpen(null);
    } catch (error) {
      console.error('Failed to rename conversation:', error);
    }
  };

  const handleDeleteConversation = async (convId: string) => {
    if (!confirm('Delete this conversation? This action cannot be undone.')) return;

    try {
      await api.deleteConversation(convId);
      loadConversations();
      setMenuOpen(null);
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleArchiveConversation = async (convId: string) => {
    try {
      await api.archiveConversation(convId);
      loadConversations();
      setMenuOpen(null);
    } catch (error) {
      console.error('Failed to archive conversation:', error);
    }
  };

  const handlePinConversation = async (convId: string) => {
    try {
      await api.pinConversation(convId);
      loadConversations();
      setMenuOpen(null);
    } catch (error) {
      console.error('Failed to pin conversation:', error);
    }
  };

  const toggleMenu = (convId: string) => {
    setMenuOpen(menuOpen === convId ? null : convId);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return 'Previous 7 days';
    return date.toLocaleDateString();
  };

  // Group conversations by date
  const groupedConversations = conversations.reduce((groups, conv) => {
    const date = formatDate(conv.updated_at);
    if (!groups[date]) groups[date] = [];
    groups[date].push(conv);
    return groups;
  }, {} as Record<string, Conversation[]>);

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

          {!collapsed && currentUser && (
            <>
              <p className="sidebar-label history-label">Conversations</p>
              {loading ? (
                <div className="text-xs text-slate-500 py-2">Loading conversations...</div>
              ) : conversations.length === 0 ? (
                <div className="text-xs text-slate-500 py-2">No conversations yet</div>
              ) : (
                Object.entries(groupedConversations).map(([date, convs]) => (
                  <div key={date}>
                    <p className="text-xs text-slate-500 py-1">{date}</p>
                    {convs.map((conv) => (
                      <div key={conv.id} className="conversation-item-wrapper">
                        <button
                          className="conversation-item"
                          onClick={() => handleConversationClick(conv)}
                        >
                          {conv.is_pinned && <Pin size={12} className="text-ait-gold mr-1" />}
                          <span className="truncate">{conv.title}</span>
                        </button>
                        <button
                          className="conversation-menu-button"
                          onClick={() => toggleMenu(conv.id)}
                        >
                          <MoreVertical size={14} />
                        </button>
                        {menuOpen === conv.id && (
                          <div className="conversation-dropdown">
                            <button onClick={() => {
                              const newTitle = prompt('Enter new title:', conv.title);
                              if (newTitle) handleRenameConversation(conv.id, newTitle);
                            }}>
                              <Edit2 size={14} /> Rename
                            </button>
                            <button onClick={() => handlePinConversation(conv.id)}>
                              <Pin size={14} /> {conv.is_pinned ? 'Unpin' : 'Pin'}
                            </button>
                            <button onClick={() => handleArchiveConversation(conv.id)}>
                              <Archive size={14} /> {conv.is_archived ? 'Unarchive' : 'Archive'}
                            </button>
                            <button onClick={() => handleDeleteConversation(conv.id)} className="text-red-400">
                              <Trash2 size={14} /> Delete
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ))
              )}
            </>
          )}
        </nav>

        {currentUser && !collapsed && (
          <div className="sidebar-footer">
            <div className="user-profile">
              <div className="user-avatar">
                {currentUser.profile_image_url ? (
                  <img src={currentUser.profile_image_url} alt={currentUser.full_name} />
                ) : (
                  <UserIcon size={20} />
                )}
              </div>
              <div className="user-info">
                <div className="user-name">{currentUser.full_name}</div>
                <div className="user-email">{currentUser.email}</div>
              </div>
              <button className="user-menu-button" onClick={() => setMenuOpen('user')}>
                <MoreVertical size={14} />
              </button>
              {menuOpen === 'user' && (
                <div className="user-dropdown">
                  <button onClick={() => { setActiveTab('profile'); onCloseMobile(); }}>
                    <UserIcon size={14} /> Profile
                  </button>
                  <button onClick={() => { setActiveTab('settings'); onCloseMobile(); }}>
                    <Settings size={14} /> Settings
                  </button>
                  <button onClick={onLogout} className="text-red-400">
                    <LogOut size={14} /> Log out
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

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
