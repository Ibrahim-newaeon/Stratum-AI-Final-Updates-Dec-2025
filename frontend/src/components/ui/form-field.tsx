/**
 * Form Field Components
 * Accessible form inputs with labels, help text, and validation feedback
 */

import { forwardRef, ReactNode, InputHTMLAttributes, useId } from 'react';
import { cn } from '@/lib/utils';

interface FormLabelProps {
  children: ReactNode;
  htmlFor?: string;
  required?: boolean;
  className?: string;
}

/**
 * Form Label with optional required indicator
 */
export function FormLabel({ children, htmlFor, required, className }: FormLabelProps) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn('text-sm font-medium text-foreground block mb-2', className)}
    >
      {children}
      {required && (
        <span className="text-red-500 ms-0.5" aria-hidden="true">*</span>
      )}
      {required && <span className="sr-only">(required)</span>}
    </label>
  );
}

interface FormErrorProps {
  id?: string;
  children: ReactNode;
  className?: string;
}

/**
 * Form Error Message
 */
export function FormError({ id, children, className }: FormErrorProps) {
  if (!children) return null;

  return (
    <p
      id={id}
      role="alert"
      className={cn('mt-1.5 text-sm text-red-500 flex items-center gap-1', className)}
    >
      <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
      <span>{children}</span>
    </p>
  );
}

interface FormSuccessProps {
  children: ReactNode;
  className?: string;
}

/**
 * Form Success Message
 */
export function FormSuccess({ children, className }: FormSuccessProps) {
  if (!children) return null;

  return (
    <p className={cn('mt-1.5 text-sm text-green-500 flex items-center gap-1', className)}>
      <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
      </svg>
      <span>{children}</span>
    </p>
  );
}

interface FormHelpTextProps {
  id?: string;
  children: ReactNode;
  className?: string;
}

/**
 * Form Help Text
 */
export function FormHelpText({ id, children, className }: FormHelpTextProps) {
  return (
    <p id={id} className={cn('mt-1 text-xs text-muted-foreground', className)}>
      {children}
    </p>
  );
}

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helpText?: string;
  success?: string;
  icon?: ReactNode;
  endIcon?: ReactNode;
  containerClassName?: string;
}

/**
 * Complete Form Field with label, input, icons, and validation states
 */
export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  (
    {
      label,
      error,
      helpText,
      success,
      icon,
      endIcon,
      required,
      className,
      containerClassName,
      id,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const fieldId = id || generatedId;
    const errorId = `${fieldId}-error`;
    const helpId = `${fieldId}-help`;

    const hasError = !!error;
    const hasSuccess = !!success && !hasError;

    return (
      <div className={containerClassName}>
        {label && (
          <FormLabel htmlFor={fieldId} required={required}>
            {label}
          </FormLabel>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute start-4 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            id={fieldId}
            required={required}
            aria-invalid={hasError}
            aria-describedby={
              [error && errorId, helpText && helpId].filter(Boolean).join(' ') || undefined
            }
            className={cn(
              'w-full py-3 rounded-xl text-foreground placeholder-muted-foreground',
              'outline-none transition-all duration-200',
              'bg-background border',
              icon ? 'ps-12' : 'ps-4',
              endIcon ? 'pe-12' : 'pe-4',
              hasError
                ? 'border-red-500 focus:border-red-500 focus:ring-2 focus:ring-red-500/20'
                : hasSuccess
                ? 'border-green-500 focus:border-green-500 focus:ring-2 focus:ring-green-500/20'
                : 'border-border focus:border-primary focus:ring-2 focus:ring-primary/20',
              className
            )}
            {...props}
          />
          {endIcon && (
            <div className="absolute end-4 top-1/2 -translate-y-1/2">
              {endIcon}
            </div>
          )}
          {/* Inline validation indicator */}
          {hasSuccess && !endIcon && (
            <div className="absolute end-4 top-1/2 -translate-y-1/2 text-green-500">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
          )}
        </div>
        {error && <FormError id={errorId}>{error}</FormError>}
        {success && !error && <FormSuccess>{success}</FormSuccess>}
        {helpText && !error && <FormHelpText id={helpId}>{helpText}</FormHelpText>}
      </div>
    );
  }
);

FormField.displayName = 'FormField';

export default FormField;
