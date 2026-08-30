import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, ImageCard } from '../types';
import { api } from '../services/api';
import { MarkdownRenderer } from './MarkdownRenderer';
import {
  Send, Sparkles, Volume2, Play, Pause, ThumbsUp, ThumbsDown,
  Copy, Check, Bookmark, RefreshCw, AlertCircle, CheckCircle2, ShieldCheck, Mic,
  Plus, Brain, Globe2, GraduationCap, X, FileText, Share2, Link2
} from 'lucide-react';

interface ChatViewProps {
  onOpenVoiceModal: () => void;
  conversationId?: string;
  onLoadConversation?: (conversationId: string) => void;
  onVoiceResponse?: (transcript: string, response: ChatMessage) => void;
}

const SUGGESTED_PROMPTS = [
  'What is the BCA fee?',
  'Who teaches DBMS?',
  'When is the DBMS exam?',
  'What is the DBMS syllabus?',
  'What is the BCA timetable?',
  'Show AIT library information.',
  'What events happened last year?',
  'Explain normalization.',
  'Make a study plan for my exam.',
  'Show my result.'
];

export const ChatView: React.FC<ChatViewProps> = ({ onOpenVoiceModal, conversationId: propConversationId, onLoadConversation, onVoiceResponse }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(propConversationId);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [lastUserPrompt, setLastUserPrompt] = useState<string>('');
  const [selectedImage, setSelectedImage] = useState<ImageCard | null>(null);
  const [failedImageUrls, setFailedImageUrls] = useState<Set<string>>(new Set());
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [voiceModeActive, setVoiceModeActive] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [thinkEnabled, setThinkEnabled] = useState(false);
  const [attachment, setAttachment] = useState<File | null>(null);
  const [attachmentId, setAttachmentId] = useState<string | null>(null);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    const useAttachment = (event: Event) => {
      const id = (event as CustomEvent<string>).detail;
      setAttachmentId(id);
      setInput(value => value || 'Explain this file.');
    };
    window.addEventListener('ait:use-attachment', useAttachment);
    return () => window.removeEventListener('ait:use-attachment', useAttachment);
  }, []);

  useEffect(() => {
    const resetChat = () => {
      setMessages([]);
      setInput('');
      setIsLoading(false);
      setConversationId(undefined);
      setLastUserPrompt('');
    };
    window.addEventListener('ait:new-chat', resetChat);
    return () => window.removeEventListener('ait:new-chat', resetChat);
  }, []);

  // Load conversation when conversationId prop changes
  useEffect(() => {
    if (propConversationId && propConversationId !== conversationId) {
      loadConversation(propConversationId);
    }
  }, [propConversationId, conversationId]);

  const loadConversation = async (convId: string) => {
    setLoadingConversation(true);
    try {
      const convData = await api.getConversation(convId);
      setConversationId(convId);
      setMessages(convData.messages.map((msg: any) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        status: 'complete',
        timestamp: msg.created_at,
        intent: msg.intent,
        entities: msg.entities,
        selected_source: msg.selected_source,
        sources: msg.sources,
        images: msg.images,
        voice_asset_id: msg.voice_asset_id,
        confidence: msg.confidence,
        feedback: msg.feedback,
        input_mode: (msg.source_metadata && msg.source_metadata.input_mode) || 'text'
      })));

      if (onLoadConversation) {
        onLoadConversation(convId);
      }
    } catch (error) {
      console.error('Failed to load conversation:', error);
    } finally {
      setLoadingConversation(false);
    }
  };

  const handleSend = async (textToSend?: string, regenerate = false) => {
    const query = (textToSend || input).trim();
    if (!query || isLoading) return;

    setLastUserPrompt(query);

    let uploadedAttachmentId = attachmentId;
    try {
      if (attachment && !uploadedAttachmentId) {
        const uploaded = await api.uploadAttachment(attachment, conversationId);
        uploadedAttachmentId = uploaded.id;
        setAttachmentId(uploaded.id);
      }
    } catch (err: any) {
      setMessages(prev => [...prev, { id: `attachment-error-${Date.now()}`, role: 'assistant', content: err.message || 'This file could not be uploaded. Please try another copy.', status: 'error', timestamp: new Date().toISOString() }]);
      return;
    }

    const userMsgId = `user-${Date.now()}`;
    const tempAsstId = `asst-temp-${Date.now()}`;

    const userMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: query,
      status: 'complete',
      timestamp: new Date().toISOString(),
    };

    const thinkingMsg: ChatMessage = {
      id: tempAsstId,
      role: 'assistant',
      content: '',
      status: 'thinking',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => regenerate
      ? [...prev.filter(msg => msg.content !== '' && msg.status !== 'thinking'), thinkingMsg]
      : [...prev, userMsg, thinkingMsg]
    );
    if (!textToSend) setInput('');
    setAttachment(null);
    setAttachmentId(null);
    setToolsOpen(false);
    setIsLoading(true);

    try {
      const res = await api.sendMessage(query, conversationId, 'TEXT', regenerate, {
        think: thinkEnabled,
        tool: thinkEnabled ? 'THINK' : undefined,
        attachmentIds: uploadedAttachmentId ? [uploadedAttachmentId] : [],
      });
      if (res.conversation_id) {
        setConversationId(res.conversation_id);
      }

      const verifiedAnswer = res.content || res.answer || "I couldn't find verified AIT information about that.";

      setMessages(prev =>
        prev.map(msg =>
          msg.id === tempAsstId
            ? {
                ...res,
                id: res.id || res.message_id || tempAsstId,
                role: 'assistant',
                content: verifiedAnswer,
                status: 'complete',
                timestamp: res.timestamp || new Date().toISOString(),
              }
            : msg
        )
      );
    } catch (err: any) {
      console.error('Chat error:', err);
      const friendlyErr = "Something went wrong while preparing your answer. Please try again.";
      setMessages(prev =>
        prev.map(msg =>
          msg.id === tempAsstId
            ? {
                id: tempAsstId,
                role: 'assistant',
                content: friendlyErr,
                status: 'error',
                timestamp: new Date().toISOString(),
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerate = (query?: string) => {
    const promptToRetry = query || lastUserPrompt;
    if (!promptToRetry || isLoading) return;
    // Regeneration reuses the prompt without adding a second user message.
    handleSend(promptToRetry, true);
  };

  const handlePlayAudio = (msg: ChatMessage) => {
    const assetId = msg.voice_asset_id;
    if (playingAudioId === (assetId || msg.id)) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      window.speechSynthesis.cancel();
      setPlayingAudioId(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
    }
    window.speechSynthesis.cancel();

    const activeKey = assetId || msg.id;
    setPlayingAudioId(activeKey);

    if (assetId) {
      const audioUrl = api.getVoiceAudioUrl(assetId);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        setPlayingAudioId(null);
      };

      audio.play().catch(() => {
        speakWithBrowser(msg.content, activeKey);
      });
    } else {
      speakWithBrowser(msg.content, activeKey);
    }
  };

  const speakWithBrowser = (text: string, activeKey: string) => {
    if (!('speechSynthesis' in window)) {
      setPlayingAudioId(null);
      return;
    }
    const cleanText = text.replace(/[*#`_\-\[\]\(\)]/g, ' ');
    const utter = new SpeechSynthesisUtterance(cleanText);
    utter.rate = 1.0;
    utter.pitch = 1.0;
    utter.onend = () => setPlayingAudioId(null);
    utter.onerror = () => setPlayingAudioId(null);
    window.speechSynthesis.speak(utter);
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleShare = async () => {
    if (!conversationId) return;
    try {
      const result = await api.createShare(conversationId);
      const link = `${window.location.origin}/share/${result.token}`;
      setShareLink(link);
      await navigator.clipboard.writeText(link).catch(() => undefined);
    } catch (error) {
      console.error('Failed to create share link:', error);
    }
  };

  const handleToggleSave = (id: string) => {
    setSavedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleFeedback = async (msgId: string, type: 'helpful' | 'unhelpful') => {
    try {
      await api.submitFeedback(msgId, type);
      setMessages(prev =>
        prev.map(m => (m.id === msgId ? { ...m, feedback: type } : m))
      );
    } catch (err) {
      console.error(err);
    }
  };

  const handleVoiceResponse = (transcript: string, response: ChatMessage) => {
    // Add the user's voice transcript as a user message with voice indicator
    const userMsgId = `user-voice-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: transcript, // Use the actual transcript from voice
      status: 'complete',
      timestamp: new Date().toISOString(),
      // Add metadata to indicate this was a voice message
      input_mode: 'voice'
    };

    // Add the assistant's response
    const asstMsg: ChatMessage = {
      ...response,
      status: 'complete',
      timestamp: response.timestamp || new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg, asstMsg]);
    setLastUserPrompt(transcript);

    if (response.conversation_id) {
      setConversationId(response.conversation_id);
    }

    // Notify parent component about the voice response
    if (onVoiceResponse) {
      onVoiceResponse(transcript, response);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4.75rem)] max-w-4xl mx-auto px-3 sm:px-6 w-full">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-6 pt-4 pb-6 pr-1 sm:pr-2">
        {/* Loading Conversation */}
        {loadingConversation && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <div className="flex items-center space-x-3 text-slate-300">
              <div className="flex space-x-1.5 items-center">
                <div className="w-2 h-2 rounded-full bg-ait-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-ait-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-ait-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-sm font-medium text-slate-300">Loading conversation…</span>
            </div>
          </div>
        )}

        {/* Welcome Screen if empty */}
        {messages.length === 0 && !loadingConversation && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 py-8">
            <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-3xl bg-slate-900 border border-slate-700/80 p-3 shadow-2xl flex items-center justify-center mb-5">
              <img
                src="/assets/ait/ait-logo.webp"
                alt="Ahmedabad Institute of Technology"
                className="w-full h-full object-contain"
              />
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white font-heading tracking-tight mb-2">
              AIT AI Assistant
            </h2>
            <p className="text-sm sm:text-base text-slate-400 max-w-md mb-8">
              How can I help you today? Ask questions about admissions, fees, faculty, schedules, facilities, or academic subjects.
            </p>

            <div className="w-full max-w-2xl grid grid-cols-1 sm:grid-cols-2 gap-2.5 sm:gap-3 text-left">
              {SUGGESTED_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(prompt)}
                  className="p-3.5 rounded-2xl bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-ait-500/50 text-slate-200 hover:text-white text-xs sm:text-sm font-medium transition-all duration-200 flex items-center justify-between group shadow-sm hover:shadow-md"
                >
                  <span className="truncate mr-2">{prompt}</span>
                  <Sparkles className="w-4 h-4 text-ait-gold opacity-60 group-hover:opacity-100 group-hover:scale-110 transition-all flex-shrink-0" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message List */}
        {messages.map(msg => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} space-y-1.5`}
          >
            {/* Role Header */}
            <div className="flex items-center space-x-2 text-[11px] text-slate-400 px-1">
              <span className="font-semibold text-slate-300">
                {msg.role === 'user' ? 'You' : 'AIT AI Assistant'}
              </span>
              {msg.input_mode === 'voice' && msg.role === 'user' && (
                <div className="flex items-center" title="Voice message">
                  <Mic className="w-3 h-3 text-ait-gold" />
                </div>
              )}
              <span>•</span>
              <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>

            {/* Bubble */}
            <div
              className={`w-full max-w-2xl rounded-2xl p-4 sm:p-5 shadow-md transition-all ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-ait-600 to-blue-600 text-white font-medium ml-auto'
                  : msg.status === 'error'
                  ? 'bg-red-950/40 text-red-200 border border-red-500/30'
                  : 'bg-slate-900/90 text-slate-100 border border-slate-800/90'
              }`}
            >
              {/* Thinking State */}
              {msg.status === 'thinking' ? (
                <div className="flex items-center space-x-3 py-1 text-slate-300">
                  <div className="flex space-x-1.5 items-center">
                    <div className="w-2 h-2 rounded-full bg-ait-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 rounded-full bg-ait-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full bg-ait-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <span className="text-xs sm:text-sm font-medium text-slate-300">Thinking…</span>
                </div>
              ) : msg.status === 'error' ? (
                <div className="flex items-start space-x-2.5">
                  <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm text-red-200">{msg.content || "I’m unable to generate an answer right now. Please try again."}</p>
                    <button
                      onClick={() => handleRegenerate(lastUserPrompt)}
                      className="mt-2.5 px-3 py-1 rounded-lg bg-red-600/80 hover:bg-red-500 text-white text-xs font-semibold flex items-center space-x-1.5 transition-all"
                    >
                      <RefreshCw className="w-3 h-3" />
                      <span>Retry</span>
                    </button>
                  </div>
                </div>
              ) : msg.role === 'user' ? (
                <div className="text-xs sm:text-sm font-medium leading-relaxed text-white whitespace-pre-wrap">
                  {msg.content}
                </div>
              ) : (
                /* Assistant Message with Clean Markdown Rendering */
                <div className="space-y-2">
                  <MarkdownRenderer content={msg.content} />
                </div>
              )}

              {/* Verified Images Gallery with Lightbox */}
              {msg.role === 'assistant' && msg.status === 'complete' && msg.images && msg.images.length > 0 && (
                <div className="mt-4 pt-3.5 border-t border-slate-800/80">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {msg.images.filter(img => img.image_url && !failedImageUrls.has(img.image_url)).map((img, idx) => (
                      <div
                        key={`${img.image_url}-${idx}`}
                        onClick={() => setSelectedImage(img)}
                        className="rounded-xl overflow-hidden bg-slate-950 border border-slate-800 group cursor-pointer hover:border-ait-500/50 transition-all"
                      >
                        <div className="relative h-40 bg-slate-900 overflow-hidden">
                          <img
                            src={img.image_url}
                            alt={img.alt_text || 'AIT Official Image'}
                            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                            onError={() => {
                              setFailedImageUrls(prev => {
                                const next = new Set(prev);
                                next.add(img.image_url);
                                return next;
                              });
                              if (selectedImage?.image_url === img.image_url) setSelectedImage(null);
                            }}
                          />
                          <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-80" />
                          <div className="absolute bottom-2 left-2.5 right-2.5">
                            <p className="text-xs font-semibold text-white truncate">{img.caption || img.source_page}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Chat Actions: Copy, Replay, Regenerate, Feedback, Save */}
              {msg.role === 'assistant' && msg.status === 'complete' && (
                <div className="mt-3.5 pt-2.5 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80">
                  <div className="flex items-center space-x-1.5 sm:space-x-2">
                    <button
                      onClick={() => handlePlayAudio(msg)}
                      className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-blue-300 border border-slate-700/80 flex items-center space-x-1.5 transition-all text-xs font-medium"
                      title="Listen to Voice Answer"
                    >
                      {playingAudioId === (msg.voice_asset_id || msg.id) ? (
                        <>
                          <Pause className="w-3.5 h-3.5 text-blue-400" />
                          <span>Pause</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5 text-blue-400" />
                          <span>Replay</span>
                        </>
                      )}
                    </button>

                    <button
                      onClick={() => handleCopy(msg.content, msg.id)}
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all"
                      title="Copy exact answer"
                    >
                      {copiedId === msg.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>

                    <button
                      onClick={() => handleRegenerate()}
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all"
                      title="Regenerate answer"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>

                    <button onClick={handleShare} disabled={!conversationId} title="Share conversation" aria-label="Share conversation" className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 disabled:opacity-40 transition-all"><Share2 className="w-3.5 h-3.5" /></button>

                    <button
                      onClick={() => handleToggleSave(msg.id)}
                      className={`p-1.5 rounded-lg transition-all ${
                        savedIds.has(msg.id) ? 'text-ait-gold bg-amber-500/20' : 'hover:bg-slate-800 text-slate-400'
                      }`}
                      title="Save answer"
                    >
                      <Bookmark className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => handleFeedback(msg.id, 'helpful')}
                      className={`p-1.5 rounded-lg transition-all ${
                        msg.feedback === 'helpful' ? 'text-emerald-400 bg-emerald-950/40' : 'hover:bg-slate-800 text-slate-400'
                      }`}
                      title="Helpful Answer"
                    >
                      <ThumbsUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleFeedback(msg.id, 'unhelpful')}
                      className={`p-1.5 rounded-lg transition-all ${
                        msg.feedback === 'unhelpful' ? 'text-red-400 bg-red-950/40' : 'hover:bg-slate-800 text-slate-400'
                      }`}
                      title="Report / Unhelpful"
                    >
                      <ThumbsDown className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Suggested Follow-up Chips */}
            {msg.role === 'assistant' && msg.status === 'complete' && msg.suggested_followups && msg.suggested_followups.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2 max-w-2xl">
                {msg.suggested_followups.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(chip)}
                    className="px-3 py-1.5 rounded-full text-xs font-medium bg-slate-900 hover:bg-slate-800 text-blue-300 hover:text-white border border-slate-800 hover:border-ait-500/50 transition-all flex items-center space-x-1 shadow-sm"
                  >
                    <Sparkles className="w-3 h-3 text-ait-gold" />
                    <span>{chip}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="mt-auto pt-2 pb-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center space-x-2 bg-slate-900/90 p-2 rounded-2xl border border-slate-800 shadow-xl"
        >
          {attachment && (
            <div className="absolute -translate-y-14 left-2 flex items-center gap-2 rounded-lg border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 shadow-lg">
              <FileText className="h-4 w-4 text-ait-gold" />
              <span className="max-w-[180px] truncate">{attachment.name}</span>
              <button type="button" onClick={() => { setAttachment(null); setAttachmentId(null); }} aria-label="Remove attachment" title="Remove attachment" className="text-slate-400 hover:text-white">
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.txt,image/png,image/jpeg,image/webp"
            onChange={(event) => { setAttachment(event.target.files?.[0] || null); setAttachmentId(null); }}
          />
          <div className="relative flex-shrink-0">
            <button
              type="button"
              onClick={() => setToolsOpen((open) => !open)}
              className="p-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition-all"
              title="Open tools and attachments"
              aria-label="Open tools and attachments"
              aria-expanded={toolsOpen}
            >
              <Plus className="w-5 h-5" />
            </button>
            {toolsOpen && (
              <div className="absolute bottom-14 left-0 z-20 w-56 rounded-xl border-slate-700 bg-slate-900 p-2 shadow-2xl">
                <button type="button" onClick={() => fileInputRef.current?.click()} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800"><FileText className="h-4 w-4" />Upload file</button>
                <button type="button" onClick={() => { setInput((value) => value ? `${value} Search the web for this: ` : 'Search the web for: '); setToolsOpen(false); }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800"><Globe2 className="h-4 w-4" />Search the web</button>
                <button type="button" onClick={() => { setInput((value) => value ? `${value} Study this: ` : 'Study this: '); setToolsOpen(false); }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800"><GraduationCap className="h-4 w-4" />Study mode</button>
                <button type="button" onClick={() => { setThinkEnabled((enabled) => !enabled); setToolsOpen(false); }} className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-800 ${thinkEnabled ? 'text-ait-gold' : 'text-slate-200'}`}><Brain className="h-4 w-4" />{thinkEnabled ? 'Think enabled' : 'Think more'}</button>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onOpenVoiceModal}
            className={`p-3 rounded-xl transition-all hover:scale-105 flex-shrink-0 ${
              voiceModeActive
                ? 'bg-ait-600 text-white animate-pulse'
                : 'bg-slate-800 hover:bg-slate-700 text-blue-400'
            }`}
            title="Start Voice Mode"
            aria-label="Start Voice Mode"
          >
            <Volume2 className="w-5 h-5" />
          </button>

          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPaste={(e) => {
              const pastedImage = Array.from(e.clipboardData.files).find((file) => file.type.startsWith('image/'));
              if (pastedImage) { setAttachment(pastedImage); setAttachmentId(null); }
            }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              setAttachment(e.dataTransfer.files?.[0] || null); setAttachmentId(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            rows={1}
            aria-label="Ask anything about AIT"
            placeholder="Ask anything about AIT..."
            className="flex-1 resize-none bg-transparent px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none min-h-[42px] max-h-32"
            disabled={isLoading}
          />

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="p-3 rounded-xl bg-ait-600 hover:bg-ait-500 disabled:opacity-40 disabled:hover:bg-ait-600 text-white font-semibold transition-all hover:scale-105 flex-shrink-0 shadow-lg shadow-ait-600/30"
            title="Send Message"
            aria-label="Send Message"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
        <p className="text-[11px] text-center text-slate-500 mt-2">
          AIT AI Assistant provides verified answers from official college repositories.
        </p>
      </div>

      {shareLink && <div role="status" className="fixed bottom-20 left-1/2 z-40 flex -translate-x-1/2 items-center gap-2 rounded-lg border-emerald-500/30 bg-slate-900 px-3 py-2 text-xs text-emerald-200 shadow-xl"><Link2 className="h-4 w-4" /><span>Share link copied</span><button onClick={() => setShareLink(null)} aria-label="Dismiss share notification"><X className="h-4 w-4" /></button></div>}

      {/* Image Lightbox Modal */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-md"
          onClick={() => setSelectedImage(null)}
        >
          <div
            className="relative max-w-3xl w-full bg-slate-900 border border-slate-700/80 rounded-3xl overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={selectedImage.image_url}
              alt={selectedImage.alt_text || 'AIT Image'}
              className="w-full max-h-[70vh] object-contain bg-slate-950"
              onError={() => {
                setFailedImageUrls(prev => new Set(prev).add(selectedImage.image_url));
                setSelectedImage(null);
              }}
            />
            <div className="p-4 bg-slate-900 flex items-center justify-between border-t border-slate-800">
              <div>
                <h4 className="text-sm font-bold text-white">{selectedImage.caption}</h4>
                <p className="text-xs text-slate-400">{selectedImage.provenance}</p>
              </div>
              <button
                onClick={() => setSelectedImage(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
