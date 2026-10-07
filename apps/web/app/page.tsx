"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";

export default function HomePage() {
  const router = useRouter();
  useEffect(() => {
    (async () => {
      // Login phase bypassed for local learning-flow testing (NEXT_PUBLIC_SKIP_LOGIN=true).
      if (skipLogin()) {
        await ensureDevStudent();
        router.replace("/subjects");
        return;
      }
      const token = localStorage.getItem("yt_token");
      router.replace(token ? "/subjects" : "/login");
    })().catch(() => router.replace("/login"));
  }, [router]);
  return <p>YourTutor</p>;
}
