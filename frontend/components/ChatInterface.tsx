"use client";

import { useState } from "react";
import { api, AgentStep } from "@/lib/api";

type Message = {
  role: "user" | "navi";
  text: string;
  steps?: AgentStep[];
  escalated?: boolean;
  containsSimulatedData?: boolean;
};

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [journeyId, setJourneyId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMessage = input.trim();
    setMessages((prev) => [...prev, { role: "user", text: userMessage }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await api.sendMessage(userMessage, journeyId);
      setJourneyId(response.journey_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "navi",
          text: response.reply,
          steps: response.steps,
          escalated: response.escalated,
          containsSimulatedData: response.contains_simulated_data,
        },
      ]);
    } catch (err) {
      setError("NAVI couldn't process that request. Please sign in and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-6">
        {messages.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-300 p-6 text-slate-500">
            Try: <span className="font-medium">&ldquo;My doctor ordered an MRI for my knee&rdquo;</span>
          </div>
        )}
        {messages.map((message, index) => (
          <div key={index} className={message.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block max-w-2xl rounded-2xl px-4 py-3 text-sm ${
                message.role === "user" ? "bg-navi-600 text-white" : "bg-white text-slate-800 shadow-sm"
              }`}
            >
              {message.text}
            </div>
            {message.containsSimulatedData && (
              <div className="mt-2 inline-block rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-left text-xs text-amber-800">
                ⚠ Some figures above are from NAVI&apos;s demo/simulation mode, not a live check with your
                insurer — confirm before relying on them.
              </div>
            )}
            {message.steps && message.steps.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {message.steps.map((step, stepIndex) => (
                  <span
                    key={stepIndex}
                    className="rounded-full bg-navi-50 px-3 py-1 text-xs font-medium text-navi-900"
                  >
                    {step.agent_name.replace("_", " ")}
                  </span>
                ))}
                {message.escalated && (
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                    escalated for human review
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-sm text-slate-400">NAVI's agents are working on it…</div>}
        {error && <div className="text-sm text-red-500">{error}</div>}
      </div>

      <div className="border-t border-slate-200 bg-white p-4">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm outline-none focus:border-navi-500"
            placeholder="Describe what your doctor ordered…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="rounded-lg bg-navi-600 px-5 py-2 text-sm font-medium text-white hover:bg-navi-500 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
