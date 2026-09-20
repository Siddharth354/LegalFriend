const ACT_SOURCE_URLS: readonly [RegExp, string][] = [
  [
    /BNS/i,
    "https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf",
  ],
  [
    /RBI.*Digital Lending/i,
    "https://www.rbi.org.in/scripts/NotificationUser.aspx?Id=12848&Mode=0",
  ],
  [
    /Negotiable Instruments/i,
    "https://www.indiacode.nic.in/bitstream/123456789/15327/1/negotiable_instruments_act,_1881.pdf",
  ],
];

export function resolveSourceUrl(citationString: string): string | null {
  for (const [pattern, url] of ACT_SOURCE_URLS) {
    if (pattern.test(citationString)) return url;
  }
  return null;
}
