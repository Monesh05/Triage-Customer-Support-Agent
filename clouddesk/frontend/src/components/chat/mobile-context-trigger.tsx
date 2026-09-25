"use client";

// name: components/chat/mobile-context-trigger.tsx
// purpose: On mobile/tablet the AI Support context panel (spec section 10) does not fit beside the
//          chat, so per spec section 16 ("context panel moves below/behind a button") it collapses
//          behind this small trigger, opening the exact same <SupportContextPanel> content in a
//          bottom sheet instead of a second, divergent implementation.
// author: CloudDesk Team
// date: 2026-09-25

import { useState } from "react";
import { Info } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";

export function MobileContextTrigger({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <Button variant="outline" size="sm" className="w-full gap-1.5 lg:hidden" onClick={() => setIsOpen(true)}>
        <Info className="size-3.5" />
        View account context
      </Button>
      <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Account context</SheetTitle>
          <SheetDescription>What CloudDesk AI Support can see about your account.</SheetDescription>
        </SheetHeader>
        <div className="px-4 pb-4">{children}</div>
      </SheetContent>
    </Sheet>
  );
}
