import type { AnalyzeResponse } from "@/features/legal-notice-flow/schemas/analyze.schema";

export type FlowStage = "arrive" | "conversation";

export type Language = "en-IN" | "hi-IN";

export type ConversationTurn = {
  readonly id: string;
  readonly result: AnalyzeResponse;
  readonly audioUrl: string | null;
};
