"use client";

import { useRef, useState } from "react";
import { useCanUseLiveCamera } from "@/shared/hooks/useCanUseLiveCamera";
import type { UiStrings } from "@/shared/lib/uiStrings";
import { CameraCapture } from "@/shared/ui/CameraCapture";
import { CameraIcon, MicIcon } from "@/shared/ui/icons";

type ArriveScreenProps = {
  readonly strings: UiStrings;
  readonly onStart: () => void;
  readonly onPhotoCaptured: (image: Blob) => void;
};

export function ArriveScreen({
  strings,
  onStart,
  onPhotoCaptured,
}: ArriveScreenProps): React.JSX.Element {
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const canUseLiveCamera = useCanUseLiveCamera();
  const [cameraOpen, setCameraOpen] = useState<boolean>(false);

  function handlePhotoClick(): void {
    if (canUseLiveCamera) {
      setCameraOpen(true);
    } else {
      cameraInputRef.current?.click();
    }
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>): void {
    const file: File | undefined = event.target.files?.[0];
    if (file) onPhotoCaptured(file);
  }

  function handleLiveCapture(image: Blob): void {
    setCameraOpen(false);
    onPhotoCaptured(image);
  }

  return (
    <section className="arrive-screen">
      <div className="arrive-intro">
        <p className="arrive-wordmark">{strings.appName}</p>
        <p className="arrive-tagline">{strings.tagline}</p>
      </div>
      <div className="arrive-actions">
        <button
          type="button"
          className="action-card action-card-primary"
          onClick={onStart}
        >
          <span className="action-card-icon">
            <MicIcon className="icon-sm" />
          </span>
          <span>
            <span className="action-card-title">{strings.speakLabel}</span>
            <span className="action-card-hint">{strings.speakHint}</span>
          </span>
        </button>
        <button
          type="button"
          className="action-card action-card-secondary"
          onClick={handlePhotoClick}
        >
          <span className="action-card-icon">
            <CameraIcon className="icon-sm" />
          </span>
          <span>
            <span className="action-card-title">{strings.photoLabel}</span>
            <span className="action-card-hint">{strings.photoHint}</span>
          </span>
        </button>
      </div>

      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
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
