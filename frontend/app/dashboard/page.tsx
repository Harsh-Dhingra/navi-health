"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, CareJourney } from "@/lib/api";
import CareJourneyTimeline from "@/components/CareJourneyTimeline";

export default function DashboardPage() {
  const [journeys, setJourneys] = useState<CareJourney[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listCareJourneys()
      .then(setJourneys)
      .catch(() => setError("Sign in to view your care journeys."));
  }, []);

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-navi-900">Your care journeys</h1>
          <p className="text-sm text-slate-500">Every request NAVI has helped you navigate.</p>
        </div>
        <Link href="/" className="text-sm font-medium text-navi-600 hover:underline">
          New request →
        </Link>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="space-y-4">
        {journeys.map((journey) => (
          <CareJourneyTimeline key={journey.id} journey={journey} />
        ))}
        {!error && journeys.length === 0 && (
          <p className="text-sm text-slate-400">No care journeys yet — start one from the chat.</p>
        )}
      </div>
    </main>
  );
}
