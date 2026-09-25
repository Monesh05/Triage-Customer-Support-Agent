// name: components/portal/payments-table.tsx
// purpose: Payment history table for /billing. The duplicate-charge callout that used to live
//          inline here now renders as its own component (billing-incident-alert.tsx, spec section
//          6) above this table, so this component is table-only.
// author: CloudDesk Team
// date: 2026-09-25

import { CreditCard } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Payment } from "@/lib/api/types";
import { formatCurrency, formatDate, formatEnumLabel } from "@/lib/format";

export function PaymentsTable({ payments }: { payments: Payment[] }) {
  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-base">Payment history</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
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
