import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
vi.mock("../../app/fonts", () => ({
  instrumentSerif: { variable: "" },
  inter: { variable: "" },
  notoSerifDevanagari: { variable: "" },
}));

import BrownieLanding from "../../app/brownie/Landing";
import { trust } from "../../app/brownie/landing-extras";
import GrievancePage, { metadata as grievanceMeta } from "../../app/grievance/page";
import PrivacyPage, { metadata as privacyMeta } from "../../app/privacy/page";
import TermsPage, { metadata as termsMeta } from "../../app/terms/page";
import { DRAFT_BANNER, PLACEHOLDER, SCHEDULE_PLACEHOLDER, grievance, inventory, legalLinks, privacy, terms } from "../../lib/legal-copy";
import { existsSync } from "node:fs";
import { join } from "node:path";

afterEach(cleanup);

const pages = [
  { name: "privacy", Page: PrivacyPage, meta: privacyMeta, title: "Brownie · Privacy", h1: privacy.title },
  { name: "terms", Page: TermsPage, meta: termsMeta, title: "Brownie · Terms", h1: terms.title },
  { name: "grievance", Page: GrievancePage, meta: grievanceMeta, title: "Brownie · Grievance", h1: grievance.title },
] as const;

describe.each(pages)("the $name page", ({ Page, meta, title, h1 }) => {
  it("shows the draft banner, the title and links to all three pages", () => {
    render(<Page />);
    expect(screen.getByTestId("draft-banner")).toHaveTextContent(DRAFT_BANNER);
    expect(DRAFT_BANNER).toBe("Draft: under legal review. Not yet in force.");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(h1);
    expect(meta.title).toBe(title);
    const nav = within(screen.getByTestId("legal-nav"));
    for (const link of legalLinks) expect(nav.getByRole("link", { name: link.label })).toHaveAttribute("href", link.href);
  });
});

describe("the links resolve to routes", () => {
  it("has a page file for every legal link", () => {
    for (const link of legalLinks) expect(existsSync(join(process.cwd(), "app", link.href.slice(1), "page.tsx")), link.href).toBe(true);
  });
});

describe("the privacy page", () => {
  it("has its key headings, including children and guardians, and rights", () => {
    render(<PrivacyPage />);
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual(expect.arrayContaining([
      privacy.sections.who.heading,
      privacy.sections.inventoryHeading,
      privacy.sections.children.heading,
      privacy.sections.rights.heading,
    ]));
  });

  it("describes every data category with all six facts, and a real retention statement", () => {
    render(<PrivacyPage />);
    expect(inventory.length).toBeGreaterThanOrEqual(15);
    for (const item of inventory) {
      const block = within(screen.getByTestId(`inventory-${item.id}`));
      for (const label of Object.values(privacy.fieldLabels)) expect(block.getByText(label), `${item.id} ${label}`).toBeInTheDocument();
      for (const key of ["what", "why", "where", "who", "kept", "thirdParty"] as const) expect(item[key].trim(), `${item.id}.${key}`).not.toBe("");
    }
  });

  it("states each retention period, and says honestly that the clean-up is not scheduled", () => {
    const kept = (id: string) => inventory.find((i) => i.id === id)!.kept;
    expect(SCHEDULE_PLACEHOLDER).toBe("[owner to confirm the scheduled job is running]");
    const periods: Record<string, RegExp> = {
      guest: /90 days/,
      code: /24 hours/,
      rate: /7 days/,
      tokens: /30 days after expiry/,
      llmlog: /14 days[\s\S]*90 days/,
      video: /30 days/,
    };
    for (const [id, re] of Object.entries(periods)) {
      expect(kept(id), id).toMatch(re);
      expect(kept(id), id).toContain(SCHEDULE_PLACEHOLDER);
      expect(kept(id), id).not.toMatch(/removed automatically|deleted automatically/i);
    }
    expect(JSON.stringify(privacy.sections.short)).toContain(SCHEDULE_PLACEHOLDER);
  });

  it("keeps the schedule placeholder on the rendered page", () => {
    render(<PrivacyPage />);
    expect(screen.getAllByText(new RegExp(SCHEDULE_PLACEHOLDER.replace(/[[\]]/g, "\$&"))).length).toBeGreaterThanOrEqual(7);
  });

  it("states the data that has no time rule, and the gaps that remain", () => {
    const kept = (id: string) => inventory.find((i) => i.id === id)!.kept;
    for (const id of ["safety", "group", "report", "teacher", "learner"]) expect(kept(id), id).toMatch(/no time rule/i);
    expect(kept("ai")).toMatch(/do not store the text/i);
    expect(kept("research")).toMatch(/deleted together with the learner/i);
    expect(kept("research")).toContain(PLACEHOLDER);
    expect(kept("logs")).toMatch(/backups/i);
    expect(kept("logs")).toMatch(/Neon, R2/);
    expect(inventory.find((i) => i.id === "video")!.what).toMatch(/source and story text/i);
    expect(inventory.find((i) => i.id === "ai")!.thirdParty).toContain(PLACEHOLDER);
  });

  it("describes export and delete as they work, and says teacher accounts have no self-service", () => {
    const rights = privacy.sections.rights.body.join(" ");
    expect(rights).toMatch(/sessions, answers, progress and mastery, review cards, lesson records, safety flags/);
    expect(rights).toMatch(/PIN hash, the family code, server file paths and keys/);
    expect(rights).toMatch(/sign-in code rows[\s\S]*research rows[\s\S]*video jobs and their files/);
    expect(rights).toMatch(/guest can download and delete their own data/);
    expect(rights).toMatch(/teacher and class-owner accounts have no self-service export or delete/i);
    expect(rights).toMatch(/Anthropic/);
    expect(rights).not.toMatch(/export does not include/i);
    expect(JSON.stringify(inventory.find((i) => i.id === "account"))).toMatch(/no self-service export or delete/);
  });

  it("does not claim compliance the code lacks", () => {
    const text = JSON.stringify(privacy);
    expect(text).not.toMatch(/\bwe (are|is) (fully )?compliant\b|complies with|verified parental consent is in place/i);
    expect(privacy.sections.children.today.join(" ")).toMatch(/no age check yet/i);
  });

  it("keeps the owner placeholders", () => {
    render(<PrivacyPage />);
    expect(screen.getAllByText(new RegExp(PLACEHOLDER.replace(/[[\]]/g, "\$&"))).length).toBeGreaterThanOrEqual(3);
  });
});

