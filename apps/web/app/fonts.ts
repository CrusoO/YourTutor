import { Instrument_Serif, Inter, Noto_Serif_Devanagari } from "next/font/google";

export const instrumentSerif = Instrument_Serif({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-instrument-serif",
});

export const inter = Inter({
  weight: ["400", "500"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const notoSerifDevanagari = Noto_Serif_Devanagari({
  weight: ["400", "500"],
  subsets: ["devanagari"],
  display: "swap",
  variable: "--font-noto-serif-deva",
});
