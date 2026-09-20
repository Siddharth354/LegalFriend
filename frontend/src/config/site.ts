export const siteConfig: {
  readonly name: string;
  readonly apiBaseUrl: string;
} = {
  name: "Nyaya-Dost",
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
};