describe("the terms page", () => {
  it("covers wrong answers, no teacher substitute, no emergency service, age, acceptable use, and leaves the liability text to counsel", () => {
    render(<TermsPage />);
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    for (const id of ["wrong", "teacher", "emergency", "age", "use", "limit"]) {
      expect(headings).toContain(terms.sections.find((s) => s.id === id)!.heading);
    }
    expect(screen.getByText(/checked by calculation|check a maths answer by calculation/i)).toBeInTheDocument();
    expect(screen.getAllByText(new RegExp("\[owner to supply\]")).length).toBeGreaterThanOrEqual(3);
  });
});

describe("the grievance page", () => {
  it("shows every contact field as a placeholder and never a made-up contact", () => {
    render(<GrievancePage />);
    for (const field of grievance.contact.fields) expect(screen.getByTestId(`contact-${field.id}`)).toHaveTextContent(PLACEHOLDER);
    expect(screen.getByTestId("reply-time")).toHaveTextContent(PLACEHOLDER);
    expect(screen.getByRole("heading", { name: grievance.send.heading })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: grievance.process.heading })).toBeInTheDocument();
  });

  it("has no email address, phone number or helpline number anywhere in the legal copy", () => {
    const all = JSON.stringify({ privacy, terms, grievance, inventory });
    expect(all).not.toMatch(/[\w.+-]+@[\w-]+\.[\w.]+/);
    expect(all).not.toMatch(/\d{5,}|\d{3,}[ -]\d{3,}/);
    expect(all).not.toMatch(/https?:\/\//);
  });
});

describe("links from the landing page", () => {
  it("links the footer to all three pages", () => {
    window.history.replaceState({}, "", "/");
    render(<BrownieLanding />);
    const footer = within(screen.getByTestId("footer-legal"));
    for (const link of legalLinks) expect(footer.getByRole("link", { name: link.label })).toHaveAttribute("href", link.href);
  });

  it("points the remember and child answers at the privacy page and keeps them pending", () => {
    const rows = trust.items.filter((i) => "link" in i);
    expect(rows.map((i) => i.id)).toEqual(["remember", "child"]);
    for (const row of rows) {
      expect("pending" in row && row.pending, row.id).toBe(true);
      expect("link" in row && row.link.href).toBe("/privacy");
    }
    window.history.replaceState({}, "", "/");
    render(<BrownieLanding />);
    const link = within(screen.getByTestId("trust-remember")).getByRole("link", { name: /privacy page/i });
    expect(link).toHaveAttribute("href", "/privacy");
  });
});
