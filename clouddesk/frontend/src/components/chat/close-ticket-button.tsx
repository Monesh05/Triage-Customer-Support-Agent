"use client";

// name: components/chat/close-ticket-button.tsx
// purpose: Customer self-service "Close ticket" action on the ticket detail page (post-launch,
//          2026-09-25). Mirrors components/console/approval-queue.tsx's authenticated
//          client-side POST pattern exactly: the JWT lives in an httpOnly cookie invisible to
//          client-side JS, so this calls the typed API client (which routes browser calls through
//          the same-origin proxy at app/api/backend/[...path]/route.ts) rather than attaching an
//          Authorization header itself, and surfaces the real outcome via a toast.
// author: CloudDesk Team
// date: 2026-09-25

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { closeTicket } from "@/lib/api/tickets";

export function CloseTicketButton({ ticketId }: { ticketId: string }) {
  const router = useRouter();
  const [isClosing, setIsClosing] = useState(false);

  async function handleClose(): Promise<void> {
    setIsClosing(true);
    try {
      await closeTicket(ticketId);
      toast.success("Ticket closed", { description: "This ticket has been marked as closed." });
      router.refresh();
    } catch (cause) {
      toast.error("Could not close this ticket", {
        description: cause instanceof ApiError ? cause.detail : "Unknown error",
      });
    } finally {
      setIsClosing(false);
    }
  }

  return (
    <Button size="sm" onClick={handleClose} disabled={isClosing} className="gap-1.5">
      {isClosing ? <Loader2 className="size-3.5 animate-spin" /> : <CheckCircle2 className="size-3.5" />}
      Close ticket
    </Button>
  );
}
