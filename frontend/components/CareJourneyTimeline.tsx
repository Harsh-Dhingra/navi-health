import { CareJourney } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  in_progress: "bg-amber-100 text-amber-800",
  completed: "bg-emerald-100 text-emerald-800",
  escalated: "bg-red-100 text-red-800",
};

export default function CareJourneyTimeline({ journey }: { journey: CareJourney }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h3 className="font-medium text-slate-900">{journey.title}</h3>
          <p className="text-xs text-slate-400">{new Date(journey.created_at).toLocaleString()}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${STATUS_COLORS[journey.status] ?? "bg-slate-100"}`}>
          {journey.status.replace("_", " ")}
        </span>
      </div>
      <ol className="space-y-2 border-l border-slate-200 pl-4">
        {journey.steps.map((step, index) => (
          <li key={index} className="text-sm text-slate-600">
            <span className="font-medium text-slate-800">{step.agent_name.replace("_", " ")}</span>
            {" — "}
            {step.status}
            {step.requires_human_review && (
              <span className="ml-2 rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700">needs review</span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
