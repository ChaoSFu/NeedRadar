"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getOpportunity } from "@/lib/api";
import type { Opportunity } from "@/types/opportunity";

export default function OpportunityPage() {
  const params = useParams<{ id: string }>();
  const [item, setItem] = useState<Opportunity | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { getOpportunity(params.id).then(setItem).catch(() => setError("机会不存在，或 Python API 未启动。")); }, [params.id]);
  if (error) return <main className="mx-auto max-w-4xl px-6 py-10"><Link href="/radar" className="text-blue-700">← Back to Radar</Link><p className="mt-6 rounded-lg bg-red-50 p-4 text-red-700">{error}</p></main>;
  if (!item) return <main className="mx-auto max-w-4xl px-6 py-10 text-slate-500">Loading opportunity…</main>;
  return <main className="mx-auto max-w-4xl px-6 py-10"><Link href="/radar" className="text-sm text-blue-700">← Back to Radar</Link><header className="mt-6 rounded-2xl bg-slate-900 p-7 text-white"><p className="text-sm text-blue-200">{item.region} · {item.category} · Demo data</p><div className="mt-2 flex flex-wrap items-end justify-between gap-4"><h1 className="text-3xl font-semibold">{item.title}</h1><div className="flex gap-5"><div><b className="text-2xl">{item.marketScore}</b><p className="text-xs text-slate-300">Market Score</p></div><div><b className="text-2xl">{item.confidenceScore}</b><p className="text-xs text-slate-300">Confidence · {item.confidenceLabel}</p></div></div></div><p className="mt-4 text-slate-200">{item.oneLineSummary}</p></header><div className="mt-7 grid gap-4 md:grid-cols-2"><Section title="The problem">{item.problem}</Section><Section title="Target user">{item.targetUser}</Section><Section title="Job to be done">{item.jobToBeDone}</Section><Section title="Why now">{item.whyNow}</Section><Section title="Why AI">{item.aiAngle}</Section><Section title="Possible MVP">{item.possibleMvp}</Section></div><section className="mt-7 rounded-xl border border-slate-200 bg-white p-6"><h2 className="text-lg font-semibold">Pain points</h2><ul className="mt-3 list-disc space-y-1 pl-5 text-slate-700">{item.painPoints.map((point) => <li key={point}>{point}</li>)}</ul><h2 className="mt-6 text-lg font-semibold">Existing workarounds</h2><p className="mt-2 text-slate-700">{item.workarounds.join(" · ")}</p></section><section className="mt-7 rounded-xl border border-slate-200 bg-white p-6"><h2 className="text-lg font-semibold">Original evidence</h2><p className="mt-1 text-sm text-slate-500">Evidence remains traceable to raw signals; it is not AI-generated.</p>{item.evidence.map((evidence) => <article key={evidence.query} className="mt-4 rounded-lg bg-slate-50 p-4"><div className="flex flex-wrap gap-x-3 text-xs text-slate-500"><span>{evidence.platform}</span><span>{evidence.observedAt}</span><span>{evidence.region}</span></div><p className="mt-2 font-medium">Query: {evidence.query}</p><p className="mt-1 text-slate-700">“{evidence.excerpt}”</p><a className="mt-2 inline-block text-sm text-blue-700" href={evidence.sourceUrl} target="_blank" rel="noreferrer">Open source ↗</a></article>)}</section><div className="mt-7 flex flex-wrap gap-3"><button className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">Watch</button><button className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm">Reject</button><button className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white">Test this opportunity</button></div></main>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) { return <section className="rounded-xl border border-slate-200 bg-white p-5"><h2 className="font-semibold">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{children}</p></section>; }
