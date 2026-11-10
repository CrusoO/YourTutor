"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import ReviewItemCard from "@/components/staff/ReviewItemCard";
import { reviewItems, staffToken, type ReviewCard } from "@/lib/api";
import { useCopy } from "@/lib/locale";

type Copy = Record<string, string>;

/** Staff only (teacher or admin): approve, reject or send back draft content items. */
export default function ReviewPage() {
  const router = useRouter();
  const copy = useCopy() as unknown as Copy;
  const [cards, setCards] = useState<ReviewCard[]>([]);
  const [total, setTotal] = useState(0);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!staffToken()) {
      router.push("/staff/login");
      return;
    }
    reviewItems()
      .then((data) => {
        setCards(data.items);
        setTotal(data.total);
        setLoaded(true);
      })
      .catch(() => router.push("/staff/login"));
  }, [router]);

  async function more() {
    const data = await reviewItems(cards.length);
    setCards((rows) => [...rows, ...data.items]);
    setTotal(data.total);
  }

  function decided(next: ReviewCard) {
    // an item that now has its two approvals, or a reject or fix, leaves the pending list
    const done = next.blocked || next.approvals >= next.approvals_needed;
    setCards((rows) => (done ? rows.filter((r) => r.id !== next.id) : rows.map((r) => (r.id === next.id ? next : r))));
  }

  return (
    <main className="stack" data-testid="review-page">
      <h1>{copy.reviewTitle}</h1>
      <p className="muted">{copy.reviewIntro}</p>
      {loaded && cards.length === 0 ? <p>{copy.reviewEmpty}</p> : null}
      {cards.map((card) => (
        <ReviewItemCard key={card.id} card={card} onDecided={decided} />
      ))}
      {cards.length < total ? (
        <button type="button" className="secondary" onClick={() => void more()}>
          {copy.reviewMore}
        </button>
      ) : null}
      <Link href="/teacher">{copy.reviewBack}</Link>
    </main>
  );
}
