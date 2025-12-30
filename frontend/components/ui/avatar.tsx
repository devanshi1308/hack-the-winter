import React from 'react';

interface AvatarProps {
  children?: React.ReactNode;
  className?: string;
}

const Avatar = ({ children, className }: AvatarProps) => {
  return (
    <div className={`relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full ${className || ''}`}>
      {children}
    </div>
  );
};

interface AvatarFallbackProps {
    children?: React.ReactNode;
    className?: string;
}

const AvatarFallback = ({ children, className }: AvatarFallbackProps) => {
  return (
    <div className={`flex h-full w-full items-center justify-center rounded-full bg-muted ${className || ''}`}>
      {children}
    </div>
  );
};

export { Avatar, AvatarFallback };