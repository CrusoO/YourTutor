import { redirect } from "next/navigation";

type Item = {
  id: string;
  stem: string;
  type: string;
  options: { id?: string; en?: string }[];
};

async function loadForm(
  checkpointId: string,
  form: string,
  cookieHeader: string | undefined
): Promise<{ items: Item[]; html?: string } | null> {
  const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const response = await fetch(`${api}/checkpoints/${checkpointId}/forms/${form}`, {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
    redirect: "manual",
  });
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export default async function ComparisonCheckpointPage({
  params,
  searchParams,
}: {
  params: Promise<{ checkpointId: string; form: string }>;
  searchParams: Promise<{ token?: string }>;
}) {
  const { checkpointId, form } = await params;
  const { token } = await searchParams;
  const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  if (token) {
    redirect(`${api}/checkpoints/${encodeURIComponent(checkpointId)}/forms/${encodeURIComponent(form)}?token=${encodeURIComponent(token)}`);
  }
  const { cookies, headers } = await import("next/headers");
  const store = await cookies();
  const cookieHeader = (await headers()).get("cookie") || store.toString();
  const data = await loadForm(checkpointId, form, cookieHeader || undefined);
  return (
    <main style={{ maxWidth: "40rem", margin: "1.5rem auto", fontFamily: "sans-serif" }}>
      <h1>
        Checkpoint {checkpointId} — Form {form}
      </h1>
      <p>Comparison form. No tutor session.</p>
      <p>Open the assignment link you were given. The token is exchanged for a cookie and removed from the URL.</p>
      {data === null && <p>This link is invalid or expired.</p>}
      {data?.items.map((item, index) => (
        <section key={item.id} style={{ marginBottom: "1.5rem" }}>
          <h2>
            {index + 1}. {item.stem}
          </h2>
          {item.options?.length ? (
            <ol type="a">
              {item.options.map((opt) => (
                <li key={opt.id}>{opt.en}</li>
              ))}
            </ol>
          ) : (
            <p>Answer: ________</p>
          )}
        </section>
      ))}
    </main>
  );
}
