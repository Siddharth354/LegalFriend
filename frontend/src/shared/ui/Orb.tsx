"use client";

import { useEffect, useRef } from "react";

type OrbProps = {
  readonly size?: number;
  readonly speed?: number;
};

const HEX_RE = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i;

function hexToRgba(hex: string, alpha: number): string {
  const match: RegExpMatchArray | null = hex.trim().match(HEX_RE);
  if (!match) return `rgba(0,0,0,${alpha})`;

  const clean: string = match[1];
  const full: string =
    clean.length === 3
      ? clean
          .split("")
          .map((c: string): string => c + c)
          .join("")
      : clean;
  const r: number = Number.parseInt(full.substring(0, 2), 16);
  const g: number = Number.parseInt(full.substring(2, 4), 16);
  const b: number = Number.parseInt(full.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

export function Orb({ size = 220, speed = 1 }: OrbProps): React.JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect((): (() => void) => {
    const canvas: HTMLCanvasElement | null = canvasRef.current;
    if (!canvas) return (): void => undefined;

    const dpr: number = window.devicePixelRatio || 1;
    const pixelSize: number = size * dpr;
    canvas.width = pixelSize;
    canvas.height = pixelSize;

    const context: CanvasRenderingContext2D | null = canvas.getContext("2d");
    if (!context) return (): void => undefined;

    const cx: number = pixelSize / 2;
    const cy: number = pixelSize / 2;
    const base: number = pixelSize * 0.16;
    let t: number = Math.random() * 100;
    let frameId: number = 0;

    const reduceMotion: boolean = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const root: HTMLElement = document.documentElement;

    function orbColor(): string {
      const value: string = getComputedStyle(root)
        .getPropertyValue("--ink")
        .trim();
      return HEX_RE.test(value) ? value : "#000000";
    }

    function render(): void {
      if (!context) return;
      context.clearRect(0, 0, pixelSize, pixelSize);
      const color: string = orbColor();
      const breathe: number = Math.sin(t) * pixelSize * 0.012;
      const r1: number = base + breathe;

      const layers: readonly [number, number][] = [
        [base * 4.4, 0.05],
        [base * 3.2, 0.08],
        [base * 2.2, 0.14],
        [r1 * 1.5, 0.26],
      ];
      for (const [radius, alpha] of layers) {
        const gradient: CanvasGradient = context.createRadialGradient(
          cx,
          cy,
          0,
          cx,
          cy,
          radius,
        );
        gradient.addColorStop(0, hexToRgba(color, alpha));
        gradient.addColorStop(1, hexToRgba(color, 0));
        context.fillStyle = gradient;
        context.beginPath();
        context.arc(cx, cy, radius, 0, Math.PI * 2);
        context.fill();
      }

      const core: CanvasGradient = context.createRadialGradient(
        cx - r1 * 0.28,
        cy - r1 * 0.32,
        r1 * 0.04,
        cx,
        cy,
        r1,
      );
      core.addColorStop(0, hexToRgba(color, 0.98));
      core.addColorStop(0.7, hexToRgba(color, 0.9));
      core.addColorStop(1, hexToRgba(color, 0.72));
      context.fillStyle = core;
      context.beginPath();
      context.arc(cx, cy, r1, 0, Math.PI * 2);
      context.fill();

      t += 0.016 * speed;
      if (!reduceMotion) frameId = requestAnimationFrame(render);
    }

    render();
    return (): void => cancelAnimationFrame(frameId);
  }, [size, speed]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: size, height: size }}
      aria-label="Voice indicator"
    />
  );
}
