"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (mode === "register") {
        await api.register(email, password, fullName);
      }
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      router.push("/");
    } catch (err) {
      setError("Could not authenticate. Check your credentials and that the backend is running.");
    }
  }

  return (
    <main className="mx-auto flex h-screen max-w-md flex-col justify-center px-6">
      <h1 className="mb-1 text-2xl font-semibold text-navi-900">NAVI</h1>
      <p className="mb-6 text-sm text-slate-500">
        {mode === "login" ? "Sign in to continue" : "Create your account"}
      </p>
      <form onSubmit={handleSubmit} className="space-y-3">
        {mode === "register" && (
          <input
            className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm"
            placeholder="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        )}
        <input
          type="email"
          required
          className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          required
          className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <button
          type="submit"
          className="w-full rounded-lg bg-navi-600 px-4 py-2 text-sm font-medium text-white hover:bg-navi-500"
        >
          {mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>
      <button
        className="mt-4 text-sm text-navi-600 hover:underline"
        onClick={() => setMode(mode === "login" ? "register" : "login")}
      >
        {mode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
      </button>
    </main>
  );
}
