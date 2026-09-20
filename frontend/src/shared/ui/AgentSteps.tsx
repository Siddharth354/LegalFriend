"use client";

import { useEffect, useRef, useState } from "react";

type StepDef = {
  readonly id: string;
  readonly label: string;
  readonly detail: string;
};

const STEPS: readonly StepDef[] = [
  {
    id: "intent",
    label: "Understanding your question",
    detail: "Working out what kind of help you need",
  },
  {
    id: "facts",
    label: "Noting the details",
    detail: "Lender, amount, and the nature of the threat",
  },
  {
    id: "retrieval",
    label: "Searching the law",
    detail: "Looking through the relevant statutes",
  },
  {
    id: "advocate",
    label: "Drafting your answer",
    detail: "Grounding the answer in what was found",
  },
  {
    id: "critic",
    label: "Double-checking the details",
    detail: "Making sure the answer matches the law",
  },
  {
    id: "judge",
    label: "Finalizing your answer",
    detail: "Confirming the citations before sending",
  },
];

const STEP_INTERVAL_MS = 2200;

type AgentStepsProps = {
  readonly active: boolean;
};

export function AgentSteps({
  active,
}: AgentStepsProps): React.JSX.Element | null {
  const [stepIndex, setStepIndex] = useState<number>(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect((): (() => void) | undefined => {
    if (!active) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return undefined;
    }
    setStepIndex(0);
    intervalRef.current = setInterval((): void => {
      setStepIndex((current: number): number =>
        Math.min(current + 1, STEPS.length - 1),
      );
    }, STEP_INTERVAL_MS);
    return (): void => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [active]);

  if (!active) return null;

  const revealed: readonly StepDef[] = STEPS.slice(0, stepIndex + 1);

  return (
    <div className="agent-steps">
      <div className="agent-steps-header">
        <span className="agent-steps-title">How I'm working on this</span>
        <span className="agent-steps-meta">{stepIndex} done</span>
      </div>
      {revealed.map((step: StepDef, index: number): React.JSX.Element => {
        const isRunning: boolean = index === stepIndex;
        return (
          <div
            className={`agent-step-row ${isRunning ? "lf-border-beam" : ""}`}
            data-beam={isRunning ? "on" : "off"}
            key={step.id}
          >
            <span className="agent-step-icon">
              {isRunning ? (
                <span className="agent-step-icon-running" />
              ) : (
                <span className="agent-step-icon-done">✓</span>
              )}
            </span>
            <span className="agent-step-label">
              {step.label}
              <span className="agent-step-detail">{step.detail}</span>
            </span>
            <span className={`agent-step-status ${isRunning ? "running" : ""}`}>
              {isRunning ? "Running" : "Done"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
