import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';
import { Mic, MicOff, X, Volume2, Sparkles, CheckCircle2, RotateCcw, AlertCircle, Play, Pause, Settings, Globe, Languages } from 'lucide-react';
import { ChatMessage } from '../types';

interface VoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onResponseReceived?: (transcript: string, response: ChatMessage) => void;
  conversationId?: string;
}

type VoiceState = 'IDLE' | 'REQUESTING_PERMISSION' | 'LISTENING' | 'PROCESSING' | 'SPEAKING' | 'COMPLETED' | 'ERROR';
type VoiceLanguage = 'en-IN' | 'hi-IN' | 'gu-IN';

interface VoiceSettings {
  language: VoiceLanguage;
  autoSpeak: boolean;
  continuousMode: boolean;
  preferredVoiceName: string | null;
}

const LANGUAGE_OPTIONS: { value: VoiceLanguage; label: string; flag: string }[] = [
  { value: 'en-IN', label: 'English', flag: '🇬🇧' },
  { value: 'hi-IN', label: 'हिंदी', flag: '🇮🇳' },
  { value: 'gu-IN', label: 'ગુજરાતી', flag: '🇮🇳' }
];

const LISTENING_TIMEOUT = 15000; // 15 seconds of silence
const MIN_SPEECH_LENGTH = 2; // Minimum characters to consider valid speech

