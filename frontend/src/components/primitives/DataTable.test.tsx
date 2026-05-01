import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { DataTable, type DataTableColumn } from './DataTable';

interface Row {
  id: number;
  name: string;
  amount: number;
}

const rows: Row[] = [
  { id: 1, name: 'Bravo', amount: 30 },
  { id: 2, name: 'Alpha', amount: 10 },
  { id: 3, name: 'Charlie', amount: 20 },
];

const columns: DataTableColumn<Row>[] = [
  {
    id: 'name',
    header: 'Name',
    cell: (r) => r.name,
    sortable: true,
    sortAccessor: (r) => r.name,
  },
  {
    id: 'amount',
    header: 'Amount',
    cell: (r) => r.amount,
    sortable: true,
    sortAccessor: (r) => r.amount,
  },
];

describe('DataTable', () => {
  it('renders all rows', () => {
    render(<DataTable data={rows} columns={columns} />);
    expect(screen.getByText('Bravo')).toBeInTheDocument();
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Charlie')).toBeInTheDocument();
  });

  it('renders the empty message when data is []', () => {
    render(<DataTable data={[]} columns={columns} emptyMessage="Nothing here" />);
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('renders skeleton rows when loading', () => {
    const { container } = render(<DataTable data={[]} columns={columns} loading loadingRows={3} />);
    const skels = container.querySelectorAll('.animate-pulse');
    // 3 rows × 2 columns = 6 skeleton bars.
    expect(skels.length).toBe(6);
  });

  it('renders the error shell', () => {
    render(<DataTable data={rows} columns={columns} error="Something broke" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Something broke');
  });

  it('sorts rows ascending on first header click', () => {
    render(<DataTable data={rows} columns={columns} />);
    fireEvent.click(screen.getByRole('button', { name: /Name/ }));
    const tableRows = screen.getAllByRole('row');
    // First row is the header. Then sorted body.
    expect(within(tableRows[1]).getByText('Alpha')).toBeInTheDocument();
    expect(within(tableRows[2]).getByText('Bravo')).toBeInTheDocument();
    expect(within(tableRows[3]).getByText('Charlie')).toBeInTheDocument();
  });

  it('sorts descending on second header click', () => {
    render(<DataTable data={rows} columns={columns} />);
    const btn = screen.getByRole('button', { name: /Name/ });
    fireEvent.click(btn);
    fireEvent.click(btn);
    const tableRows = screen.getAllByRole('row');
    expect(within(tableRows[1]).getByText('Charlie')).toBeInTheDocument();
    expect(within(tableRows[2]).getByText('Bravo')).toBeInTheDocument();
    expect(within(tableRows[3]).getByText('Alpha')).toBeInTheDocument();
  });

  it('sorts numerically by amount when configured', () => {
    render(<DataTable data={rows} columns={columns} />);
    fireEvent.click(screen.getByRole('button', { name: /Amount/ }));
    const cells = screen.getAllByRole('cell');
    // Order: 10, 20, 30 across rows
    expect(cells.map((c) => c.textContent).filter((t) => /^\d+$/.test(t ?? ''))).toEqual([
      '10',
      '20',
      '30',
    ]);
  });

  it('exposes aria-sort on the active sort column', () => {
    render(<DataTable data={rows} columns={columns} />);
    fireEvent.click(screen.getByRole('button', { name: /Name/ }));
    const headers = screen.getAllByRole('columnheader');
    expect(headers[0].getAttribute('aria-sort')).toBe('ascending');
    expect(headers[1].getAttribute('aria-sort')).toBe('none');
  });

  it('triggers onRowClick when a row is clicked', () => {
    const handler = vi.fn();
    render(<DataTable data={rows} columns={columns} onRowClick={handler} />);
    fireEvent.click(screen.getByText('Bravo').closest('tr')!);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler.mock.calls[0][0]).toEqual(rows[0]);
  });

  it('row keyboard activation (Enter / Space)', () => {
    const handler = vi.fn();
    render(<DataTable data={rows} columns={columns} onRowClick={handler} />);
    const row = screen.getByText('Bravo').closest('tr')!;
    fireEvent.keyDown(row, { key: 'Enter' });
    expect(handler).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(row, { key: ' ' });
    expect(handler).toHaveBeenCalledTimes(2);
  });

  it('uses rowKey for stable React keys', () => {
    render(<DataTable data={rows} columns={columns} rowKey={(r) => r.id} />);
    expect(screen.getAllByRole('row').length).toBe(1 + rows.length);
  });
});
