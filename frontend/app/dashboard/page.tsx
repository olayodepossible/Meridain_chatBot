'use client';

import { UserButton, useSession, useUser } from '@clerk/clerk-react';
import ChatBot from '@/components/chatBot';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function Dashboard() {
  const { isSignedIn, isLoaded: userLoaded } = useUser();
  const { isLoaded: sessionLoaded } = useSession();
  const router = useRouter();
  const clerkReady = userLoaded && sessionLoaded;

  useEffect(() => {
    if (!clerkReady || isSignedIn) return;
    router.replace('/');
  }, [clerkReady, isSignedIn, router]);

  if (!clerkReady || !isSignedIn) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-gray-100 text-gray-600">
        Loading…
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="mx-auto max-w-4xl">
          <header className="mb-8 flex items-start justify-between gap-4">
            <div className="text-center sm:text-left">
              <h1 className="text-4xl font-bold text-gray-800">
                Meridian Electronics Company
              </h1>
              <p className="mt-2 text-gray-600">
                Meridian Electronics ChatBot
              </p>
            </div>
            <UserButton />
          </header>

          <div className="h-[600px]">
            <ChatBot />
          </div>

          <footer className="mt-8 text-center text-sm text-gray-500">
            <p>&copy; {new Date().getFullYear()} Meridian Electronics. All rights reserved.</p>
          </footer>
        </div>
      </div>
    </main>
  );
}
