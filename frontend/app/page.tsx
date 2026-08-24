import ChatInterface from "@/components/ChatInterface";

export default function HomePage() {
  return (
    <main className="mx-auto flex h-screen max-w-3xl flex-col">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-xl font-semibold text-navi-900">NAVI</h1>
        <p className="text-sm text-slate-500">Your AI guide through the U.S. healthcare system.</p>
      </header>
      <ChatInterface />
    </main>
  );
}
