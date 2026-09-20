"use client";

import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type {
  AnalyzeResponse,
  Citation as CitationType,
} from "@/features/legal-notice-flow/schemas/analyze.schema";
import type { ConversationTurn } from "@/features/legal-notice-flow/types";
import { useCanUseLiveCamera } from "@/shared/hooks/useCanUseLiveCamera";
import { rehypeCitations } from "@/shared/lib/rehypeCitations";
import {
  getSharedAudioElement,
  pauseTurnAudio,
  playTurnAudio,
} from "@/shared/lib/turnAudioPlayer";
import type { UiStrings } from "@/shared/lib/uiStrings";
import { AgentSteps } from "@/shared/ui/AgentSteps";
import { CameraCapture } from "@/shared/ui/CameraCapture";
import { Citation } from "@/shared/ui/Citation";
import { ErrorIllustration } from "@/shared/ui/ErrorIllustration";
import {
  CameraIcon,
  MicIcon,
  SpeakerIcon,
  StopIcon,
  UploadIcon,
} from "@/shared/ui/icons";
import { Orb } from "@/shared/ui/Orb";

type ConversationScreenProps = {
  readonly strings: UiStrings;
  readonly turns: readonly ConversationTurn[];
  readonly isRecording: boolean;
  readonly isThinking: boolean;
  readonly error: string | null;
  readonly elapsedSeconds: number;
  readonly maxRecordingSeconds: number;
  readonly onRecord: () => void;
  readonly onCameraCapture: (image: Blob) => void;
  readonly onFileUpload: (image: Blob) => void;
};

