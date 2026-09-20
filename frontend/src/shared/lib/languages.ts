export const APP_LANGUAGES = [
  { code: "en-IN", native: "English", gloss: "English" },
  { code: "hi-IN", native: "हिंदी", gloss: "Hindi" },
  { code: "bn-IN", native: "বাংলা", gloss: "Bengali" },
  { code: "gu-IN", native: "ગુજરાતી", gloss: "Gujarati" },
  { code: "kn-IN", native: "ಕನ್ನಡ", gloss: "Kannada" },
  { code: "ml-IN", native: "മലയാളം", gloss: "Malayalam" },
  { code: "mr-IN", native: "मराठी", gloss: "Marathi" },
  { code: "od-IN", native: "ଓଡ଼ିଆ", gloss: "Odia" },
  { code: "pa-IN", native: "ਪੰਜਾਬੀ", gloss: "Punjabi" },
  { code: "ta-IN", native: "தமிழ்", gloss: "Tamil" },
  { code: "te-IN", native: "తెలుగు", gloss: "Telugu" },
] as const;

export type AppLanguageCode = (typeof APP_LANGUAGES)[number]["code"];

export const DEFAULT_APP_LANGUAGE: AppLanguageCode = "en-IN";