export const VoiceModal: React.FC<VoiceModalProps> = ({ isOpen, onClose, onResponseReceived, conversationId }) => {
  const [voiceState, setVoiceState] = useState<VoiceState>('IDLE');
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [latestResponse, setLatestResponse] = useState<ChatMessage | null>(null);
  const [voiceSettings, setVoiceSettings] = useState<VoiceSettings>(() => {
    const saved = localStorage.getItem('ait_voice_settings');
    return saved ? JSON.parse(saved) : {
      language: 'en-IN',
      autoSpeak: true,
      continuousMode: false,
      preferredVoiceName: null
    };
  });
  const [showSettings, setShowSettings] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [ttsSupported, setTtsSupported] = useState(true);
  const [listeningTimer, setListeningTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastSpeechRef = useRef<number>(Date.now());

  // Check browser support
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setSpeechSupported(!!SpeechRecognition);
    setTtsSupported('speechSynthesis' in window);
  }, []);

  // Save settings
  useEffect(() => {
    localStorage.setItem('ait_voice_settings', JSON.stringify(voiceSettings));
  }, [voiceSettings]);

  // Cleanup on close
  useEffect(() => {
    if (!isOpen) {
      handleStop();
      cleanupTimers();
      setTranscript('');
      setInterimTranscript('');
      setLatestResponse(null);
      setErrorMessage(null);
      setVoiceState('IDLE');
      if (audioRef.current) {
        audioRef.current.pause();
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    }
  }, [isOpen]);

  const cleanupTimers = useCallback(() => {
    if (listeningTimer) {
      clearTimeout(listeningTimer);
      setListeningTimer(null);
    }
  }, [listeningTimer]);

  const resetSpeechTimer = useCallback(() => {
    cleanupTimers();
    if (voiceState === 'LISTENING') {
      const timer = setTimeout(() => {
        handleStop();
        if (transcript.length < MIN_SPEECH_LENGTH) {
          setErrorMessage('No speech detected. Please try speaking again.');
          setVoiceState('ERROR');
        } else {
          handleProcessVoice();
        }
      }, LISTENING_TIMEOUT);
      setListeningTimer(timer);
    }
  }, [voiceState, transcript, cleanupTimers]);

  useEffect(() => {
    if (voiceState === 'LISTENING') {
      resetSpeechTimer();
    }
    return cleanupTimers;
  }, [voiceState, transcript, resetSpeechTimer, cleanupTimers]);

  const handleStart = async () => {
    setErrorMessage(null);
    setTranscript('');
    setInterimTranscript('');
    setLatestResponse(null);

    if (!speechSupported) {
      setVoiceState('ERROR');
      setErrorMessage('Voice input is not supported by this browser. Please use a supported browser or type your question instead.');
      return;
    }

    setVoiceState('REQUESTING_PERMISSION');

    // Check microphone permission
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
      }
    } catch (err: any) {
      setVoiceState('ERROR');
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMessage('Microphone access is blocked. Please allow microphone permission in your browser settings and try again.');
      } else {
        setErrorMessage('Could not access your microphone. Please check your browser permissions.');
      }
      return;
    }

    setVoiceState('LISTENING');

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = voiceSettings.language;

        recognition.onresult = (event: any) => {
          let interim = '';
          let final = '';
          lastSpeechRef.current = Date.now();
          resetSpeechTimer();

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              final += transcript;
            } else {
              interim += transcript;
            }
          }

          if (final) {
            setTranscript(prev => prev + final);
          }
          setInterimTranscript(interim);
        };

        recognition.onerror = (e: any) => {
          console.error('Speech recognition error:', e);
          cleanupTimers();
          
          const errorMessages: Record<string, string> = {
            'not-allowed': 'Microphone access is blocked. Please allow microphone permission in your browser settings.',
            'no-speech': 'No speech detected. Please try speaking again.',
            'audio-capture': 'Could not access your microphone. Please check your browser permissions.',
            'network': 'Network error occurred during speech recognition.',
            'aborted': 'Speech recognition was interrupted.',
            'language-not-supported': 'The selected language is not supported for speech recognition.'
          };

          setErrorMessage(errorMessages[e.error] || "I couldn't understand that. Please try again.");
          setVoiceState('ERROR');
        };

        recognition.onend = () => {
          cleanupTimers();
          // Auto-submit if we have meaningful speech and user didn't manually stop
          if (voiceState === 'LISTENING' && transcript.length >= MIN_SPEECH_LENGTH) {
            handleProcessVoice();
          } else if (voiceState === 'LISTENING') {
            setVoiceState('IDLE');
          }
        };

        recognition.start();
        recognitionRef.current = recognition;
      } catch (e) {
        cleanupTimers();
        setVoiceState('ERROR');
        setErrorMessage("I couldn't start speech recognition. Please try again.");
      }
    }
  };

  const handleStop = () => {
    cleanupTimers();
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
    if (voiceState === 'LISTENING') {
      setVoiceState('IDLE');
    }
  };

  const handleProcessVoice = async () => {
    handleStop();
    const finalTranscript = (transcript + interimTranscript).trim();
    
    if (!finalTranscript || finalTranscript.length < MIN_SPEECH_LENGTH) {
      setErrorMessage('Please speak a complete question.');
      setVoiceState('ERROR');
      return;
    }

    setVoiceState('PROCESSING');
    setErrorMessage(null);

    try {
      const data = await api.sendVoiceTranscript(finalTranscript, conversationId);
      const res = data.chat_response;
      setLatestResponse(res);
      
      if (onResponseReceived) {
        onResponseReceived(finalTranscript, res);
      }

      // Auto-speak if enabled
      if (voiceSettings.autoSpeak && ttsSupported) {
        playVoiceOutput(res);
      } else {
        setVoiceState('COMPLETED');
      }

      // Continuous mode: auto-listen after speaking completes
      if (voiceSettings.continuousMode) {
        setTimeout(() => {
          if (voiceState !== 'LISTENING') {
            handleStart();
          }
        }, 1000);
      }
    } catch (err: any) {
      console.error('Error processing voice query:', err);
      setVoiceState('ERROR');
      setErrorMessage(err.message || "I couldn't complete that request. Please try again.");
    }
  };

  const playVoiceOutput = (res: ChatMessage) => {
    setVoiceState('SPEAKING');

    if (res.voice_asset_id) {
      const audioUrl = api.getVoiceAudioUrl(res.voice_asset_id);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        setVoiceState('COMPLETED');
      };

      audio.onerror = () => {
        fallbackBrowserTTS(res.content);
      };

      audio.play().catch(() => {
        fallbackBrowserTTS(res.content);
      });
    } else {
      fallbackBrowserTTS(res.content);
    }
  };

  const fallbackBrowserTTS = (text: string) => {
    if (!ttsSupported) {
      setVoiceState('COMPLETED');
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[*#`_\-\[\]\(\)]/g, ' ');
      const utter = new SpeechSynthesisUtterance(cleanText);
      
      // Try to select appropriate voice based on language
      const voices = window.speechSynthesis.getVoices();
      const langCode = voiceSettings.language.split('-')[0];
      const matchingVoice = voices.find(v => v.lang.startsWith(langCode)) || 
                          voices.find(v => v.lang.startsWith('en')) ||
                          voices[0];
      
      if (matchingVoice) {
        utter.voice = matchingVoice;
      }
      
      utter.rate = 1.0;
      utter.pitch = 1.0;
      utter.onend = () => setVoiceState('COMPLETED');
      utter.onerror = () => {
        setVoiceState('COMPLETED');
      };
      window.speechSynthesis.speak(utter);
    } catch {
      setVoiceState('COMPLETED');
    }
  };

  const handleStopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    if (ttsSupported) {
      window.speechSynthesis.cancel();
    }
    setVoiceState('COMPLETED');
  };

  const handleReplay = () => {
    if (!latestResponse) return;
    if (voiceState === 'SPEAKING') {
      handleStopSpeaking();
    } else {
      playVoiceOutput(latestResponse);
    }
  };

  const updateSettings = (updates: Partial<VoiceSettings>) => {
    setVoiceSettings(prev => ({ ...prev, ...updates }));
  };

  if (!isOpen) return null;

  const displayTranscript = transcript + interimTranscript;
  const selectedLanguage = LANGUAGE_OPTIONS.find(l => l.value === voiceSettings.language);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-700/90 rounded-3xl p-6 sm:p-8 shadow-2xl overflow-hidden">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
          aria-label="Close voice assistant"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Settings Button */}
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="absolute top-4 left-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
          aria-label="Voice settings"
        >
          <Settings className="w-5 h-5" />
        </button>

        {/* Settings Panel */}
        {showSettings && (
          <div className="absolute top-16 left-4 right-4 bg-slate-800 border border-slate-700 rounded-2xl p-4 z-10 shadow-xl">
            <h4 className="text-sm font-semibold text-white mb-3 flex items-center space-x-2">
              <Globe className="w-4 h-4" />
              <span>Voice Settings</span>
            </h4>
            
            {/* Language Selection */}
            <div className="mb-4">
              <label className="text-xs text-slate-400 mb-2 block">Language</label>
              <div className="flex flex-wrap gap-2">
                {LANGUAGE_OPTIONS.map(lang => (
                  <button
                    key={lang.value}
                    onClick={() => updateSettings({ language: lang.value })}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                      voiceSettings.language === lang.value
                        ? 'bg-ait-600 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    <span className="mr-1">{lang.flag}</span>
                    {lang.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Auto Speak Toggle */}
            <div className="mb-4">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={voiceSettings.autoSpeak}
                  onChange={(e) => updateSettings({ autoSpeak: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-ait-600 focus:ring-ait-500"
                />
                <span className="text-sm text-slate-300">Auto-speak responses</span>
              </label>
            </div>

            {/* Continuous Mode Toggle */}
            <div>
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={voiceSettings.continuousMode}
                  onChange={(e) => updateSettings({ continuousMode: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-ait-600 focus:ring-ait-500"
                />
                <span className="text-sm text-slate-300">Continuous conversation</span>
              </label>
            </div>
          </div>
        )}

        {/* Modal Header */}
        <div className="text-center mb-6 mt-4">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-tr from-ait-600 to-blue-500 text-white shadow-lg shadow-ait-600/30 mb-3">
            <Volume2 className="w-6 h-6" />
          </div>
          <h3 className="font-heading text-xl font-bold text-white">AIT Voice Assistant</h3>
          <p className="text-xs text-slate-400 mt-1 flex items-center justify-center space-x-1">
            <span>Speak naturally in</span>
            <span className="flex items-center space-x-1">
              <span>{selectedLanguage?.flag}</span>
              <span>{selectedLanguage?.label}</span>
            </span>
          </p>
        </div>

        {/* Dynamic Waveform Visualizer */}
        <div className="h-24 flex items-center justify-center space-x-1.5 bg-slate-950/80 rounded-2xl p-4 mb-5 border border-slate-800">
          {voiceState === 'REQUESTING_PERMISSION' ? (
            <div className="flex items-center space-x-2 text-yellow-300 text-xs font-semibold animate-pulse">
              <Sparkles className="w-4 h-4" />
              <span>Requesting microphone permission...</span>
            </div>
          ) : voiceState === 'LISTENING' ? (
            <>
              {[40, 75, 20, 90, 50, 85, 30, 95, 60, 80, 45, 100, 35, 70, 55].map((height, i) => (
                <div
                  key={i}
                  className="w-1.5 bg-gradient-to-t from-ait-600 to-blue-400 rounded-full transition-all duration-150 animate-pulse"
                  style={{
                    height: `${height}%`,
                    animationDelay: `${i * 80}ms`,
                  }}
                />
              ))}
            </>
          ) : voiceState === 'SPEAKING' ? (
            <div className="flex items-center space-x-2 text-blue-300 text-xs font-semibold">
              <Volume2 className="w-5 h-5 animate-bounce text-ait-gold" />
              <span>Speaking Response...</span>
            </div>
          ) : voiceState === 'PROCESSING' ? (
            <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold animate-pulse">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span>Processing verified answer...</span>
            </div>
          ) : (
            <div className="text-center text-xs text-slate-400">
              {voiceState === 'COMPLETED' ? 'Response completed. Tap replay or ask another question.' : 'Tap the microphone button below to start speaking.'}
            </div>
          )}
        </div>

        {/* Live Transcript Display */}
        <div className="bg-slate-950/80 rounded-2xl p-4 mb-4 border border-slate-800 min-h-[64px]">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Live Speech Transcript:
          </div>
          <p className="text-sm font-medium text-slate-200 italic">
            {displayTranscript || (voiceState === 'LISTENING' ? 'Listening...' : 'No voice detected yet.')}
          </p>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mb-4 p-3 rounded-xl bg-red-950/50 border border-red-500/30 text-xs text-red-300 flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Browser Support Warning */}
        {!speechSupported && (
          <div className="mb-4 p-3 rounded-xl bg-yellow-950/50 border border-yellow-500/30 text-xs text-yellow-300 flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-yellow-400 flex-shrink-0" />
            <span>Voice input is not supported by this browser. Please use Chrome, Edge, or Safari.</span>
          </div>
        )}

        {/* AI Answer Preview */}
        {latestResponse && (
          <div className="bg-slate-950/80 rounded-2xl p-4 mb-5 border border-slate-800 max-h-44 overflow-y-auto">
            <div className="text-[11px] font-semibold text-emerald-400 flex items-center space-x-1 mb-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Verified Response:</span>
            </div>
            <p className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
              {latestResponse.content}
            </p>
          </div>
        )}

        {/* Action Controls */}
        <div className="flex items-center justify-center space-x-3">
          {voiceState !== 'LISTENING' && voiceState !== 'REQUESTING_PERMISSION' ? (
            <button
              onClick={handleStart}
              disabled={!speechSupported}
              className="px-6 py-3.5 rounded-2xl bg-ait-600 hover:bg-ait-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold flex items-center space-x-2 shadow-xl shadow-ait-600/30 transition-all hover:scale-105"
              aria-label={latestResponse ? 'Ask another question' : 'Start speaking'}
            >
              <Mic className="w-5 h-5" />
              <span>{latestResponse ? 'Ask Another Question' : 'Start Speaking'}</span>
            </button>
          ) : (
            <button
              onClick={handleProcessVoice}
              className="px-6 py-3.5 rounded-2xl bg-red-600 hover:bg-red-500 text-white font-semibold flex items-center space-x-2 shadow-xl shadow-red-600/30 transition-all hover:scale-105"
              aria-label="Done speaking and submit"
            >
              <MicOff className="w-5 h-5 animate-pulse" />
              <span>Done Speaking & Submit</span>
            </button>
          )}

          {latestResponse && (
            <button
              onClick={handleReplay}
              className="p-3.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-blue-300 border border-slate-700 transition-all"
              title={voiceState === 'SPEAKING' ? 'Stop Speaking' : 'Replay Audio'}
              aria-label={voiceState === 'SPEAKING' ? 'Stop speaking' : 'Replay audio'}
            >
              {voiceState === 'SPEAKING' ? <Pause className="w-5 h-5" /> : <RotateCcw className="w-5 h-5" />}
            </button>
          )}

          {voiceState === 'SPEAKING' && (
            <button
              onClick={handleStopSpeaking}
              className="p-3.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-red-300 border border-slate-700 transition-all"
              title="Stop Speaking"
              aria-label="Stop speaking"
            >
              <Volume2 className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Text Fallback */}
        <div className="mt-4 text-center">
          <button
            onClick={onClose}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Prefer typing? [ Type your question instead ]
          </button>
        </div>
      </div>
    </div>
  );
};