function splitHeadline(text: string): { headline: string; body: string } {
  const match = text.match(/^(.*?[.!?।])(\s|$)/);
  if (!match) return { headline: text.replace(/^[#*\s]+/, ""), body: "" };
  return {
    headline: match[1].replace(/^[#*\s]+/, ""),
    body: text.slice(match[0].length).trim(),
  };
}

function ErrorCard({
  message,
}: {
  readonly message: string;
}): React.JSX.Element {
  return (
    <div className="error-card">
      <ErrorIllustration />
      <p className="error-card-title">Hmm, that didn't go through</p>
      <p className="error-card-detail">{message}</p>
    </div>
  );
}

function citeIndex(children: ReactNode): number {
  const raw: string = Array.isArray(children)
    ? children.join("")
    : String(children ?? "");
  return Number.parseInt(raw, 10);
}

function VerdictCard({
  turn,
  isPlaying,
  autoplayFailed,
  onToggle,
}: {
  readonly turn: ConversationTurn;
  readonly isPlaying: boolean;
  readonly autoplayFailed: boolean;
  readonly onToggle: () => void;
}): React.JSX.Element {
  const result: AnalyzeResponse = turn.result;
  const { headline, body } = splitHeadline(result.advice.transcript);
  const topCitation: CitationType | undefined = result.citations[0];

  return (
    <div className="conversation-turn">
      {result.advice.verbatim_transcript.trim() ? (
        <p className="transcript user-turn">
          {result.advice.verbatim_transcript}
        </p>
      ) : null}
      <article className="verdict-card">
        <div className="verdict-headline-row">
          <h2 className="verdict-headline">{headline}</h2>
          {turn.audioUrl ? (
            <button
              type="button"
              className={`replay-control ${autoplayFailed && !isPlaying ? "prompt" : ""}`}
              onClick={onToggle}
              aria-label={
                isPlaying
                  ? "Pause reply audio"
                  : autoplayFailed
                    ? "Tap to hear the reply"
                    : "Replay reply audio"
              }
            >
              <SpeakerIcon className="icon-sm" />
            </button>
          ) : null}
        </div>
        {body ? (
          <div className="verdict-body">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeCitations]}
              components={{
                cite({ children }) {
                  const index: number = citeIndex(children);
                  return (
                    <Citation
                      index={index}
                      source={result.citations[index - 1]}
                    />
                  );
                },
              }}
            >
              {body}
            </ReactMarkdown>
          </div>
        ) : null}
        {topCitation ? (
          <p className="verdict-citation">{topCitation.citation_string}</p>
        ) : null}
        {result.citations.length > 1 ? (
          <details className="verdict-more-citations">
            <summary>Full citations ({result.citations.length})</summary>
            <div className="citations">
              {result.citations.map(
                (citation: CitationType): React.JSX.Element => (
                  <article
                    className="citation"
                    key={`${citation.citation_string}-${citation.score}`}
                  >
                    <strong>{citation.citation_string}</strong>
                    <span>{citation.content}</span>
                  </article>
                ),
              )}
            </div>
          </details>
        ) : null}
      </article>
    </div>
  );
}

export function ConversationScreen({
  strings,
  turns,
  isRecording,
  isThinking,
  error,
  elapsedSeconds,
  maxRecordingSeconds,
  onRecord,
  onCameraCapture,
  onFileUpload,
}: ConversationScreenProps): React.JSX.Element {
  const canUseLiveCamera = useCanUseLiveCamera();
  const [cameraOpen, setCameraOpen] = useState<boolean>(false);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const latestTurnRef = useRef<HTMLDivElement>(null);
  const stepsRef = useRef<HTMLDivElement>(null);
  const attemptedAutoplayIdsRef = useRef<Set<string>>(new Set());
  const [playingTurnId, setPlayingTurnId] = useState<string | null>(null);
  const [autoplayFailedId, setAutoplayFailedId] = useState<string | null>(null);

  useEffect((): (() => void) => {
    const audio: HTMLAudioElement = getSharedAudioElement();
    const handleEnded = (): void => setPlayingTurnId(null);
    const handlePause = (): void => setPlayingTurnId(null);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("pause", handlePause);
    return (): void => {
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("pause", handlePause);
    };
  }, []);

  useEffect((): void => {
    const latest: ConversationTurn | undefined = turns[turns.length - 1];
    if (!latest?.audioUrl) return;
    if (attemptedAutoplayIdsRef.current.has(latest.id)) return;
    attemptedAutoplayIdsRef.current.add(latest.id);
    playTurnAudio(latest.id, latest.audioUrl)
      .then((): void => setPlayingTurnId(latest.id))
      .catch((): void => setAutoplayFailedId(latest.id));
  }, [turns]);

  function toggleTurnAudio(turn: ConversationTurn): void {
    if (!turn.audioUrl) return;
    if (playingTurnId === turn.id) {
      pauseTurnAudio();
      return;
    }
    playTurnAudio(turn.id, turn.audioUrl)
      .then((): void => {
        setPlayingTurnId(turn.id);
        setAutoplayFailedId((current: string | null): string | null =>
          current === turn.id ? null : current,
        );
      })
      .catch((): void => undefined);
  }

  useEffect((): void => {
    if (!isRecording) {
      const target: HTMLDivElement | null = isThinking
        ? stepsRef.current
        : latestTurnRef.current;
      target?.scrollIntoView({ behavior: "auto", block: "start" });
    }
  }, [isRecording, isThinking]);

  useEffect((): (() => void) | undefined => {
    if (!isThinking) return undefined;
    const container: HTMLDivElement | null = stepsRef.current;
    if (!container) return undefined;
    const observer: ResizeObserver = new ResizeObserver((): void => {
      container.scrollIntoView({ behavior: "auto", block: "end" });
    });
    observer.observe(container);
    return (): void => observer.disconnect();
  }, [isThinking]);

  function handleCameraClick(): void {
    if (canUseLiveCamera) {
      setCameraOpen(true);
    } else {
      cameraInputRef.current?.click();
    }
  }

  function handleCameraChange(
    event: React.ChangeEvent<HTMLInputElement>,
  ): void {
    const file: File | undefined = event.target.files?.[0];
    if (file) onCameraCapture(file);
  }

  function handleLiveCapture(image: Blob): void {
    setCameraOpen(false);
    onCameraCapture(image);
  }

  function handleUploadChange(
    event: React.ChangeEvent<HTMLInputElement>,
  ): void {
    const file: File | undefined = event.target.files?.[0];
    if (file) onFileUpload(file);
  }

  const controlsDisabled: boolean = isRecording || isThinking;
  const secondsRemaining: number = maxRecordingSeconds - elapsedSeconds;

  return (
    <section className="listen-screen">
      {isRecording ? (
        <div className="listen-center">
          <Orb size={220} speed={1} />
          <p className="listen-status">{strings.listening}</p>
          <p
            className={`recording-timer ${secondsRemaining <= 5 ? "warning" : ""}`}
          >
            0:{elapsedSeconds.toString().padStart(2, "0")} / 0:
            {maxRecordingSeconds.toString().padStart(2, "0")}
          </p>
        </div>
      ) : (
        <div className="conversation-transcript">
          {turns.length === 0 && !isThinking ? (
            <div
              className="empty-state-center"
              role={error ? "alert" : undefined}
            >
              {error ? (
                <ErrorCard message={error} />
              ) : (
                <p className="listen-status">{strings.emptyState}</p>
              )}
            </div>
          ) : (
            <>
              {turns.map(
                (turn: ConversationTurn, index: number): React.JSX.Element => {
                  const isLatest: boolean = index === turns.length - 1;
                  return (
                    <div
                      key={turn.id}
                      ref={isLatest ? latestTurnRef : undefined}
                    >
                      <VerdictCard
                        turn={turn}
                        isPlaying={playingTurnId === turn.id}
                        autoplayFailed={autoplayFailedId === turn.id}
                        onToggle={(): void => toggleTurnAudio(turn)}
                      />
                    </div>
                  );
                },
              )}
              {isThinking ? (
                <div ref={stepsRef}>
                  <AgentSteps active={isThinking} />
                </div>
              ) : null}
              {error && !isThinking ? <ErrorCard message={error} /> : null}
            </>
          )}
        </div>
      )}

      <div className="listen-controls">
        <button
          type="button"
          className="camera-control"
          onClick={handleCameraClick}
          disabled={controlsDisabled}
          aria-label="Photograph the notice"
        >
          <CameraIcon className="icon-sm" />
        </button>
        <button
          type="button"
          className={`listen-record-control ${isRecording ? "recording" : ""}`}
          onClick={onRecord}
          disabled={isThinking}
          aria-label={
            isRecording ? "Stop recording and send" : "Start recording"
          }
          aria-pressed={isRecording}
        >
          {isRecording ? (
            <StopIcon className="icon-sm" />
          ) : (
            <MicIcon className="icon-sm" />
          )}
        </button>
        <button
          type="button"
          className="upload-control"
          onClick={(): void => uploadInputRef.current?.click()}
          disabled={controlsDisabled}
          aria-label="Upload a photo"
        >
          <UploadIcon className="icon-sm" />
        </button>
      </div>
      <div className="recording-progress" />

      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleCameraChange}
        className="hidden"
      />
      <input
        ref={uploadInputRef}
        type="file"
        accept="image/*"
        onChange={handleUploadChange}
        className="hidden"
      />

      <CameraCapture
        open={cameraOpen}
        onCapture={handleLiveCapture}
        onClose={(): void => setCameraOpen(false)}
      />
    </section>
  );
}
