import localFont from "next/font/local";

/*
 * Self-hosted (OFL-1.1, from @fontsource 5.3.0; licences and sources in app/font-files/). No request to Google at build or run time.
 * Latin subset for Latin faces, Devanagari subset for Noto Serif Devanagari. Inter 400 reuses the file already shipped in public/fonts.
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
