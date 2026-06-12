"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Mic, Square } from "lucide-react";
import { getToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface VoiceInputProps {
  onResult: (text: string) => void;
  disabled?: boolean;
}

interface SpeechRecognitionResultLike {
  isFinal: boolean;
  0: {
    transcript: string;
  };
}

interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: SpeechRecognitionResultLike;
  };
}

interface SpeechRecognitionErrorEventLike {
  error: string;
}

interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

interface SpeechRecognitionWindow extends Window {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
}

function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  const speechWindow = window as SpeechRecognitionWindow;
  return speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition || null;
}

// 浏览器原生语音识别
function supportsSpeechRecognition(): boolean {
  return typeof window !== "undefined" && Boolean(getSpeechRecognitionConstructor());
}

export function VoiceInput({ onResult, disabled }: VoiceInputProps) {
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interim, setInterim] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  const startRecordingForASR = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: mediaRecorder.mimeType });
        try {
          const token = getToken();
          const resp = await fetch(`${API_BASE}/api/resources/speech-recognize`, {
            method: "POST",
            headers: {
              Authorization: token ? `Bearer ${token}` : "",
              "Content-Type": "application/octet-stream",
            },
            body: blob,
          });
          if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || "识别失败");
          const data = await resp.json();
          if (data.text) onResult(data.text);
        } catch (e) {
          setError(e instanceof Error ? e.message : "语音识别失败");
        }
        setListening(false);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setListening(true);
    } catch {
      setError("无法访问麦克风");
    }
  }, [onResult]);

  const startListening = useCallback(() => {
    setError(null);
    setInterim("");

    if (supportsSpeechRecognition()) {
      const SpeechRecognition = getSpeechRecognitionConstructor();
      if (!SpeechRecognition) return;
      const recognition = new SpeechRecognition();
      recognition.lang = "zh-CN";
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        let final = "";
        let interimText = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            final += result[0].transcript;
          } else {
            interimText += result[0].transcript;
          }
        }
        if (final) {
          onResult(final);
          setInterim("");
        } else {
          setInterim(interimText);
        }
      };

      recognition.onerror = (event) => {
        if (event.error !== "no-speech") {
          setError(event.error === "not-allowed" ? "麦克风权限被拒绝" : `识别错误: ${event.error}`);
        }
        setListening(false);
      };

      recognition.onend = () => {
        setListening(false);
        setInterim("");
      };

      recognitionRef.current = recognition;
      recognition.start();
      setListening(true);
    } else {
      void startRecordingForASR();
    }
  }, [onResult, startRecordingForASR]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setListening(false);
    setInterim("");
  }, []);

  return (
    <div className="relative inline-flex items-center">
      {listening && interim && (
        <span className="mr-2 max-w-[120px] truncate text-xs text-[var(--color-terracotta)] animate-pulse">
          {interim}
        </span>
      )}
      <button
        type="button"
        onClick={listening ? stopListening : startListening}
        disabled={disabled}
        title={listening ? "点击停止" : "语音输入"}
        className={`inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs transition-all ${
          listening
            ? "animate-pulse bg-red-500 text-white ring-2 ring-red-300"
            : "text-[var(--color-warm-gray-500)] ring-1 ring-[var(--color-warm-gray-200)] hover:text-[var(--color-terracotta)] hover:ring-[var(--color-terracotta)]"
        } disabled:cursor-not-allowed disabled:opacity-50`}
      >
        {listening ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        {listening ? "停止" : "语音"}
      </button>
      {error && (
        <span className="absolute -bottom-5 left-0 whitespace-nowrap text-[10px] text-red-500">{error}</span>
      )}
    </div>
  );
}
