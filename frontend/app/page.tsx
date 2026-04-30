'use client';

import { SignInButton, SignUpButton, useUser } from '@clerk/nextjs';
import { Bot, LogIn, UserPlus } from 'lucide-react';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  const { isSignedIn, isLoaded } = useUser();

  useEffect(() => {
    router.prefetch('/dashboard');
  }, [router]);

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace('/dashboard');
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || isSignedIn) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-gray-100 text-gray-600">
        Redirecting to chatbot...
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100">
      <div className="container mx-auto flex min-h-screen items-center justify-center px-4 py-8">
        <section className="w-full max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-xl">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-slate-800 text-white">
            <Bot className="h-8 w-8" />
          </div>

          <p className="mb-2 text-sm font-semibold uppercase tracking-[0.25em] text-slate-500">
            Meridian Electronics
          </p>
          <h1 className="mb-4 text-4xl font-bold text-gray-900">
            Customer Support ChatBot
          </h1>
          <p className="mx-auto mb-8 max-w-2xl text-gray-600">
            Sign in or create an account to access the AI assistant for product availability,
            order placement, and order history support.
          </p>

          <div className="flex flex-col justify-center gap-3 sm:flex-row">
            <SignInButton mode="modal" forceRedirectUrl="/dashboard">
              <button className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-800 px-6 py-3 font-semibold text-white transition hover:bg-slate-900">
                <LogIn className="h-5 w-5" />
                Login
              </button>
            </SignInButton>

            <SignUpButton mode="modal" forceRedirectUrl="/dashboard">
              <button className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-6 py-3 font-semibold text-slate-800 transition hover:bg-slate-50">
                <UserPlus className="h-5 w-5" />
                Sign Up
              </button>
            </SignUpButton>
          </div>
        </section>
      </div>
    </main>
  );
}