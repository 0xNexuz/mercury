// Same-origin by default. Next proxies /api to FastAPI, which lets one local
// Cloudflare Tunnel expose the complete dashboard without exposing SQLite.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export type ActionOutcome = ["better" | "neutral" | "worse", string];
export type Scenario = {
  id: string; title: string; service: string; category: string; symptoms: string[];
  baseline_action: string; preferred_action: string; candidate_actions: string[];
  telemetry: { label: string; value: string; delta: string }[];
  outcomes: Record<string, ActionOutcome>; recovery_minutes: Record<string, number>;
};
export type Evidence = {
  incident_id: string; score: { total: number; service: number; symptoms: number; category: number; error_signature: number; dependency: number };
  confidence: number; attempted_actions: { action: string; result: string; detail?: string }[];
  successful_action?: { action: string; detail?: string };
};
export type Analysis = {
  incident_id: string; memory_mode: "forget" | "remember"; memory_status: string; retrieval_terms: string[];
  baseline_decision: { action: string; confidence: number };
  memory_informed_decision: { action: string; confidence: number; changed: boolean; memory_evidence: string[] };
  policy: { risk_class: string; approval_required: boolean; reason: string };
  relevant_memories: Evidence[]; explanation: Record<string, string>; trace: Record<string, unknown>[];
};
export type Incident = Scenario & {
  incident_id: string; scenario_id: string; status: "open" | "resolved"; created_at: string;
  outcome?: { executed_action: string; result: string; detail: string; recovery_time_minutes: number };
  last_analysis?: Analysis; base_receipt?: Record<string, unknown>; trace: Record<string, unknown>[];
};
export type Commitments = {
  incident_id: string; incident_id_hash: `0x${string}`; memory_context_hash: `0x${string}`;
  decision_hash: `0x${string}`; outcome_hash: `0x${string}`; contract_address?: `0x${string}`;
  chain_id: number; status: string;
};
