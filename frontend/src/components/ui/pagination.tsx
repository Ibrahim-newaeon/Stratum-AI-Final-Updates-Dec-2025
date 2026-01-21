"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  MoreHorizontal,
} from "lucide-react"

import { cn } from "@/lib/utils"

// Pagination variants
const paginationVariants = cva(
  "flex items-center gap-1",
  {
    variants: {
      size: {
        default: "",
        sm: "[&_button]:h-7 [&_button]:w-7 [&_button]:text-xs",
        lg: "[&_button]:h-10 [&_button]:w-10 [&_button]:text-base",
      },
    },
    defaultVariants: {
      size: "default",
    },
  }
)

// Button variants
const paginationButtonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        outline:
          "border border-input bg-transparent hover:bg-accent hover:text-accent-foreground",
      },
      isActive: {
        true: "bg-primary text-primary-foreground hover:bg-primary/90",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      isActive: false,
    },
  }
)

export interface PaginationProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof paginationVariants> {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
  showFirstLast?: boolean
  showPrevNext?: boolean
  siblingCount?: number
  boundaryCount?: number
  variant?: "default" | "ghost" | "outline"
}

// Generate page numbers to display
function generatePagination(
  currentPage: number,
  totalPages: number,
  siblingCount: number = 1,
  boundaryCount: number = 1
): (number | "ellipsis")[] {
  // Total page numbers to show (excluding ellipsis)
  const totalPageNumbers = siblingCount * 2 + boundaryCount * 2 + 3

  // If total pages is less than page numbers to show, show all pages
  if (totalPages <= totalPageNumbers) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }

  // Calculate left and right sibling pages
  const leftSiblingIndex = Math.max(currentPage - siblingCount, boundaryCount + 1)
  const rightSiblingIndex = Math.min(
    currentPage + siblingCount,
    totalPages - boundaryCount
  )

  // Determine if we need ellipsis
  const showLeftEllipsis = leftSiblingIndex > boundaryCount + 2
  const showRightEllipsis = rightSiblingIndex < totalPages - boundaryCount - 1

  // Generate the pages array
  const pages: (number | "ellipsis")[] = []

  // Add boundary pages at the start
  for (let i = 1; i <= boundaryCount; i++) {
    pages.push(i)
  }

  // Add left ellipsis
  if (showLeftEllipsis) {
    pages.push("ellipsis")
  } else if (boundaryCount + 1 < leftSiblingIndex) {
    // Add the page that would be hidden by ellipsis
    pages.push(boundaryCount + 1)
  }

  // Add sibling pages and current page
  for (let i = leftSiblingIndex; i <= rightSiblingIndex; i++) {
    if (i > boundaryCount && i <= totalPages - boundaryCount) {
      pages.push(i)
    }
  }

  // Add right ellipsis
  if (showRightEllipsis) {
    pages.push("ellipsis")
  } else if (rightSiblingIndex < totalPages - boundaryCount) {
    // Add the page that would be hidden by ellipsis
    pages.push(totalPages - boundaryCount)
  }

  // Add boundary pages at the end
  for (let i = totalPages - boundaryCount + 1; i <= totalPages; i++) {
    if (!pages.includes(i)) {
      pages.push(i)
    }
  }

  return pages
}

