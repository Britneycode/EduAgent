"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { getToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface VoiceInputProps {
  onResult: (text: string) => void;
  disabled?: boolean;
}

// 浏览器原生语音识别
function supportsSpeechRecognition(): boolean {
  return !!(typeof window !== "undefined" &&
    ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition));
}

export function VoiceInput({ onResult, disabled }: VoiceInputProps) {
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interim, setInterim] = useState("");
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  const startListening = useCallback(() => {
    setError(null);
    setInterim("");

    if (supportsSpeechRecognition()) {
      // 方案1：浏览器原生语音识别（Chrome/Edge）
      const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SR();
      recognition.lang = "zh-CN";
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event: any) => {
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

      recognition.onerror = (event: any) => {
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
      // 方案2：录音后调用 DashScope Paraformer API
      startRecordingForASR();
    }
  }, [onResult]);

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

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

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
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
        {listening ? "停止" : "语音"}
      </button>
      {error && (
        <span className="absolute -bottom-5 left-0 whitespace-nowrap text-[10px] text-red-500">{error}</span>
      )}
    </div>
  );
}
