'use client';

import { useAuth } from '@clerk/clerk-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef } from 'react';

/**
 * Static export on CloudFront can leave `?__clerk_handshake=...` on the URL after Clerk
 * finishes the session. Once signed in, replace with a clean path so the app state matches production.
 */
export function ClerkHandshakeCleanup() {
  const { isSignedIn, isLoaded } = useAuth();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const done = useRef(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || done.current) return;
    if (!searchParams?.has('__clerk_handshake')) return;
    done.current = true;
    const path = pathname && pathname !== '/' ? pathname : '/dashboard';
    router.replace(path);
  }, [isLoaded, isSignedIn, pathname, router, searchParams]);

  return null;
}
