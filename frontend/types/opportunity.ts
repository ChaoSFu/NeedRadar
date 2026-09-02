export type OpportunitySummary = {
  id: string; title: string; region: string; category: string; momentum: "Rising" | "Surging" | "Stable";
  marketScore: number; confidenceScore: number; confidenceLabel: "Low" | "Medium" | "High"; oneLineSummary: string;
  whyNow: string;
};

export type Opportunity = OpportunitySummary & {
  problem: string; targetUser: string;
  jobToBeDone: string; painPoints: string[]; whyNow: string; workarounds: string[]; aiAngle: string; possibleMvp: string;
  evidence: { query: string; excerpt: string; platform: string; observedAt: string; region: string; sourceUrl: string }[];
};
