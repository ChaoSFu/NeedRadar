"use client";

import { useEffect, useState } from "react";
import { OpportunityCard } from "@/components/opportunity-card";
import { getOpportunities } from "@/lib/api";
import type { OpportunitySummary } from "@/types/opportunity";

export default function RadarPage() {
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOpportunities().then(setOpportunities).catch(() => setError("暂时无法加载机会数据，请确认 Python API 已启动。"));
  }, []);

  return <main className="mx-auto max-w-6xl px-6 py-12"><p className="text-sm font-medium text-blue-700">DAILY OPPORTUNITY FEED</p><h1 className="mt-2 text-4xl font-semibold tracking-tight">Find your next AI opportunity.</h1><p className="mt-3 max-w-2xl text-slate-600">Discover what people need before you build. All signals below are clearly marked demo data.</p><div className="mt-7 flex flex-wrap gap-3 text-sm"><span className="rounded-full bg-blue-50 px-3 py-2 text-blue-700">{opportunities.length || "…"} demo opportunities detected</span><span className="rounded-full border border-slate-200 bg-white px-3 py-2">All regions · Emerging first</span></div>{error ? <p className="mt-8 rounded-lg bg-red-50 p-4 text-red-700">{error}</p> : null}<section className="mt-8 grid gap-4 md:grid-cols-2">{opportunities.map((opportunity) => <OpportunityCard key={opportunity.id} opportunity={opportunity} />)}</section>{!error && opportunities.length === 0 ? <p className="mt-8 text-slate-500">Loading opportunities…</p> : null}</main>;
}
