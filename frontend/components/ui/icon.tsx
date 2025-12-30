import React from 'react'
import { cn } from '@/lib/utils'

interface IconProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl'
  variant?: 'default' | 'muted' | 'primary' | 'secondary' | 'success' | 'warning' | 'error'
  className?: string
  children: React.ReactElement<{ className?: string }>
}

const iconSizes = {
  xs: 'h-3 w-3',
  sm: 'h-4 w-4', 
  md: 'h-5 w-5',
  lg: 'h-6 w-6',
  xl: 'h-8 w-8',
  '2xl': 'h-10 w-10'
}

const iconVariants = {
  default: 'text-foreground',
  muted: 'text-muted-foreground',
  primary: 'text-primary',
  secondary: 'text-secondary-foreground',
  success: 'text-green-500',
  warning: 'text-yellow-500',
  error: 'text-red-500'
}

export function Icon({ 
  size = 'sm', 
  variant = 'default', 
  className, 
  children,
}: IconProps) {
  return React.cloneElement(children, {
    ...children.props,
    className: cn(
      iconSizes[size],
      iconVariants[variant],
      'inline-flex shrink-0',
      className,
      children.props?.className
    )
  })
}

export default Icon