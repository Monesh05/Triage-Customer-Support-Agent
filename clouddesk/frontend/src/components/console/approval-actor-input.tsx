"use client";

// name: components/console/approval-actor-input.tsx
// purpose: The reviewer identity field for the Approval Queue. There is no auth yet (Phase 10),
//          so this is a plain, explicit text input (not a fake login) identifying who is
//          approving/rejecting — sent as `actor` on every decision call.
// author: CloudDesk Team
// date: 2026-09-24

import { UserCog } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ApprovalActorInput({
  actor,
  onChange,
}: {
  actor: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor="approval-actor" className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <UserCog className="size-4" />
        Reviewing as
      </Label>
      <Input
        id="approval-actor"
        value={actor}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 w-48"
        placeholder="support_console"
      />
    </div>
  );
}
