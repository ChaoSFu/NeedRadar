import type { Opportunity, OpportunitySummary } from "@/types/opportunity";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export function getOpportunities(): Promise<OpportunitySummary[]> {
  return request<OpportunitySummary[]>("/opportunities");
}

export function getOpportunity(id: string): Promise<Opportunity> {
  return request<Opportunity>(`/opportunities/${encodeURIComponent(id)}`);
}
