"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
  Search,
  X,
} from "lucide-react"

import { cn } from "@/lib/utils"

// Table variants using CVA
const tableVariants = cva(
  "w-full caption-bottom text-sm",
  {
    variants: {
      variant: {
        default: "",
        striped: "[&_tbody_tr:nth-child(odd)]:bg-muted/50",
        bordered: "[&_th]:border [&_td]:border",
      },
      size: {
        default: "",
        sm: "[&_th]:py-2 [&_th]:px-3 [&_td]:py-2 [&_td]:px-3 text-xs",
        lg: "[&_th]:py-4 [&_th]:px-6 [&_td]:py-4 [&_td]:px-6",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

// Column definition interface
export interface ColumnDef<T> {
  id: string
  header: string | React.ReactNode
  accessorKey?: keyof T
  accessorFn?: (row: T) => React.ReactNode
  cell?: (row: T) => React.ReactNode
  sortable?: boolean
  filterable?: boolean
  width?: string | number
  align?: "left" | "center" | "right"
  className?: string
}

// Sort state
export interface SortState {
  column: string | null
  direction: "asc" | "desc" | null
}

// Pagination state
export interface PaginationState {
  page: number
  pageSize: number
  totalItems: number
}

// DataTable props
export interface DataTableProps<T>
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof tableVariants> {
  columns: ColumnDef<T>[]
  data: T[]
  // Sorting
  sortable?: boolean
  defaultSort?: SortState
  onSortChange?: (sort: SortState) => void
  // Pagination
  pagination?: PaginationState
  onPaginationChange?: (pagination: PaginationState) => void
  pageSizeOptions?: number[]
  // Filtering
  filterable?: boolean
  filterPlaceholder?: string
  onFilterChange?: (filter: string) => void
  // Selection
  selectable?: boolean
  selectedRows?: T[]
  onSelectionChange?: (rows: T[]) => void
  rowKey?: keyof T | ((row: T) => string)
  // Loading
  loading?: boolean
  loadingRows?: number
  // Empty state
  emptyMessage?: React.ReactNode
  // Row click
  onRowClick?: (row: T) => void
  // Sticky header
  stickyHeader?: boolean
  maxHeight?: string | number
}

// Get row key helper
function getRowKey<T>(row: T, rowKey?: keyof T | ((row: T) => string), index?: number): string {
  if (typeof rowKey === "function") {
    return rowKey(row)
  }
  if (rowKey && row[rowKey] !== undefined) {
    return String(row[rowKey])
  }
  return String(index)
}

// DataTable component
function DataTableInner<T>(
  {
    columns,
    data,
    variant,
    size,
    sortable = false,
    defaultSort,
    onSortChange,
    pagination,
    onPaginationChange,
    pageSizeOptions = [10, 25, 50, 100],
    filterable = false,
    filterPlaceholder = "Search...",
    onFilterChange,
    selectable = false,
    selectedRows = [],
    onSelectionChange,
    rowKey,
    loading = false,
    loadingRows = 5,
    emptyMessage = "No data available",
    onRowClick,
    stickyHeader = false,
    maxHeight,
    className,
    ...props
  }: DataTableProps<T>,
  ref: React.ForwardedRef<HTMLDivElement>
) {
  const [sort, setSort] = React.useState<SortState>(
    defaultSort || { column: null, direction: null }
  )
  const [filter, setFilter] = React.useState("")
  const [selected, setSelected] = React.useState<Set<string>>(new Set())

  // Update selected when selectedRows changes
  React.useEffect(() => {
    const newSelected = new Set(
      selectedRows.map((row, i) => getRowKey(row, rowKey, i))
    )
    setSelected(newSelected)
  }, [selectedRows, rowKey])

  // Handle sort click
  const handleSort = (columnId: string) => {
    if (!sortable) return

    let newDirection: "asc" | "desc" | null = "asc"
    if (sort.column === columnId) {
      if (sort.direction === "asc") newDirection = "desc"
      else if (sort.direction === "desc") newDirection = null
    }

    const newSort = {
      column: newDirection ? columnId : null,
      direction: newDirection,
    }
    setSort(newSort)
    onSortChange?.(newSort)
  }

  // Handle filter change
  const handleFilterChange = (value: string) => {
    setFilter(value)
    onFilterChange?.(value)
  }

  // Handle row selection
  const handleRowSelect = (row: T, index: number) => {
    const key = getRowKey(row, rowKey, index)
    const newSelected = new Set(selected)

    if (newSelected.has(key)) {
      newSelected.delete(key)
    } else {
      newSelected.add(key)
    }

    setSelected(newSelected)
    const selectedData = data.filter((r, i) =>
      newSelected.has(getRowKey(r, rowKey, i))
    )
    onSelectionChange?.(selectedData)
  }

  // Handle select all
  const handleSelectAll = () => {
    if (selected.size === data.length) {
      setSelected(new Set())
      onSelectionChange?.([])
    } else {
      const allKeys = new Set(data.map((r, i) => getRowKey(r, rowKey, i)))
      setSelected(allKeys)
      onSelectionChange?.(data)
    }
  }

  // Handle page change
  const handlePageChange = (newPage: number) => {
    if (pagination && onPaginationChange) {
      onPaginationChange({ ...pagination, page: newPage })
    }
  }

  // Handle page size change
  const handlePageSizeChange = (newSize: number) => {
    if (pagination && onPaginationChange) {
      onPaginationChange({ ...pagination, pageSize: newSize, page: 1 })
    }
  }

  // Get cell value
  const getCellValue = (row: T, column: ColumnDef<T>): React.ReactNode => {
    if (column.cell) {
      return column.cell(row)
    }
    if (column.accessorFn) {
      return column.accessorFn(row)
    }
    if (column.accessorKey) {
      return row[column.accessorKey] as React.ReactNode
    }
    return null
  }

  // Sort icon
  const SortIcon = ({ columnId }: { columnId: string }) => {
    if (sort.column !== columnId) {
      return <ChevronsUpDown className="ml-1 h-4 w-4 text-muted-foreground/50" />
    }
    if (sort.direction === "asc") {
      return <ChevronUp className="ml-1 h-4 w-4" />
    }
    return <ChevronDown className="ml-1 h-4 w-4" />
  }

  // Calculate pagination
  const totalPages = pagination
    ? Math.ceil(pagination.totalItems / pagination.pageSize)
    : 0
  const startItem = pagination
    ? (pagination.page - 1) * pagination.pageSize + 1
    : 0
  const endItem = pagination
    ? Math.min(pagination.page * pagination.pageSize, pagination.totalItems)
    : 0

  return (
    <div ref={ref} className={cn("space-y-4", className)} {...props}>
      {/* Filter input */}
      {filterable && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder={filterPlaceholder}
            value={filter}
            onChange={(e) => handleFilterChange(e.target.value)}
            className="h-10 w-full rounded-md border border-input bg-background pl-10 pr-10 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {filter && (
            <button
              onClick={() => handleFilterChange("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label="Clear filter"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      )}

      {/* Table container */}
      <div
        className={cn(
          "relative overflow-auto rounded-md border",
          stickyHeader && "overflow-y-auto"
        )}
        style={{ maxHeight: maxHeight }}
      >
        <table className={cn(tableVariants({ variant, size }))}>
          <thead
            className={cn(
              "bg-muted/50 [&_tr]:border-b",
              stickyHeader && "sticky top-0 z-10 bg-muted"
            )}
          >
            <tr>
              {/* Selection checkbox header */}
              {selectable && (
                <th className="h-12 w-12 px-4">
                  <input
                    type="checkbox"
                    checked={selected.size === data.length && data.length > 0}
                    onChange={handleSelectAll}
                    className="h-4 w-4 rounded border-input"
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {columns.map((column) => (
                <th
                  key={column.id}
                  className={cn(
                    "h-12 px-4 text-left align-middle font-medium text-muted-foreground",
                    column.sortable !== false && sortable && "cursor-pointer select-none",
                    column.align === "center" && "text-center",
                    column.align === "right" && "text-right",
                    column.className
                  )}
                  style={{ width: column.width }}
                  onClick={() =>
                    column.sortable !== false && sortable && handleSort(column.id)
                  }
                  aria-sort={
                    sort.column === column.id
                      ? sort.direction === "asc"
                        ? "ascending"
                        : "descending"
                      : undefined
                  }
                >
                  <div
                    className={cn(
                      "flex items-center",
                      column.align === "center" && "justify-center",
                      column.align === "right" && "justify-end"
                    )}
                  >
                    {column.header}
                    {column.sortable !== false && sortable && (
                      <SortIcon columnId={column.id} />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="[&_tr:last-child]:border-0">
            {/* Loading state */}
            {loading && (
              <>
                {Array.from({ length: loadingRows }).map((_, i) => (
                  <tr key={`loading-${i}`} className="border-b">
                    {selectable && (
                      <td className="p-4">
                        <div className="h-4 w-4 animate-pulse rounded bg-muted" />
                      </td>
                    )}
                    {columns.map((column) => (
                      <td key={column.id} className="p-4">
                        <div className="h-4 animate-pulse rounded bg-muted" />
                      </td>
                    ))}
                  </tr>
                ))}
              </>
            )}

            {/* Empty state */}
            {!loading && data.length === 0 && (
              <tr>
                <td
                  colSpan={columns.length + (selectable ? 1 : 0)}
                  className="h-24 text-center text-muted-foreground"
                >
                  {emptyMessage}
                </td>
              </tr>
            )}

            {/* Data rows */}
            {!loading &&
              data.map((row, index) => {
                const key = getRowKey(row, rowKey, index)
                const isSelected = selected.has(key)

                return (
                  <tr
                    key={key}
                    className={cn(
                      "border-b transition-colors",
                      isSelected && "bg-primary/5",
                      onRowClick && "cursor-pointer hover:bg-muted/50"
                    )}
                    onClick={() => onRowClick?.(row)}
                    data-state={isSelected ? "selected" : undefined}
                  >
                    {selectable && (
                      <td className="p-4">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            e.stopPropagation()
                            handleRowSelect(row, index)
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="h-4 w-4 rounded border-input"
                          aria-label={`Select row ${index + 1}`}
                        />
                      </td>
                    )}
                    {columns.map((column) => (
                      <td
                        key={column.id}
                        className={cn(
                          "p-4 align-middle",
                          column.align === "center" && "text-center",
                          column.align === "right" && "text-right",
                          column.className
                        )}
                      >
                        {getCellValue(row, column)}
                      </td>
                    ))}
                  </tr>
                )
              })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && (
        <div className="flex items-center justify-between px-2">
          <div className="text-sm text-muted-foreground">
            {pagination.totalItems > 0 ? (
              <>
                Showing {startItem} to {endItem} of {pagination.totalItems} entries
              </>
            ) : (
              "No entries"
            )}
          </div>

          <div className="flex items-center gap-4">
            {/* Page size selector */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Rows per page:</span>
              <select
                value={pagination.pageSize}
                onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                className="h-8 rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Rows per page"
              >
                {pageSizeOptions.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>

            {/* Page navigation */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-input bg-background text-sm disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="px-2 text-sm">
                Page {pagination.page} of {totalPages || 1}
              </span>
              <button
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page >= totalPages}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-input bg-background text-sm disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground"
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Export with forwardRef
export const DataTable = React.forwardRef(DataTableInner) as <T>(
  props: DataTableProps<T> & { ref?: React.ForwardedRef<HTMLDivElement> }
) => ReturnType<typeof DataTableInner>

// Also export types
export type { ColumnDef as DataTableColumnDef }
