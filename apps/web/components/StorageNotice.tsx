"use client";

import { useEffect, useState } from "react";
import { storageMode } from "@/lib/api";
import { useCopy } from "@/lib/locale";

/** A small banner when the browser will not keep sign-in on the device (private mode, blocked site data). */
export default function StorageNotice() {
  const copy = useCopy();
  const [limited, setLimited] = useState(false);
  useEffect(() => setLimited(storageMode() !== "device"), []);
  if (!limited) return null;
  return (
    <p className="banner" role="status" data-testid="storage-notice">
      {copy.privateModeNotice}
    </p>
  );
}
