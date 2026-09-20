import { siteConfig } from "@/config/site";
import {
  type AnalyzeResponse,
  analyzeResponseSchema,
  apiErrorSchema,
} from "@/features/legal-notice-flow/schemas/analyze.schema";

export class ApiError extends Error {
  public constructor(public readonly userMessage: string) {
    super(userMessage);
  }
}

export async function analyzeAudio(
  audio: Blob,
  sessionId: string,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  const formData: FormData = new FormData();
  formData.append("audio", audio, "question.webm");

  const response: Response = await fetch(
    `${siteConfig.apiBaseUrl}/api/v1/analyze/voice`,
    {
      method: "POST",
      headers: { "X-Session-Id": sessionId },
      body: formData,
      signal,
    },
  );

  const payload: unknown = await response.json().catch((): null => null);
  if (!response.ok) {
    const errorResult = apiErrorSchema.safeParse(payload);
    throw new ApiError(
      errorResult.success
        ? errorResult.data.error.message_user
        : "Something went wrong. Please try again.",
    );
  }

  return analyzeResponseSchema.parse(payload);
}

export function toAudioUrl(audioPayloadB64: string): string {
  const decoded: string = atob(audioPayloadB64);
  const buffer: ArrayBuffer = new ArrayBuffer(decoded.length);
  const bytes: Uint8Array = new Uint8Array(buffer);
  for (let index: number = 0; index < decoded.length; index += 1) {
    bytes[index] = decoded.charCodeAt(index);
  }
  const blob: Blob = new Blob([buffer], { type: detectAudioMimeType(bytes) });
  return URL.createObjectURL(blob);
}

function detectAudioMimeType(bytes: Uint8Array): string {
  const signature: string = String.fromCharCode(...bytes.slice(0, 4));
  if (signature === "RIFF") return "audio/wav";
  if (signature === "OggS") return "audio/ogg";
  if (signature === "ID3") return "audio/mpeg";
  if (
    bytes[0] === 0x1a &&
    bytes[1] === 0x45 &&
    bytes[2] === 0xdf &&
    bytes[3] === 0xa3
  )
    return "audio/webm";
  return "audio/mpeg";
}
