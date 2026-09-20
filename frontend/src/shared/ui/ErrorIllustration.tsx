export function ErrorIllustration(): React.JSX.Element {
  return (
    <svg
      viewBox="0 0 96 96"
      width="72"
      height="72"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M28 20h32l8 8v40a4 4 0 0 1-4 4H28a4 4 0 0 1-4-4V24a4 4 0 0 1 4-4Z"
        stroke="var(--ink)"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M60 20v8h8"
        stroke="var(--ink)"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M34 46c3-4 6-4 9 0s6 4 9 0 6-4 9 0"
        stroke="var(--ink)"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.55"
      />
      <path
        d="M34 58h20"
        stroke="var(--ink)"
        strokeWidth="1.7"
        strokeLinecap="round"
        opacity="0.3"
      />
      <circle cx="68" cy="66" r="6" fill="var(--danger)" />
      <path
        d="M68 63v3.5M68 69v.1"
        stroke="var(--paper)"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}
