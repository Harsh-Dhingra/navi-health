import Link from "next/link";
import ChatInterface from "@/components/ChatInterface";

export default function HomePage() {
  return (
    <main className="mx-auto flex h-screen max-w-3xl flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
        <div>
          <h1 className="text-xl font-semibold text-navi-900">NAVI</h1>
          <p className="text-sm text-slate-500">Your AI guide through the U.S. healthcare system.</p>
        </div>
        <Link href="/dashboard" className="text-sm font-medium text-navi-600 hover:underline">
          Care journeys →
        </Link>
      </header>
      <ChatInterface />
      <footer className="border-t border-slate-100 bg-white px-6 py-2 text-center text-xs text-slate-400">
        NAVI is a navigation tool, not a medical provider, and does not give medical advice. Beta — some data
        may be simulated.
      </footer>
    </main>
  );
}
