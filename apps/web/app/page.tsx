import type { Metadata } from "next";
import BrownieLanding from "./brownie/Landing";
import { landingContent } from "./brownie/content";

export const metadata: Metadata = {
  title: landingContent.metadata.title,
  description: landingContent.metadata.description,
  openGraph: {
    title: landingContent.metadata.title,
    description: landingContent.metadata.description,
    type: "website",
  },
};

export default function HomePage() {
  return <BrownieLanding />;
}
