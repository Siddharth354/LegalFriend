"use client";

import { useCallback, useEffect, useState } from "react";
import type { AppLanguageCode } from "@/shared/lib/languages";
import { unlockTurnAudio } from "@/shared/lib/turnAudioPlayer";
import { useUiLanguage } from "@/shared/lib/useUiLanguage";
import { BackIcon, PlusIcon } from "@/shared/ui/icons";
import { LanguageSwitcher } from "@/shared/ui/LanguageSwitcher";
import { ThemeToggle } from "@/shared/ui/ThemeToggle";
import { ArriveScreen } from "./components/ArriveScreen";
import { ConversationScreen } from "./components/ConversationScreen";
import { useAnalyzePipeline } from "./hooks/useAnalyzePipeline";
import { MAX_RECORDING_SECONDS, useRecorder } from "./hooks/useRecorder";
import type { FlowStage } from "./types";

const sessionStorageKey: string = "legalfriend-session-id";

function getSessionId(): string {
  const existing: string | null = localStorage.getItem(sessionStorageKey);
  if (existing) return existing;
  const created: string = crypto.randomUUID();
  localStorage.setItem(sessionStorageKey, created);
  return created;
}

export function LegalNoticeFlow(): React.JSX.Element {
  const [stage, setStage] = useState<FlowStage>("arrive");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [, setDocumentImage] = useState<Blob | null>(null);
  const recorder = useRecorder();
  const pipeline = useAnalyzePipeline();
  const { language, setLanguage, strings } = useUiLanguage();

  useEffect((): void => setSessionId(getSessionId()), []);

  const handleRecord = useCallback(async (): Promise<void> => {
    if (recorder.state !== "recording") {
      unlockTurnAudio();
      pipeline.clearError();
      await recorder.start();
      return;
    }
    const audio: Blob = await recorder.stop();
    if (sessionId) await pipeline.submit(audio, sessionId);
  }, [
    recorder.state,
    recorder.start,
    recorder.stop,
    pipeline.clearError,
    pipeline.submit,
    sessionId,
  ]);

  useEffect((): void => {
    if (
      recorder.state === "recording" &&
      recorder.elapsedSeconds >= MAX_RECORDING_SECONDS
    ) {
      void handleRecord();
    }
  }, [recorder.state, recorder.elapsedSeconds, handleRecord]);

  const startVoice = async (): Promise<void> => {
    unlockTurnAudio();
    pipeline.clearError();
    setStage("conversation");
    await recorder.start();
  };

  const handlePhotoCaptured = async (image: Blob): Promise<void> => {
    unlockTurnAudio();
    pipeline.clearError();
    setDocumentImage(image);
    setStage("conversation");
    await recorder.start();
  };

  const goBack = (): void => {
    if (recorder.state === "recording") recorder.cancel();
    setStage("arrive");
  };

  const restart = (): void => {
    if (recorder.state === "recording") recorder.cancel();
    const nextSessionId: string = crypto.randomUUID();
    localStorage.setItem(sessionStorageKey, nextSessionId);
    setSessionId(nextSessionId);
    setDocumentImage(null);
    pipeline.reset();
    setStage("arrive");
  };

  return (
    <main className="flow">
      <div className="flow-chrome">
        {stage !== "arrive" ? (
          <button
            type="button"
            className="chrome-back"
            onClick={goBack}
            aria-label="Back to start"
          >
            <BackIcon className="icon-sm" />
          </button>
        ) : (
          <span className="chrome-back-spacer" aria-hidden="true" />
        )}
        <div className="chrome-right">
          {stage === "conversation" && pipeline.turns.length > 0 ? (
            <button
              type="button"
              className="chrome-globe"
              onClick={restart}
              aria-label="Start a new conversation"
            >
              <PlusIcon className="icon-sm" />
            </button>
          ) : null}
          <LanguageSwitcher
            language={language}
            onSelect={(code: AppLanguageCode): void => setLanguage(code)}
          />
          <ThemeToggle />
        </div>
      </div>

      {stage === "arrive" ? (
        <ArriveScreen
          strings={strings}
          onStart={(): void => void startVoice()}
          onPhotoCaptured={(image: Blob): void =>
            void handlePhotoCaptured(image)
          }
        />
      ) : null}
      {stage === "conversation" ? (
        <ConversationScreen
          strings={strings}
          turns={pipeline.turns}
          isRecording={recorder.state === "recording"}
          isThinking={pipeline.isLoading}
          error={recorder.error ?? pipeline.error}
          elapsedSeconds={recorder.elapsedSeconds}
          maxRecordingSeconds={MAX_RECORDING_SECONDS}
          onRecord={(): void => void handleRecord()}
          onCameraCapture={(image: Blob): void => setDocumentImage(image)}
          onFileUpload={(image: Blob): void => setDocumentImage(image)}
        />
      ) : null}
    </main>
  );
}
