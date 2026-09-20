"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type RecorderState = "idle" | "recording" | "error";

export const MAX_RECORDING_SECONDS = 28;

export type Recorder = {
  readonly state: RecorderState;
  readonly error: string | null;
  readonly elapsedSeconds: number;
  readonly start: () => Promise<void>;
  readonly stop: () => Promise<Blob>;
  readonly cancel: () => void;
};

export function useRecorder(): Recorder {
  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const releaseStream = useCallback((): void => {
    for (const track of streamRef.current?.getTracks() ?? []) track.stop();
    streamRef.current = null;
    recorderRef.current = null;
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  }, []);

  useEffect((): (() => void) => {
    return (): void => releaseStream();
  }, [releaseStream]);

  const start = useCallback(async (): Promise<void> => {
    try {
      const stream: MediaStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      const recorder: MediaRecorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event: BlobEvent): void => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = (): void => {
        setError("Recording stopped unexpectedly. Please try again.");
        setState("error");
        releaseStream();
      };
      recorderRef.current = recorder;
      streamRef.current = stream;
      recorder.start();
      setError(null);
      setElapsedSeconds(0);
      setState("recording");
      timerRef.current = setInterval((): void => {
        setElapsedSeconds((current: number): number => current + 1);
      }, 1000);
    } catch {
      setError("Microphone access is needed to ask your question.");
      setState("error");
    }
  }, [releaseStream]);

  const stop = useCallback(async (): Promise<Blob> => {
    const recorder: MediaRecorder | null = recorderRef.current;
    if (recorder?.state !== "recording")
      throw new Error("No active recording.");

    const recording: Blob = await new Promise<Blob>(
      (resolve: (value: Blob) => void): void => {
        recorder.onstop = (): void => {
          const audio: Blob = new Blob(chunksRef.current, {
            type: recorder.mimeType || "audio/webm",
          });
          resolve(audio);
        };
        recorder.stop();
      },
    );
    releaseStream();
    setState("idle");
    setElapsedSeconds(0);
    return recording;
  }, [releaseStream]);

  const cancel = useCallback((): void => {
    releaseStream();
    setState("idle");
    setElapsedSeconds(0);
  }, [releaseStream]);

  return { state, error, elapsedSeconds, start, stop, cancel };
}
