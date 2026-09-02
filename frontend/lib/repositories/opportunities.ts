import { demoOpportunities } from "@/lib/demo/opportunities";
import type { Opportunity } from "@/types/opportunity";
export function listOpportunities(): Opportunity[] { return demoOpportunities; }
export function findOpportunity(id: string): Opportunity | undefined { return demoOpportunities.find((item) => item.id === id); }
