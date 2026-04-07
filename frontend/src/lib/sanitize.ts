/**
 * HTML sanitization utility using DOMPurify.
 *
 * SECURITY: All HTML from API responses MUST be sanitized before rendering
 * with dangerouslySetInnerHTML to prevent stored XSS attacks.
 */
import DOMPurify from 'dompurify';

/**
 * Sanitize HTML content for safe rendering via dangerouslySetInnerHTML.
 *
 * Allows standard formatting tags, links, images, and CMS content.
 * Strips scripts, event handlers, and other dangerous elements.
 */
export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    USE_PROFILES: { html: true },
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'ul', 'ol', 'li',
      'a', 'strong', 'em', 'b', 'i', 'u', 's', 'code', 'pre',
      'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'img', 'figure', 'figcaption',
      'div', 'span', 'section', 'article',
      'sup', 'sub', 'mark', 'small',
    ],
    ALLOWED_ATTR: [
      'href', 'target', 'rel', 'src', 'alt', 'title', 'width', 'height',
      'class', 'id', 'style', 'colspan', 'rowspan', 'align',
    ],
    ALLOW_DATA_ATTR: false,
  });
}

/**
 * Sanitize and return as props for dangerouslySetInnerHTML.
 * Usage: <div {...sanitizedInnerHtml(content)} />
 */
export function sanitizedInnerHtml(dirty: string | undefined | null) {
  return {
    dangerouslySetInnerHTML: { __html: sanitizeHtml(dirty || '') },
  };
}
