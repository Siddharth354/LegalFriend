"use client";

import type { Citation as CitationSource } from "@/features/legal-notice-flow/schemas/analyze.schema";
import { resolveSourceUrl } from "@/shared/lib/citationSources";

export function Citation({
  index,
  source,
}: {
  readonly index: number;
  readonly source: CitationSource | undefined;
}): React.JSX.Element {
  if (!source) return <sup className="citation-marker">[{index}]</sup>;

  const url: string | null = resolveSourceUrl(source.citation_string);

  if (!url) {
    return (
      <span
        className="citation-marker citation-marker-inert"
        title={source.citation_string}
      >
        [{index}]
        <span className="visually-hidden">
          {" "}
          — {source.citation_string} — source link unavailable
        </span>
      </span>
    );
  }

  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className="citation-marker"
      title={source.citation_string}
      aria-label={`Citation ${index} — ${source.citation_string}`}
    >
      [{index}]
    </a>
  );
}
