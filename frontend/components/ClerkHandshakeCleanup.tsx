'use client';

import { useAuth } from '@clerk/clerk-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef } from 'react';

export function ClerkHandshakeCleanup() {
  const { isSignedIn, isLoaded } = useAuth();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const done = useRef(false);

  useEffect(() => {
    if (!isLoaded || done.current) return;

    const hasHandshake =
      searchParams?.has('__clerk_handshake') ||
      searchParams?.has('__clerk_db_jwt');

    if (!hasHandshake) return;

    // Only clean AFTER Clerk is sure about auth state
    if (!isSignedIn) return;

    done.current = true;

    const cleanPath = pathname || '/dashboard';

    router.replace(cleanPath);
  }, [isLoaded, isSignedIn, pathname, router, searchParams]);

  return null;
}