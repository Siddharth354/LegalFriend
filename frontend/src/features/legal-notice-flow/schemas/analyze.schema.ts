import { z } from "zod";

export const citationSchema = z.object({
  citation_string: z.string(),
  content: z.string(),
  score: z.number(),
});

export const analyzeResponseSchema = z.object({
  summary_card: z.string(),
  citations: z.array(citationSchema),
  advice: z.object({
    language: z.string(),
    transcript: z.string(),
    verbatim_transcript: z.string(),
    audio_payload_b64: z.string(),
  }),
});

export const apiErrorSchema = z.object({
  error: z.object({
    stage: z.string(),
    message_en: z.string(),
    message_user: z.string(),
  }),
});

export type AnalyzeResponse = z.infer<typeof analyzeResponseSchema>;
export type Citation = z.infer<typeof citationSchema>;
