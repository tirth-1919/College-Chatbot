import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, SourceCard, ImageCard } from '../types';
import { api } from '../services/api';
import {
  Send, Sparkles, Volume2, Play, Pause, RotateCcw, ThumbsUp, ThumbsDown,
  ExternalLink, ShieldCheck, Copy, Check, Bookmark, RefreshCw, AlertCircle
} from 'lucide-react';

interface ChatViewProps {
  onOpenVoiceModal: () => void;
}

const SUGGESTED_PROMPTS = [
  'What is the BCA fee?',
  'Who teaches DBMS?',
  'What is today\'s timetable?',
  'What events were organized last year?',
  'Show me the AIT library.',
  'Explain DBMS normalization.'
];

const PROCESSING_STEPS = [
  { text: 'Understanding request...', progress: 25 },
  { text: 'Searching verified information...', progress: 55 },
  { text: 'Checking sources...', progress: 80 },
  { text: 'Preparing answer...', progress: 95 }
];

export const ChatView: React.FC<ChatViewProps> = ({ onOpenVoiceModal }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [processingStepIdx, setProcessingStepIdx] = useState(0);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [lastUserPrompt, setLastUserPrompt] = useState<string>('');
  const [errorPrompt, setErrorPrompt] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<ImageCard | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, processingStepIdx]);

  useEffect(() => {
    let interval: any;
    if (isLoading) {
      setProcessingStepIdx(0);
      interval = setInterval(() => {
        setProcessingStepIdx(prev => (prev < PROCESSING_STEPS.length - 1 ? prev + 1 : prev));
      }, 700);
    } else {
      setProcessingStepIdx(0);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  useEffect(() => {
    const resetChat = () => {
      setMessages([]);
      setInput('');
      setIsLoading(false);
      setErrorPrompt(null);
    };
    window.addEventListener('ait:new-chat', resetChat);
    return () => window.removeEventListener('ait:new-chat', resetChat);
  }, []);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || isLoading) return;

    setErrorPrompt(null);
    setLastUserPrompt(query);

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setIsLoading(true);

    try {
      const res = await api.sendMessage(query);
      setMessages(prev => [...prev, res]);
    } catch (err) {
      setErrorPrompt(query);
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: 'Something went wrong while connecting to the assistant. Please try again.',
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerate = (query?: string) => {
    const promptToRetry = query || lastUserPrompt;
    if (promptToRetry) {
      handleSend(promptToRetry);
    }
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
        // Fallback to Web Speech API
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

  return (
    <div className="flex flex-col h-[calc(100vh-4.75rem)] max-w-4xl mx-auto px-3 sm:px-6 w-full">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-6 pt-4 pb-6 pr-1 sm:pr-2">
        {/* Welcome Screen if empty */}
        {messages.length === 0 && (
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
              <span>•</span>
              <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>

            {/* Bubble */}
            <div
              className={`w-full max-w-2xl rounded-2xl p-4 sm:p-5 shadow-md transition-all ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-ait-600 to-blue-600 text-white font-medium ml-auto'
                  : 'bg-slate-900/90 text-slate-100 border border-slate-800/90'
              }`}
            >
              {/* Main Answer text */}
              <div className="prose prose-invert prose-sm sm:prose-base max-w-none whitespace-pre-wrap leading-relaxed text-slate-100">
                {msg.content}
              </div>

              {/* Verified Images Gallery with Lightbox */}
              {msg.images && msg.images.length > 0 && (
                <div className="mt-4 pt-3.5 border-t border-slate-800">
                  <div className="text-xs font-semibold text-blue-300 mb-2.5 flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Official Verified Photographs</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {msg.images.map((img, idx) => (
                      <div
                        key={idx}
                        onClick={() => setSelectedImage(img)}
                        className="rounded-xl overflow-hidden bg-slate-950 border border-slate-800 group cursor-pointer hover:border-ait-500/50 transition-all"
                      >
                        <div className="relative h-40 bg-slate-900 overflow-hidden">
                          <img
                            src={img.image_url}
                            alt={img.alt_text || 'AIT Official Image'}
                            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = 'none';
                            }}
                          />
                          <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-85" />
                          <div className="absolute bottom-2 left-2.5 right-2.5">
                            <p className="text-xs font-semibold text-white truncate">{img.caption}</p>
                            <p className="text-[10px] text-slate-400 truncate">{img.provenance || 'AIT Official Record'}</p>
                          </div>
                        </div>
                        <div className="p-2 flex items-center justify-between text-[11px] bg-slate-950 text-slate-400">
                          <span className="truncate">{img.source_page}</span>
                          <a
                            href={img.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-blue-400 hover:text-blue-300 flex items-center space-x-1 flex-shrink-0"
                          >
                            <span>Source</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Sources Section Below Answer */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-4 pt-3.5 border-t border-slate-800">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Sources & Citations</span>
                  </div>
                  <div className="space-y-1.5">
                    {msg.sources.map((s, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80 text-xs"
                      >
                        <div className="flex items-center space-x-2 truncate mr-2">
                          <span className="text-emerald-400 font-bold">✓</span>
                          <span className="font-medium text-slate-200 truncate">{s.title}</span>
                          {s.page_or_record && (
                            <span className="text-[11px] text-slate-400 hidden sm:inline truncate">
                              • {s.page_or_record}
                            </span>
                          )}
                        </div>
                        {s.source_url && (
                          <a
                            href={s.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:text-blue-300 flex items-center space-x-1 flex-shrink-0 text-xs font-semibold"
                          >
                            <span>View source</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Chat Actions: Copy, Replay, Regenerate, Feedback, Save */}
              {msg.role === 'assistant' && (
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
            {msg.suggested_followups && msg.suggested_followups.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2 max-w-2xl">
                {msg.suggested_followups.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(chip)}
                    className="px-3 py-1.5 rounded-full text-xs font-medium bg-slate-900 hover:bg-slate-800 text-blue-300 hover:text-white border border-slate-800 hover:border-ait-500/50 transition-all flex items-center space-x-1"
                  >
                    <Sparkles className="w-3 h-3 text-ait-gold" />
                    <span>{chip}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* ChatGPT-style Processing State */}
        {isLoading && (
          <div className="flex items-start space-x-3 max-w-2xl">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-ait-600 to-blue-500 flex items-center justify-center animate-pulse flex-shrink-0 shadow-md">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div className="bg-slate-900/90 rounded-2xl p-4 border border-slate-800/90 space-y-2 flex-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-300">
                  {PROCESSING_STEPS[processingStepIdx].text}
                </span>
                <span className="text-[11px] font-mono text-blue-400">
                  {PROCESSING_STEPS[processingStepIdx].progress}%
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-ait-600 to-blue-400 h-full rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${PROCESSING_STEPS[processingStepIdx].progress}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Error retry banner */}
        {errorPrompt && !isLoading && (
          <div className="flex items-center justify-between p-3 rounded-2xl bg-red-950/40 border border-red-500/30 text-xs text-red-300 max-w-2xl">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span>Failed to get response for "{errorPrompt.slice(0, 30)}..."</span>
            </div>
            <button
              onClick={() => handleRegenerate(errorPrompt)}
              className="px-3 py-1 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold flex items-center space-x-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Try again</span>
            </button>
          </div>
        )}

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
          <button
            type="button"
            onClick={onOpenVoiceModal}
            className="p-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-blue-400 transition-all hover:scale-105 flex-shrink-0"
            title="Start Voice Mode"
            aria-label="Start Voice Mode"
          >
            <Volume2 className="w-5 h-5 text-blue-400" />
          </button>

          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
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
          AIT AI Assistant may produce factual info from verified college databases & portals.
        </p>
      </div>

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
            />
            <div className="p-4 bg-slate-900 flex items-center justify-between border-t border-slate-800">
              <div>
                <h4 className="text-sm font-bold text-white">{selectedImage.caption}</h4>
                <p className="text-xs text-slate-400">{selectedImage.provenance}</p>
              </div>
              <div className="flex items-center space-x-2">
                <a
                  href={selectedImage.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-xl bg-ait-600 hover:bg-ait-500 text-white text-xs font-semibold flex items-center space-x-1"
                >
                  <span>Official Page</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
                <button
                  onClick={() => setSelectedImage(null)}
                  className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
