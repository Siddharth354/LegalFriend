"use client";

import { useEffect, useRef, useState } from "react";
import { CloseIcon } from "@/shared/ui/icons";

type CameraCaptureProps = {
  readonly open: boolean;
  readonly onCapture: (image: Blob) => void;
  readonly onClose: () => void;
};

export function CameraCapture({
  open,
  onCapture,
  onClose,
}: CameraCaptureProps): React.JSX.Element | null {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect((): (() => void) | undefined => {
    if (!open) return undefined;
    let cancelled: boolean = false;

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" } })
      .then((stream: MediaStream): void => {
        if (cancelled) {
          for (const track of stream.getTracks()) track.stop();
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch((): void => setErrorMessage("कैमरा एक्सेस नहीं मिला। कृपया अनुमति दें।"));

    return (): void => {
      cancelled = true;
      for (const track of streamRef.current?.getTracks() ?? []) track.stop();
      streamRef.current = null;
      setErrorMessage(null);
    };
  }, [open]);

  function handleShutter(): void {
    const video: HTMLVideoElement | null = videoRef.current;
    if (!video || video.videoWidth === 0) return;

    const canvas: HTMLCanvasElement = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context: CanvasRenderingContext2D | null = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob: Blob | null): void => {
        if (blob) onCapture(blob);
      },
      "image/jpeg",
      0.92,
    );
  }

  if (!open) return null;

  return (
    <div className="camera-overlay">
      <button
        type="button"
        onClick={onClose}
        className="camera-close"
        aria-label="Close camera"
      >
        <CloseIcon className="icon-sm" />
      </button>

      {errorMessage ? (
        <div className="camera-error">
          <p>{errorMessage}</p>
        </div>
      ) : (
        <>
          <p className="eyebrow camera-eyebrow">DOCUMENT</p>
          <div className="camera-frame">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="camera-video"
            />
            <span className="camera-bracket camera-bracket-tl" />
            <span className="camera-bracket camera-bracket-tr" />
            <span className="camera-bracket camera-bracket-bl" />
            <span className="camera-bracket camera-bracket-br" />
          </div>
          <div className="camera-controls">
            <button
              type="button"
              onClick={handleShutter}
              className="record-button"
              aria-label="Take photo"
            />
            <p className="status">नोटिस की फोटो लें</p>
          </div>
        </>
      )}
    </div>
  );
}
