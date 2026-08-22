import React from 'react';
import { useLocation, useNavigate, type NavigateFunction } from 'react-router-dom';

export function useSafeLocation() {
  try {
    return useLocation();
  } catch {
    return { pathname: typeof window !== 'undefined' ? window.location.pathname : '/' };
  }
}

export function useSafeNavigate(): NavigateFunction {
  try {
    return useNavigate();
  } catch {
    return ((to: any) => {
      if (typeof to === 'string') {
        if (typeof window !== 'undefined') {
          window.history.pushState({}, '', to);
        }
      }
    }) as NavigateFunction;
  }
}

interface SafeLinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  to: string;
  children: React.ReactNode;
  className?: string;
}

export const SafeLink: React.FC<SafeLinkProps> = ({ to, children, className, onClick, ...rest }) => {
  const navigate = useSafeNavigate();

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (onClick) onClick(e);
    if (!e.defaultPrevented && e.button === 0 && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      e.preventDefault();
      navigate(to);
    }
  };

  return (
    <a href={to} onClick={handleClick} className={className} {...rest}>
      {children}
    </a>
  );
};
