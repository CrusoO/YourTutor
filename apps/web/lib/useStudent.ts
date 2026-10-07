"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { setStudentId, today } from "@/lib/api";

export type StudentToday = {
  student_id: string;
  display_name: string;
  remaining_active_minutes: number;
  resume?: { session_id: string; type: string; resumable?: boolean } | null;
};

/** The signed-in student, or a redirect to /login when there is no valid token. */
export function useStudent(): StudentToday | null {
  const router = useRouter();
  const [student, setStudent] = useState<StudentToday | null>(null);
  useEffect(() => {
    let live = true;
    ensureDevStudent()
      .then(() => today())
      .then((row: StudentToday) => {
        if (!live) return;
        setStudentId(row.student_id);
        setStudent(row);
      })
      .catch(() => {
        if (!skipLogin()) router.push("/login");
      });
    return () => {
      live = false;
    };
  }, [router]);
  return student;
}
