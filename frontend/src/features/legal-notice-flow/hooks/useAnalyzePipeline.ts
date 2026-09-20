"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { ConversationTurn } from "@/features/legal-notice-flow/types";
import { ApiError, analyzeAudio, toAudioUrl } from "@/shared/lib/api-client";

type PipelineState = {
  readonly isLoading: boolean;
  readonly turns: readonly ConversationTurn[];
  readonly error: string | null;
};

export type AnalyzePipeline = PipelineState & {
  readonly submit: (audio: Blob, sessionId: string) => Promise<void>;
  readonly reset: () => void;
  readonly clearError: () => void;
};

const initialState: PipelineState = {
  isLoading: false,
  turns: [],
  error: null,
};

export function useAnalyzePipeline(): AnalyzePipeline {
  const [state, setState] = useState<PipelineState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  useEffect((): (() => void) => {
    return (): void => abortRef.current?.abort();
  }, []);

  const submit = useCallback(
    async (audio: Blob, sessionId: string): Promise<void> => {
      abortRef.current?.abort();
      const controller: AbortController = new AbortController();
      abortRef.current = controller;

      setState(
        (current: PipelineState): PipelineState => ({
          ...current,
          isLoading: true,
          error: null,
        }),
      );
      try {
        const result = await analyzeAudio(audio, sessionId, controller.signal);
        const turn: ConversationTurn = {
          id: crypto.randomUUID(),
          result,
          audioUrl: toAudioUrl(result.advice.audio_payload_b64),
        };
        setState(
          (current: PipelineState): PipelineState => ({
            isLoading: false,
            turns: [...current.turns, turn],
            error: null,
          }),
        );
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        const message: string =
          error instanceof ApiError
            ? error.userMessage
            : "Something went wrong. Please try again.";
        setState(
          (current: PipelineState): PipelineState => ({
            ...current,
            isLoading: false,
            error: message,
          }),
        );
      }
    },
    [],
  );

  const reset = useCallback((): void => {
    abortRef.current?.abort();
    for (const turn of state.turns) {
      if (turn.audioUrl) URL.revokeObjectURL(turn.audioUrl);
    }
    setState(initialState);
  }, [state.turns]);

  const clearError = useCallback((): void => {
    setState(
      (current: PipelineState): PipelineState => ({ ...current, error: null }),
    );
  }, []);

  return { ...state, submit, reset, clearError };
}
