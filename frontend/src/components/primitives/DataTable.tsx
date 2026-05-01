/**
 * DataTable — lightweight headless table.
 *
 * No third-party table lib. Plain HTML + Tailwind so it stays
 * compositional, themable, and readable. Loading / empty / error
 * are first-class props — caller never branches on data state.
 *
 * Features:
 * - Typed column definitions with custom cell renderers.
 * - Optional sortable columns (click header → toggle asc/desc).
 * - Sticky header.
 * - Hairline rows, hover highlight on rows (theme-aware).
 * - Optional row click handler with keyboard support (Enter/Space).
 * - Pagination is intentionally NOT bundled — pass a slice in `data`
 *   from the parent. (Keeps the primitive small; pagination is a
 *   layout concern.)
 */

import { type KeyboardEvent, type ReactNode, useMemo, useState, useCallback } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface DataTableColumn<T> {
  /** Stable unique id — used for sort state. Falls back to header text. */
  id?: string;
  header: ReactNode;
  /** Render the cell. Receives the row + index. */
  cell: (row: T, rowIndex: number) => ReactNode;
  /** Enable click-to-sort on this column header. */
  sortable?: boolean;
  /** Comparator for sortable columns. Default: localeCompare on String(cell). */
  sortAccessor?: (row: T) => string | number;
  /** Tailwind class for the column (width, alignment). */
  className?: string;
  /** Tailwind class for the header cell. */
  headerClassName?: string;
  /** Tailwind class for the body cell. */
  cellClassName?: string;
  /** Hide the column on small screens. */
  hideOnMobile?: boolean;
}

interface DataTableProps<T> {
  data: T[];
  columns: DataTableColumn<T>[];
  /** Stable key for each row (defaults to row index — only safe for stable lists). */
  rowKey?: (row: T, idx: number) => string | number;
  /** Click handler on a row. */
  onRowClick?: (row: T, idx: number) => void;
  loading?: boolean;
  /** Number of skeleton rows shown when loading. Default 5. */
  loadingRows?: number;
  /** Empty message — shown when data is [] and not loading/error. */
  emptyMessage?: string;
  error?: string;
  className?: string;
  /** Caption for screen readers. */
  ariaLabel?: string;
}

type SortDirection = 'asc' | 'desc';

interface SortState {
  columnId: string;
  direction: SortDirection;
}

function getColumnId<T>(col: DataTableColumn<T>, idx: number): string {
  return col.id ?? `col-${idx}`;
}

export function DataTable<T>({
  data,
  columns,
  rowKey,
  onRowClick,
  loading = false,
  loadingRows = 5,
  emptyMessage = 'No data yet.',
  error,
  className,
  ariaLabel,
}: DataTableProps<T>) {
  const [sort, setSort] = useState<SortState | null>(null);

  const sortedData = useMemo(() => {
    if (!sort) return data;
    const col = columns.find((c, idx) => getColumnId(c, idx) === sort.columnId);
    if (!col || !col.sortable) return data;
    const accessor =
      col.sortAccessor ?? ((row: T, idx: number = 0) => String(col.cell(row, idx) ?? ''));
    const factor = sort.direction === 'asc' ? 1 : -1;
    const copy = [...data];
    copy.sort((a, b) => {
      const av = accessor(a as T);
      const bv = accessor(b as T);
      if (typeof av === 'number' && typeof bv === 'number') {
        return (av - bv) * factor;
      }
      return String(av).localeCompare(String(bv)) * factor;
    });
    return copy;
  }, [data, columns, sort]);

  const toggleSort = useCallback((columnId: string) => {
    setSort((prev) => {
      if (!prev || prev.columnId !== columnId) return { columnId, direction: 'asc' };
      if (prev.direction === 'asc') return { columnId, direction: 'desc' };
      return null;
    });
  }, []);

  const handleRowKey = useCallback(
    (e: KeyboardEvent<HTMLTableRowElement>, row: T, idx: number) => {
      if (!onRowClick) return;
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onRowClick(row, idx);
      }
    },
    [onRowClick]
  );

  if (error) {
    return (
      <div
        role="alert"
        className={cn(
          'rounded-2xl border border-danger/30 bg-danger/5',
          'p-6 text-meta text-danger',
          className
        )}
      >
        {error}
      </div>
    );
  }

  return (
    <div className={cn('rounded-2xl border border-border bg-card overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse text-sm"
          aria-label={ariaLabel}
          aria-busy={loading || undefined}
        >
          <thead className="bg-muted/40">
            <tr>
              {columns.map((col, idx) => {
                const id = getColumnId(col, idx);
                const isSorted = sort?.columnId === id;
                return (
                  <th
                    key={id}
                    scope="col"
                    aria-sort={
                      isSorted ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'
                    }
                    className={cn(
                      'px-4 py-3 text-left',
                      'text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono font-medium',
                      'border-b border-border',
                      col.hideOnMobile && 'hidden md:table-cell',
                      col.className,
                      col.headerClassName
                    )}
                  >
                    {col.sortable ? (
                      <button
                        type="button"
                        onClick={() => toggleSort(id)}
                        className={cn(
                          'inline-flex items-center gap-1 text-left',
                          'hover:text-foreground transition-colors',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded'
                        )}
                      >
                        {col.header}
                        {isSorted ? (
                          sort.direction === 'asc' ? (
                            <ChevronUp className="w-3 h-3" aria-hidden="true" />
                          ) : (
                            <ChevronDown className="w-3 h-3" aria-hidden="true" />
                          )
                        ) : (
                          <span className="w-3 h-3 inline-block" aria-hidden="true" />
                        )}
                      </button>
                    ) : (
                      col.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: loadingRows }).map((_, idx) => (
                <tr key={`skel-${idx}`} className="border-b border-border last:border-b-0">
                  {columns.map((col, cIdx) => (
                    <td
                      key={cIdx}
                      className={cn(
                        'px-4 py-4',
                        col.hideOnMobile && 'hidden md:table-cell',
                        col.className,
                        col.cellClassName
                      )}
                    >
                      <div className="h-3 w-3/4 bg-muted rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : sortedData.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-10 text-center text-meta uppercase tracking-[0.06em] text-muted-foreground"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              sortedData.map((row, idx) => {
                const key = rowKey ? rowKey(row, idx) : idx;
                const clickable = !!onRowClick;
                return (
                  <tr
                    key={key}
                    role={clickable ? 'button' : undefined}
                    tabIndex={clickable ? 0 : undefined}
                    onClick={clickable ? () => onRowClick(row, idx) : undefined}
                    onKeyDown={clickable ? (e) => handleRowKey(e, row, idx) : undefined}
                    className={cn(
                      'border-b border-border last:border-b-0',
                      'transition-colors duration-150',
                      clickable &&
                        'cursor-pointer hover:bg-muted/60 focus:outline-none focus:bg-muted/60'
                    )}
                  >
                    {columns.map((col, cIdx) => (
                      <td
                        key={cIdx}
                        className={cn(
                          'px-4 py-3 text-foreground',
                          col.hideOnMobile && 'hidden md:table-cell',
                          col.className,
                          col.cellClassName
                        )}
                      >
                        {col.cell(row, idx)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default DataTable;