const Pagination = React.forwardRef<HTMLDivElement, PaginationProps>(
  (
    {
      currentPage,
      totalPages,
      onPageChange,
      showFirstLast = true,
      showPrevNext = true,
      siblingCount = 1,
      boundaryCount = 1,
      variant = "default",
      size,
      className,
      ...props
    },
    ref
  ) => {
    const pages = generatePagination(
      currentPage,
      totalPages,
      siblingCount,
      boundaryCount
    )

    const canGoBack = currentPage > 1
    const canGoForward = currentPage < totalPages

    return (
      <nav
        ref={ref}
        role="navigation"
        aria-label="Pagination"
        className={cn(paginationVariants({ size }), className)}
        {...props}
      >
        {/* First page button */}
        {showFirstLast && (
          <button
            onClick={() => onPageChange(1)}
            disabled={!canGoBack}
            className={cn(
              paginationButtonVariants({ variant }),
              "h-8 w-8"
            )}
            aria-label="Go to first page"
          >
            <ChevronsLeft className="h-4 w-4" />
          </button>
        )}

        {/* Previous page button */}
        {showPrevNext && (
          <button
            onClick={() => onPageChange(currentPage - 1)}
            disabled={!canGoBack}
            className={cn(
              paginationButtonVariants({ variant }),
              "h-8 w-8"
            )}
            aria-label="Go to previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}

        {/* Page numbers */}
        {pages.map((page, index) =>
          page === "ellipsis" ? (
            <span
              key={`ellipsis-${index}`}
              className="flex h-8 w-8 items-center justify-center"
              aria-hidden
            >
              <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
            </span>
          ) : (
            <button
              key={page}
              onClick={() => onPageChange(page)}
              className={cn(
                paginationButtonVariants({
                  variant,
                  isActive: currentPage === page,
                }),
                "h-8 w-8"
              )}
              aria-label={`Go to page ${page}`}
              aria-current={currentPage === page ? "page" : undefined}
            >
              {page}
            </button>
          )
        )}

        {/* Next page button */}
        {showPrevNext && (
          <button
            onClick={() => onPageChange(currentPage + 1)}
            disabled={!canGoForward}
            className={cn(
              paginationButtonVariants({ variant }),
              "h-8 w-8"
            )}
            aria-label="Go to next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        )}

        {/* Last page button */}
        {showFirstLast && (
          <button
            onClick={() => onPageChange(totalPages)}
            disabled={!canGoForward}
            className={cn(
              paginationButtonVariants({ variant }),
              "h-8 w-8"
            )}
            aria-label="Go to last page"
          >
            <ChevronsRight className="h-4 w-4" />
          </button>
        )}
      </nav>
    )
  }
)
Pagination.displayName = "Pagination"

// Additional sub-components for more granular control
const PaginationContent = React.forwardRef<
  HTMLUListElement,
  React.HTMLAttributes<HTMLUListElement>
>(({ className, ...props }, ref) => (
  <ul
    ref={ref}
    className={cn("flex flex-row items-center gap-1", className)}
    {...props}
  />
))
PaginationContent.displayName = "PaginationContent"

const PaginationItem = React.forwardRef<
  HTMLLIElement,
  React.LiHTMLAttributes<HTMLLIElement>
>(({ className, ...props }, ref) => (
  <li ref={ref} className={cn("", className)} {...props} />
))
PaginationItem.displayName = "PaginationItem"

const PaginationLink = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    isActive?: boolean
  }
>(({ className, isActive, ...props }, ref) => (
  <button
    ref={ref}
    aria-current={isActive ? "page" : undefined}
    className={cn(
      paginationButtonVariants({
        variant: "default",
        isActive,
      }),
      "h-8 w-8",
      className
    )}
    {...props}
  />
))
PaginationLink.displayName = "PaginationLink"

const PaginationPrevious = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, ...props }, ref) => (
  <button
    ref={ref}
    aria-label="Go to previous page"
    className={cn(
      paginationButtonVariants({ variant: "default" }),
      "h-8 gap-1 px-2.5",
      className
    )}
    {...props}
  >
    <ChevronLeft className="h-4 w-4" />
    <span>Previous</span>
  </button>
))
PaginationPrevious.displayName = "PaginationPrevious"

const PaginationNext = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, ...props }, ref) => (
  <button
    ref={ref}
    aria-label="Go to next page"
    className={cn(
      paginationButtonVariants({ variant: "default" }),
      "h-8 gap-1 px-2.5",
      className
    )}
    {...props}
  >
    <span>Next</span>
    <ChevronRight className="h-4 w-4" />
  </button>
))
PaginationNext.displayName = "PaginationNext"

const PaginationEllipsis = React.forwardRef<
  HTMLSpanElement,
  React.HTMLAttributes<HTMLSpanElement>
>(({ className, ...props }, ref) => (
  <span
    ref={ref}
    aria-hidden
    className={cn("flex h-8 w-8 items-center justify-center", className)}
    {...props}
  >
    <MoreHorizontal className="h-4 w-4" />
    <span className="sr-only">More pages</span>
  </span>
))
PaginationEllipsis.displayName = "PaginationEllipsis"

export {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationPrevious,
  PaginationNext,
  PaginationEllipsis,
}
