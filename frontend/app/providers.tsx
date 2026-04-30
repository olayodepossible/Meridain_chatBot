'use client';

import { ClerkProvider } from '@clerk/clerk-react';

export function Providers({ children }: { children: React.ReactNode }) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!publishableKey) {
    throw new Error('Missing NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY');
  }
  return <ClerkProvider publishableKey={publishableKey}>{children}</ClerkProvider>;
}
