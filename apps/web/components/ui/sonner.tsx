"use client";

import { Toaster as Sonner, toast } from "sonner";

/** Toast host. Theme follows the system; messages are short and never blame the student. */
function Toaster() {
  return <Sonner theme="system" position="bottom-center" closeButton />;
}

export { Toaster, toast };
