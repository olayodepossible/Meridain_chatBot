'use client';

import { AuthenticateWithRedirectCallback, ClerkProvider } from '@clerk/clerk-react';
import { Suspense } from 'react';

import { ClerkHandshakeCleanup } from '@/components/ClerkHandshakeCleanup';

function afterAuthUrl(fallback: string) {
  const v = process.env.NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL?.trim();
  return v && v.length > 0 ? v : fallback;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!publishableKey) {
    throw new Error('Missing NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY');
  }

  const signInDest = afterAuthUrl('/dashboard');
  const signUpDest =
    process.env.NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL?.trim() || signInDest;

  return (
    <ClerkProvider
      publishableKey={publishableKey}
      afterSignInUrl={signInDest}
      afterSignUpUrl={signUpDest}
    >
      <AuthenticateWithRedirectCallback />
      <Suspense fallback={null}>
        <ClerkHandshakeCleanup />
      </Suspense>
      {children}
    </ClerkProvider>
  );
}
