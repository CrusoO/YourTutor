import localFont from "next/font/local";

/*
 * Self-hosted (OFL-1.1, from @fontsource 5.3.0; licences and sources in app/font-files/). No request to Google at build or run time.
 * Latin subset for Latin faces, Devanagari subset for the two Noto Devanagari faces. Inter 400 reuses the file already shipped in public/fonts.
 */
export const instrumentSerif = localFont({
  src: [
    { path: "./font-files/instrument-serif-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./font-files/instrument-serif-latin-400-italic.woff2", weight: "400", style: "italic" },
  ],
  display: "swap",
  variable: "--font-instrument-serif",
});

export const inter = localFont({
  src: [
    { path: "../public/fonts/inter-latin-400.woff2", weight: "400", style: "normal" },
    { path: "./font-files/inter-latin-500-normal.woff2", weight: "500", style: "normal" },
  ],
  display: "swap",
  variable: "--font-inter",
});

export const notoSerifDevanagari = localFont({
  src: [
    { path: "./font-files/noto-serif-devanagari-devanagari-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./font-files/noto-serif-devanagari-devanagari-500-normal.woff2", weight: "500", style: "normal" },
  ],
  display: "swap",
  variable: "--font-noto-serif-deva",
});

/*
 * Interface text in Hindi and Nepali (sans, not the serif). Devanagari subset only; Latin letters in a Hindi screen come
 * from the Latin face in the stack. preload is off so English readers never download it: the browser fetches a file only
 * when a Devanagari glyph is drawn. Applied on <html> in app/layout.tsx.
 */
export const notoSansDevanagari = localFont({
  src: [
    { path: "./font-files/noto-sans-devanagari-devanagari-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./font-files/noto-sans-devanagari-devanagari-500-normal.woff2", weight: "500", style: "normal" },
  ],
  display: "swap",
  preload: false,
  variable: "--font-noto-sans-deva",
});
