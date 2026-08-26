"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { createPublicClient, http } from "viem";
import { baseSepolia } from "viem/chains";
import { useAccount, useConnect, useSwitchChain, useWriteContract } from "wagmi";
import { api, Analysis, Commitments, Incident, ProofRun, Scenario } from "../lib/api";

const receiptAbi = [{ type: "function", name: "recordIncident", stateMutability: "nonpayable", inputs: [
  { name: "incidentId", type: "bytes32" }, { name: "memoryContextHash", type: "bytes32" },
  { name: "decisionHash", type: "bytes32" }, { name: "outcomeHash", type: "bytes32" },
], outputs: [] }] as const;

const publicClient = createPublicClient({ chain: baseSepolia, transport: http(process.env.NEXT_PUBLIC_BASE_SEPOLIA_RPC_URL ?? "https://sepolia.base.org") });
const label = (value?: string) => (value ?? "—").split("_").map((part) => part[0]?.toUpperCase() + part.slice(1)).join(" ");
const pct = (value?: number) => `${Math.round((value ?? 0) * 100)}%`;

export default function Home() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState("payments-queue");
  const [incident, setIncident] = useState<Incident | null>(null);
  const [forget, setForget] = useState<Analysis | null>(null);
  const [remember, setRemember] = useState<Analysis | null>(null);
  const [health, setHealth] = useState<{ status: string; memory?: { status: string } } | null>(null);
  const [commitment, setCommitment] = useState<Commitments | null>(null);
  const [transactionHash, setTransactionHash] = useState<string | null>(null);
  const [notice, setNotice] = useState("Choose a deterministic incident or run the two-session proof.");
  const [busy, setBusy] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [proofOpen, setProofOpen] = useState(false);
  const [proof, setProof] = useState<ProofRun | null>(null);
  const { address, isConnected, chainId } = useAccount();
  const { connectors, connectAsync } = useConnect();
  const { switchChainAsync } = useSwitchChain();
  const { writeContractAsync } = useWriteContract();

  const activeScenario = useMemo(() => scenarios.find((item) => item.id === (incident?.scenario_id ?? selectedScenario)), [scenarios, incident, selectedScenario]);
  const activeAnalysis = remember ?? forget ?? incident?.last_analysis ?? null;
  const evidence = activeAnalysis?.relevant_memories ?? [];

  useEffect(() => {
    Promise.all([api<Scenario[]>("/api/scenarios"), api<{ status: string; memory: { status: string } }>("/api/health")])
      .then(async ([items, state]) => {
        setScenarios(items); setHealth(state);
        const params = new URLSearchParams(window.location.search);
        const proofId = params.get("proof");
        if (proofId) {
          const restoredProof = await api<ProofRun>(`/api/proof-runs/${proofId}`);
          setProof(restoredProof);
          setProofOpen(true);
          const restoredSession = restoredProof.session_b ?? restoredProof.session_a;
          if (restoredSession?.incident_snapshot) setIncident(restoredSession.incident_snapshot);
          if (restoredProof.session_b?.counterfactual_analysis) setForget(restoredProof.session_b.counterfactual_analysis);
          if (restoredProof.session_b?.memory_analysis) setRemember(restoredProof.session_b.memory_analysis);
          setNotice(`${proofId} restored entirely from Sibyl after refresh.`);
          return;
        }
        const incidentId = params.get("incident");
        if (incidentId) {
          const restored = await api<Incident>(`/api/incidents/${incidentId}`);
          setIncident(restored);
          setNotice(`${restored.incident_id} restored from Sibyl after refresh.`);
        }
      })
      .catch((error: Error) => { setHealth({ status: "degraded" }); setNotice(error.message); });
  }, []);

  function rememberIncident(incidentId: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("incident", incidentId);
    window.history.replaceState({}, "", url);
  }

  function rememberProof(runId: string) {
    const url = new URL(window.location.href);
    url.searchParams.delete("incident");
    url.searchParams.set("proof", runId);
    window.history.replaceState({}, "", url);
  }

  async function startScenario(scenarioId = selectedScenario) {
    setBusy(true); setForget(null); setRemember(null); setCommitment(null); setTransactionHash(null);
    try {
      const created = await api<Incident>("/api/incidents", { method: "POST", body: JSON.stringify({ scenario_id: scenarioId }) });
      setIncident(created); rememberIncident(created.incident_id); setNotice(`${created.incident_id} persisted to Sibyl. Choose FORGET or REMEMBER.`); return created;
    } catch (error) { setNotice((error as Error).message); throw error; }
    finally { setBusy(false); }
  }

  async function runAnalysis(mode: "forget" | "remember", target = incident) {
    if (!target) return null;
    setBusy(true);
    try {
      const result = await api<Analysis>(`/api/incidents/${target.incident_id}/analyze`, { method: "POST", body: JSON.stringify({ memory_mode: mode }) });
      if (mode === "forget") setForget(result); else setRemember(result);
      setNotice(mode === "remember" && result.memory_informed_decision.changed ? "Sibyl retrieved prior evidence and changed the decision." : `${mode.toUpperCase()} analysis complete.`);
      return result;
    } catch (error) { setNotice((error as Error).message); return null; }
    finally { setBusy(false); }
  }

  async function recordSessionA() {
    setBusy(true);
    try {
      const created = await api<ProofRun>("/api/proof-runs", { method: "POST" });
      const completed = await api<ProofRun>(`/api/proof-runs/${created.run_id}/session-a`, { method: "POST" });
      setProof(completed); rememberProof(completed.run_id); setForget(null); setRemember(null);
      if (completed.session_a?.incident_snapshot) setIncident(completed.session_a.incident_snapshot);
      setNotice(`SESSION A ENDED · Sibyl write ${completed.session_a?.sibyl_memory_id} confirmed. Start fresh Session B.`);
    } catch (error) { setNotice((error as Error).message); }
    finally { setBusy(false); }
  }

  async function runFreshSessionB() {
    if (!proof?.session_a?.process_ended) { setNotice("Run Session A and confirm its process ended first."); return; }
    setBusy(true);
    try {
      const completed = await api<ProofRun>(`/api/proof-runs/${proof.run_id}/session-b`, { method: "POST" });
      setProof(completed);
      if (completed.session_b?.incident_snapshot) setIncident(completed.session_b.incident_snapshot);
      setForget(completed.session_b?.counterfactual_analysis ?? null);
      setRemember(completed.session_b?.memory_analysis ?? null);
      setProofOpen(true);
      setNotice(completed.status === "passed" ? "FRESH PROCESS PROOF PASSED · MEMORY CHANGED THIS DECISION" : "Proof did not pass.");
    } catch (error) { setNotice((error as Error).message); }
    finally { setBusy(false); }
  }

  async function resolveRecommended() {
    if (!incident || !activeScenario || incident.status === "resolved") return;
    const action = activeAnalysis?.memory_informed_decision.action ?? incident.baseline_action;
    const [result, detail] = activeScenario.outcomes[action];
    setBusy(true);
    try {
      const resolved = await api<Incident>(`/api/incidents/${incident.incident_id}/resolve`, { method: "POST", body: JSON.stringify({
        executed_action: action, result, detail, recovery_time_minutes: activeScenario.recovery_minutes[action], operator_feedback: "accepted",
        successful_action: result === "better" ? action : activeScenario.preferred_action, supersedes: [],
      }) });
      setIncident(resolved);
      const hashes = await api<Commitments>(`/api/incidents/${incident.incident_id}/commitments`);
      setCommitment(hashes); setNotice("Outcome persisted to Sibyl. Base commitments are ready for operator anchoring.");
    } catch (error) { setNotice((error as Error).message); }
    finally { setBusy(false); }
  }

  async function anchorOnBase() {
    if (!commitment) return;
    const contract = (commitment.contract_address ?? process.env.NEXT_PUBLIC_BASE_RECEIPTS_CONTRACT) as `0x${string}` | undefined;
    if (!contract) { setNotice("Base proof is not anchored: contract address is not configured."); return; }
    try {
      if (!isConnected) { await connectAsync({ connector: connectors[0] }); setNotice("Wallet connected. Approve the Base Sepolia receipt transaction."); return; }
      if (chainId !== baseSepolia.id) await switchChainAsync({ chainId: baseSepolia.id });
      const hash = await writeContractAsync({ address: contract, abi: receiptAbi, functionName: "recordIncident", args: [commitment.incident_id_hash, commitment.memory_context_hash, commitment.decision_hash, commitment.outcome_hash], chainId: baseSepolia.id });
      setTransactionHash(hash); setNotice("Transaction submitted. Waiting for a verified Base receipt…");
      await publicClient.waitForTransactionReceipt({ hash });
      const verified = await api<Record<string, unknown>>(`/api/incidents/${incident!.incident_id}/provenance/verify`, { method: "POST", body: JSON.stringify({ transaction_hash: hash }) });
      setNotice(verified.status === "VERIFIED" ? "BASE INCIDENT RECEIPT VERIFIED" : "Proof was not verified.");
    } catch (error) { setNotice(`Base proof was not anchored: ${(error as Error).message}`); }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand"><span className="brandMark">M</span><div><b>MERCURY</b><small>PERSISTENT INCIDENT INTELLIGENCE</small></div></div>
        <nav className="topnav" aria-label="Command center sections"><a href="/mercury-demo.mp4" target="_blank" rel="noreferrer">DEMO VIDEO ↗</a><span>MEMORY TRACE</span><span>SAFETY</span><span>PROVENANCE</span></nav>
        <div className="systemState"><span className={`pulse ${health?.status === "degraded" ? "bad" : ""}`} /> SIBYL MEMORY {health?.memory?.status?.toUpperCase() ?? "CHECKING"}<em>BASE SEPOLIA · {transactionHash ? "PENDING/VERIFIED" : "UNANCHORED"}</em></div>
      </header>

      <section className="demoRail panel">
        <div><span className="tag">LOAD-BEARING MEMORY PROOF</span><b>{notice}</b></div>
        <div className="railActions"><button onClick={recordSessionA} disabled={busy}>1 · RUN SESSION A</button><button className="primary" onClick={runFreshSessionB} disabled={busy || !proof?.session_a?.process_ended}>2 · START FRESH SESSION B</button><button onClick={() => setProofOpen(!proofOpen)} disabled={!proof}>VIEW PROOF {proofOpen ? "×" : "↗"}</button></div>
      </section>

      {proofOpen && proof && <section className="proofPanel panel" aria-label="Cross-session Sibyl proof inspector">
        <div className="eyebrow"><span>VIEW PROOF · REAL CROSS-PROCESS ELIGIBILITY</span><b>{proof.status === "passed" ? "PROOF PASSED" : proof.status.toUpperCase()}</b></div>
        <div className="proofFlow">
          <div><small>SESSION A</small><b>{proof.session_a?.session_id ?? "NOT RUN"}</b><code>PID {proof.session_a?.process_id ?? "—"}</code><p>Baseline: <strong>{proof.session_a?.baseline_decision?.action ?? "—"}</strong></p><p>Bad outcome: {proof.session_a?.recorded_outcome?.detail ?? "—"}</p></div>
          <span>→</span>
          <div><small>SIBYL WRITE</small><b>{proof.session_a?.write_confirmed ? "WRITE CONFIRMED" : "PENDING"}</b><code>{proof.session_a?.sibyl_memory_id ?? "—"}</code><p>Read-after-write: {proof.session_a?.read_after_write_confirmed ? "confirmed" : "pending"}</p><p>Session A ended: {proof.session_a?.orchestrator_confirmed_exit_code === 0 ? "yes · exit 0" : "pending"}</p></div>
          <span>→</span>
          <div><small>FRESH SESSION B</small><b>{proof.session_b?.session_id ?? "NOT RUN"}</b><code>PID {proof.session_b?.process_id ?? "—"}</code><p>Retrieval event: {proof.session_b?.sibyl_retrieval_event_id ?? "—"}</p><p>Retrieved: {proof.session_b?.retrieved_experience?.incident_id ?? "—"}</p></div>
        </div>
        {proof.status === "passed" && <div className="proofVerdict"><b>MEMORY CHANGED THIS DECISION</b><span>Without memory: <code>{proof.session_b?.counterfactual_decision?.action}</code></span><span>With Sibyl memory: <code>{proof.session_b?.memory_informed_decision?.action}</code></span></div>}
        <div className="proofDetails"><div><small>PROOF RUN / SIBYL RECORD</small><code>{proof.run_id} · {proof.sibyl_proof_record_id}</code><small>PROCESS ISOLATION</small><code>{proof.session_a?.process_id ?? "—"} ≠ {proof.session_b?.process_id ?? "—"} · tenant-isolated={String(proof.storage.tenant_isolated)}</code></div><div><small>RETRIEVED EXPERIENCE</small><code>{proof.session_b?.retrieved_experience ? `${proof.session_b.retrieved_experience.incident_id} · score ${pct(proof.session_b.retrieved_experience.score.total)} · ${proof.session_b.retrieved_experience.attempted_actions[0]?.detail}` : "—"}</code><small>BASE PROVENANCE</small><code>{proof.base.status} · chain {proof.base.chain_id} · {proof.base.transaction_hash ?? "no verified transaction"}</code></div></div>
      </section>}

      {!incident ? (
        <section className="launchPanel panel">
          <div className="heroFrame" aria-hidden="true"><span className="corner tl"/><span className="corner tr"/><span className="corner bl"/><span className="corner br"/><div className="scanLine" /></div>
          <div className="heroCopy"><p className="kicker">LOAD-BEARING AGENT MEMORY · 01</p><h1>MEMORY<br />CHANGED<br /><span>THE DECISION.</span></h1><p className="lede">A fresh MERCURY session behaves differently because Sibyl remembers the last operational failure.</p></div>
          <div className="brainStage" aria-label="Wireframe brain representing persistent Sibyl memory"><div className="brainHalo"/><Image className="brainVisual" src="/memory-brain.png" alt="White wireframe brain representing persistent incident memory" width={768} height={768} priority/><span className="memoryNode n1"/><span className="memoryNode n2"/><span className="memoryNode n3"/></div>
          <div className="heroEvidence"><small>MEMORY ARCHITECTURE</small><b>SIBYL / SQLITE / FTS5</b><p>Incident outcomes survive process restarts and return as decision evidence—not decorative history.</p><dl><div><dt>RELEVANCE GATE</dt><dd>≥ 0.55</dd></div><div><dt>SAFETY OVERRIDE</dt><dd>NEVER</dd></div><div><dt>CHAIN PROOF</dt><dd>BASE</dd></div></dl></div>
          <div className="heroCaption"><span>INCIDENT RESPONSE THAT COMPOUNDS</span><b>WHAT FAILED ONCE BECOMES A SAFETY RAIL.</b></div>
          <div className="scenarioPicker"><label htmlFor="scenario">SELECT DETERMINISTIC INCIDENT</label><select id="scenario" value={selectedScenario} onChange={(event) => setSelectedScenario(event.target.value)}>{scenarios.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}</select><button className="primary large" disabled={busy || !scenarios.length} onClick={() => startScenario()}>ENTER COMMAND CENTER ↗</button><small>SIMULATED TELEMETRY · REAL SIBYL PERSISTENCE</small></div>
        </section>
      ) : (
        <section className="commandGrid">
          <article className="incidentPanel panel">
            <div className="eyebrow"><span>CURRENT INCIDENT</span><strong>{incident.status === "resolved" ? "RESOLVED" : "SEV-1 · ACTIVE"}</strong></div>
            <h1>{incident.service}<br /><span>{incident.title}</span></h1><p className="incidentId">{incident.incident_id} · SIMULATED TELEMETRY · SIBYL ENTITY</p>
            <div className="metrics">{incident.telemetry.map((metric) => <div key={metric.label}><small>{metric.label}</small><b>{metric.value}</b><i>{metric.delta}</i></div>)}</div>
            <div className="symptoms"><small>OBSERVED SIGNALS</small>{incident.symptoms.map((symptom) => <span key={symptom}>{symptom}</span>)}</div>
            <div className="modeButtons"><button onClick={() => runAnalysis("forget")} disabled={busy}>FORGET · BYPASS MEMORY</button><button className="primary" onClick={() => runAnalysis("remember")} disabled={busy}>REMEMBER · QUERY SIBYL</button></div>
          </article>

          <aside className="memoryPanel panel">
            <div className="eyebrow"><span>MEMORY RETRIEVAL</span><b className={activeAnalysis?.memory_status === "degraded" ? "danger" : "live"}>{activeAnalysis?.memory_status?.toUpperCase() ?? "NOT QUERIED"}</b></div>
            {evidence[0] ? <><div className="memoryHero"><small>MOST RELEVANT · {pct(evidence[0].score.total)} MATCH</small><h2>{evidence[0].incident_id}</h2><p>Sibyl confidence · {pct(evidence[0].confidence)}</p></div><dl><div><dt>FAILED ACTION</dt><dd>{label(evidence[0].attempted_actions.find((a) => a.result === "worse")?.action)}</dd></div><div><dt>OBSERVED OUTCOME</dt><dd className="danger">{evidence[0].attempted_actions.find((a) => a.result === "worse")?.detail ?? "No failed action"}</dd></div><div><dt>SUCCESSFUL ACTION</dt><dd>{label(evidence[0].successful_action?.action)}</dd></div></dl></> : <div className="emptyMemory"><span>∅</span><h2>{activeAnalysis?.memory_status === "bypassed" ? "Memory deliberately bypassed" : "No qualifying memory"}</h2><p>{activeAnalysis ? "Sibyl was not allowed to influence this result." : "Run REMEMBER to query durable incident history."}</p></div>}
            <button type="button" className="evidenceButton" onClick={() => setEvidenceOpen(!evidenceOpen)}>Technical evidence <span>{evidenceOpen ? "×" : "↗"}</span></button>
          </aside>

          <section className="decisionPanel panel">
            <div className="eyebrow"><span>WITHOUT MEMORY VS WITH MEMORY</span><b>CONFIDENCE {pct(activeAnalysis?.memory_informed_decision.confidence)}</b></div>
            <div className="comparison"><div className="without"><small>WITHOUT MEMORY</small><h3>{label(activeAnalysis?.baseline_decision.action ?? incident.baseline_action)}</h3><p>Baseline confidence · {pct(activeAnalysis?.baseline_decision.confidence ?? .72)}</p></div><div className="arrow">→</div><div className="with"><small>WITH SIBYL MEMORY</small><h3>{label(activeAnalysis?.memory_informed_decision.action ?? incident.baseline_action)}</h3><p>Memory-informed confidence · {pct(activeAnalysis?.memory_informed_decision.confidence ?? .72)}</p></div></div>
            {activeAnalysis?.memory_informed_decision.changed ? <div className="impact"><span>✓</span><div><b>MEMORY CHANGED THIS DECISION</b><p>{activeAnalysis.explanation.how_memory_changed}</p></div></div> : <div className="noImpact">MEMORY DID NOT CHANGE THIS DECISION · {activeAnalysis?.memory_status?.toUpperCase() ?? "ANALYSIS PENDING"}</div>}
          </section>

          <aside className="actionPanel panel"><div className="eyebrow"><span>ACTION / ESCALATION</span><b>{activeAnalysis?.policy.approval_required ? "HUMAN GATE" : "POLICY CLEAR"}</b></div><h3>{incident.status === "resolved" ? "SIMULATED RESPONSE COMPLETE" : activeAnalysis?.policy.approval_required ? "AWAITING OPERATOR APPROVAL" : "READY FOR SAFE RESPONSE"}</h3><p>{activeAnalysis?.policy.reason ?? "Analyze the incident before approving a response."}</p>{incident.status === "open" ? <button onClick={resolveRecommended} disabled={busy || !activeAnalysis}>APPROVE SIMULATED RESPONSE</button> : <div className="outcome"><small>OUTCOME</small><b>{incident.outcome?.result.toUpperCase()}</b><p>{incident.outcome?.detail}</p></div>}<small>NO PRODUCTION ACTIONS WILL RUN</small></aside>

          {evidenceOpen && <section className="evidencePanel panel"><div className="eyebrow"><span>TECHNICAL EVIDENCE PANEL</span><b>EXPLAINABLE PIPELINE</b></div><div className="evidenceColumns"><div><small>RETRIEVAL QUERY</small><code>{activeAnalysis?.retrieval_terms.join(" · ") || "—"}</code><small>SIBYL MEMORY IDS</small><code>{evidence.map((item) => item.incident_id).join(", ") || "none"}</code></div><div><small>INFLUENCE</small><code>{activeAnalysis?.explanation.memory_retrieved ?? "—"}</code><small>POLICY</small><code>{activeAnalysis ? `${activeAnalysis.policy.risk_class} · approval=${activeAnalysis.policy.approval_required}` : "—"}</code></div></div><details><summary>Execution trace · {activeAnalysis?.trace.length ?? 0} steps</summary><ol>{activeAnalysis?.trace.map((step, index) => <li key={index}><b>{String(step.step)}</b><code>{JSON.stringify(step)}</code></li>)}</ol></details></section>}

          {incident.status === "resolved" && <section className="provenancePanel panel"><div className="eyebrow"><span>BASE INCIDENT RECEIPT</span><b>{transactionHash ? "SUBMITTED" : "NOT ANCHORED"}</b></div><div className="hashGrid"><div><small>INCIDENT</small><code>{incident.incident_id}</code></div><div><small>MEMORY CONTEXT</small><code>{commitment?.memory_context_hash ?? "Generate commitments after resolution"}</code></div><div><small>DECISION</small><code>{commitment?.decision_hash ?? "—"}</code></div><div><small>OUTCOME</small><code>{commitment?.outcome_hash ?? "—"}</code></div><div><small>TRANSACTION</small><code>{transactionHash ?? "Not anchored"}</code></div><div><small>OPERATOR</small><code>{address ?? "Wallet not connected"}</code></div></div><button className="primary" onClick={anchorOnBase} disabled={busy || !commitment}>{isConnected ? "ANCHOR ON BASE SEPOLIA" : "CONNECT OPERATOR WALLET"}</button></section>}
        </section>
      )}
      <footer><span>REAL · SIBYL PERSISTENCE + DECISION INFLUENCE</span><span>SIMULATED · INCIDENT TELEMETRY + MITIGATIONS</span><span>OPTIONAL · VIRTUALS ACP DEFERRED</span></footer>
    </main>
  );
}
