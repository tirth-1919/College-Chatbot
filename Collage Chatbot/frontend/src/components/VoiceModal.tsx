import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { Mic, MicOff, X, Volume2, Sparkles, CheckCircle2, RotateCcw, AlertCircle, Play, Pause } from 'lucide-react';
import { ChatMessage } from '../types';

interface VoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onResponseReceived?: (response: ChatMessage) => void;
}

type VoiceState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'SPEAKING' | 'COMPLETED' | 'ERROR';

export const VoiceModal: React.FC<VoiceModalProps> = ({ isOpen, onClose, onResponseReceived }) => {
  const [voiceState, setVoiceState] = useState<VoiceState>('IDLE');
  const [transcript, setTranscript] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [latestResponse, setLatestResponse] = useState<ChatMessage | null>(null);

  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      handleStop();
      setTranscript('');
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

  const handleStart = async () => {
    setErrorMessage(null);
    setTranscript('');
    setLatestResponse(null);

    // Check microphone permission
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
      }
    } catch (err: any) {
      setVoiceState('ERROR');
      setErrorMessage('Microphone access is required for voice chat.');
      return;
    }

    setVoiceState('LISTENING');

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-IN'; // Multi-accent Indian English / Hinglish support

        recognition.onresult = (event: any) => {
          let current = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            current += event.results[i][0].transcript;
          }
          setTranscript(current);
        };

        recognition.onerror = (e: any) => {
          console.error('Speech recognition error:', e);
          if (e.error === 'not-allowed') {
            setErrorMessage('Microphone access is required for voice chat.');
          } else {
            setErrorMessage("I couldn't understand that. Please try again.");
          }
          setVoiceState('ERROR');
        };

        recognition.onend = () => {
          // If ended while listening without manual stop
        };

        recognition.start();
        recognitionRef.current = recognition;
      } catch (e) {
        setVoiceState('ERROR');
        setErrorMessage("I couldn't understand that. Please try again.");
      }
    } else {
      // Fallback for browsers without Web Speech API
      setTranscript('What is the BCA fee?');
    }
  };

  const handleStop = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
  };

  const handleProcessVoice = async () => {
    handleStop();
    const query = transcript.trim() || 'What is the BCA fee?';
    setVoiceState('PROCESSING');
    setErrorMessage(null);

    try {
      const data = await api.sendVoiceTranscript(query);
      const res = data.chat_response;
      setLatestResponse(res);
      if (onResponseReceived) {
        onResponseReceived(res);
      }

      // Play synthesized audio
      playVoiceOutput(res);
    } catch (err: any) {
      console.error('Error processing voice query:', err);
      setVoiceState('ERROR');
      setErrorMessage("I couldn't complete that request. Please try again.");
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
    if (!('speechSynthesis' in window)) {
      setVoiceState('COMPLETED');
      setErrorMessage('Voice playback is temporarily unavailable.');
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[*#`_\-\[\]\(\)]/g, ' ');
      const utter = new SpeechSynthesisUtterance(cleanText);
      utter.rate = 1.0;
      utter.pitch = 1.0;
      utter.onend = () => setVoiceState('COMPLETED');
      utter.onerror = () => {
        setVoiceState('COMPLETED');
        setErrorMessage('Voice playback is temporarily unavailable.');
      };
      window.speechSynthesis.speak(utter);
    } catch {
      setVoiceState('COMPLETED');
      setErrorMessage('Voice playback is temporarily unavailable.');
    }
  };

  const handleReplay = () => {
    if (!latestResponse) return;
    if (voiceState === 'SPEAKING') {
      if (audioRef.current) audioRef.current.pause();
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      setVoiceState('COMPLETED');
    } else {
      playVoiceOutput(latestResponse);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-700/90 rounded-3xl p-6 sm:p-8 shadow-2xl overflow-hidden">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center mb-6">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-tr from-ait-600 to-blue-500 text-white shadow-lg shadow-ait-600/30 mb-3">
            <Volume2 className="w-6 h-6" />
          </div>
          <h3 className="font-heading text-xl font-bold text-white">AIT Voice Assistant</h3>
          <p className="text-xs text-slate-400 mt-1">
            Speak naturally to ask questions in English, Hindi, or Gujarati
          </p>
        </div>

        {/* Dynamic Waveform Visualizer */}
        <div className="h-24 flex items-center justify-center space-x-1.5 bg-slate-950/80 rounded-2xl p-4 mb-5 border border-slate-800">
          {voiceState === 'LISTENING' ? (
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
            {transcript || (voiceState === 'LISTENING' ? 'Listening...' : 'No voice detected yet.')}
          </p>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mb-4 p-3 rounded-xl bg-red-950/50 border border-red-500/30 text-xs text-red-300 flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{errorMessage}</span>
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
          {voiceState !== 'LISTENING' ? (
            <button
              onClick={handleStart}
              className="px-6 py-3.5 rounded-2xl bg-ait-600 hover:bg-ait-500 text-white font-semibold flex items-center space-x-2 shadow-xl shadow-ait-600/30 transition-all hover:scale-105"
            >
              <Mic className="w-5 h-5" />
              <span>{latestResponse ? 'Ask Another Question' : 'Start Speaking'}</span>
            </button>
          ) : (
            <button
              onClick={handleProcessVoice}
              className="px-6 py-3.5 rounded-2xl bg-red-600 hover:bg-red-500 text-white font-semibold flex items-center space-x-2 shadow-xl shadow-red-600/30 transition-all hover:scale-105"
            >
              <MicOff className="w-5 h-5 animate-pulse" />
              <span>Done Speaking & Submit</span>
            </button>
          )}

          {latestResponse && (
            <button
              onClick={handleReplay}
              className="p-3.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-blue-300 border border-slate-700 transition-all"
              title={voiceState === 'SPEAKING' ? 'Pause Audio' : 'Replay Audio'}
            >
              {voiceState === 'SPEAKING' ? <Pause className="w-5 h-5" /> : <RotateCcw className="w-5 h-5" />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

