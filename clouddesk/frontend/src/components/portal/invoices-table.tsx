// name: components/portal/invoices-table.tsx
// purpose: Invoice history table for /billing.
// author: CloudDesk Team
// date: 2026-09-24

import { FileText } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Invoice } from "@/lib/api/types";
import { formatCurrency, formatDate } from "@/lib/format";

export function InvoicesTable({ invoices }: { invoices: Invoice[] }) {
  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-base">Invoices</CardTitle>
      </CardHeader>
      <CardContent>
        {invoices.length === 0 ? (
          <EmptyState icon={FileText} title="No invoices yet" description="Invoices will appear here once issued." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Issued</TableHead>
                <TableHead>Due</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.map((invoice) => (
                <TableRow key={invoice.id}>
                  <TableCell>{formatDate(invoice.issued_at)}</TableCell>
                  <TableCell>{formatDate(invoice.due_at)}</TableCell>
                  <TableCell className="font-medium">{formatCurrency(invoice.amount)}</TableCell>
                  <TableCell>
                    <StatusBadge status={invoice.status} />
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
