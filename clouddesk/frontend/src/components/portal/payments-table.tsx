// name: components/portal/payments-table.tsx
// purpose: Payment history table for /billing, plus a callout when duplicate/failed charges are
//          detected — pointing the customer at the AI Support chat rather than a self-service
//          refund button, matching the product's real design (refunds flow through the Billing
//          Agent + approval flow, spec sections 9-22).
// author: CloudDesk Team
// date: 2026-09-24

import Link from "next/link";
import { CreditCard, MessageCircleQuestion } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Payment } from "@/lib/api/types";
import { formatCurrency, formatDate, formatEnumLabel } from "@/lib/format";

function findDuplicateCount(payments: Payment[]): number {
  const succeeded = payments.filter((p) => p.status === "succeeded");
  const bySubscription = new Map<string, number>();
  for (const payment of succeeded) {
    bySubscription.set(payment.subscription_id, (bySubscription.get(payment.subscription_id) ?? 0) + 1);
  }
  return succeeded.length - bySubscription.size;
}

export function PaymentsTable({ payments }: { payments: Payment[] }) {
  const duplicateCount = findDuplicateCount(payments);

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-base">Payment history</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {duplicateCount > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3">
            <div className="flex items-start gap-2.5">
              <MessageCircleQuestion className="mt-0.5 size-4.5 shrink-0 text-warning-foreground" />
              <p className="text-sm text-warning-foreground">
                We noticed what may be a duplicate charge on this account. Our AI Support team can
                investigate and, if confirmed, route a refund for review.
              </p>
            </div>
            <Button size="sm" variant="outline" render={<Link href="/support">Ask AI Support</Link>} />
          </div>
        ) : null}

        {payments.length === 0 ? (
          <EmptyState icon={CreditCard} title="No payments yet" description="Payments will appear here once billed." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Method</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Reference</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payments.map((payment) => (
                <TableRow key={payment.id}>
                  <TableCell>{formatDate(payment.created_at)}</TableCell>
                  <TableCell className="font-medium">
                    {formatCurrency(payment.amount, payment.currency)}
                  </TableCell>
                  <TableCell>{formatEnumLabel(payment.payment_method)}</TableCell>
                  <TableCell>
                    <StatusBadge status={payment.status} />
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {payment.transaction_reference}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
