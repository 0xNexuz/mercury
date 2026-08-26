import type { Metadata } from "next";
import Link from "next/link";
import "./docs.css";

export const metadata: Metadata = {
  title: "Build Documentation · MERCURY",
  description: "Technical guide to MERCURY's memory, decisions, proof, safety, provenance, deployment, and tests.",
};

const endpoints = [
  ["GET", "/api/health", "Checks the real Sibyl store and reports Base configuration."],
  ["GET", "/api/scenarios", "Returns six deterministic incident fixtures and labeled simulated telemetry."],
  ["POST", "/api/incidents", "Validates input, assigns INC-###, fingerprints it, and persists an open Sibyl entity."],
  ["GET", "/api/incidents/{id}", "Reloads the complete incident from Sibyl after navigation or refresh."],
  ["POST", "/api/incidents/{id}/analyze", "Runs FORGET or REMEMBER and returns decisions, evidence, policy, and trace."],
  ["POST", "/api/incidents/{id}/resolve", "Persists the operator-confirmed outcome and updates memory quality."],
  ["GET", "/api/incidents/{id}/trace", "Returns the ordered explainability trace."],
  ["GET", "/api/incidents/{id}/commitments", "Creates four canonical commitments for a resolved incident."],
  ["POST", "/api/incidents/{id}/provenance/verify", "Verifies a real Base Sepolia receipt before attaching VERIFIED status."],
  ["POST", "/api/proof-runs", "Creates an unguessable, tenant-isolated eligibility proof in Sibyl."],
  ["GET", "/api/proof-runs/{id}", "Restores the proof inspector directly from Sibyl."],
  ["POST", "/api/proof-runs/{id}/session-a", "Runs, persists, verifies, and terminates the first Python worker."],
  ["POST", "/api/proof-runs/{id}/session-b", "Launches a different worker and proves Sibyl changed the decision."],
];

const functions = [
  ["memory.py", "_client", "Opens official MemoryClient.local storage for the configured tenant."],
  ["memory.py", "save / get / search", "Writes and reloads incidents and performs FTS5 candidate generation."],
  ["memory.py", "set_entity / get_entity / journal", "Stores proof state and activity in the same Sibyl database."],
  ["engine.py", "normalize / token_set / fingerprint", "Creates stable matching features from incident signals."],
  ["engine.py", "retrieval_terms", "Produces de-duplicated FTS5 terms from the fingerprint."],
  ["engine.py", "score_memory", "Calculates every weighted relevance component and total."],
  ["engine.py", "analyze", "Builds the baseline, applies outcome influence, selects an action, and emits explanations."],
  ["engine.py", "policy_for", "Classifies the final action after memory influence."],
  ["proof.py", "create_run / get_run", "Creates and restores the isolated proof record from Sibyl."],
  ["proof.py", "run_lock / execute_worker", "Serializes a phase, launches a subprocess, and records its real exit."],
  ["proof_worker.py", "run_session_a", "Records the failed restart through the production incident functions."],
  ["proof_worker.py", "run_session_b", "Runs FORGET and REMEMBER in a new PID and requires Session A evidence."],
  ["provenance.py", "canonical_json / keccak256", "Serializes sorted compact UTF-8 JSON and hashes it."],
  ["provenance.py", "commitments", "Commits incident, exact memory context, decision plus policy, and outcome."],
  ["provenance.py", "verify_receipt", "Checks chain, success, contract, event signature, and all commitments."],
  ["page.tsx", "recordSessionA / runFreshSessionB", "Drives the hosted proof only through API responses."],
  ["page.tsx", "runAnalysis / resolveRecommended", "Runs comparisons and records operator-confirmed outcomes."],
  ["page.tsx", "anchorOnBase", "Submits commitments through the operator wallet and requests server verification."],
];

function Title({ n, title, copy }: { n: string; title: string; copy: string }) {
  return <header className="docTitle"><span>{n}</span><div><h2>{title}</h2><p>{copy}</p></div></header>;
}

export default function DocsPage() {
  return <main className="docsShell">
    <header className="docsTopbar">
      <Link className="docsBrand" href="/"><span>M</span><div><b>MERCURY</b><small>BUILD DOCUMENTATION</small></div></Link>
      <nav><a href="#architecture">ARCHITECTURE</a><a href="#memory">MEMORY</a><a href="#api">API</a><a href="#safety">SAFETY</a><a href="#provenance">BASE</a></nav>
      <Link className="backCommand" href="/">COMMAND CENTER ↗</Link>
    </header>

    <section className="docsHero">
      <div><p>SYSTEM REFERENCE · VERSION 0.1</p><h1>HOW MERCURY<br/><span>REMEMBERS.</span></h1><div className="docsLead">A complete technical guide—from simulated signal to real Sibyl memory, deterministic decision influence, human safety policy, and optional Base proof.</div></div>
      <aside><small>TRUTH LABELS</small><dl><div><dt>REAL</dt><dd>Sibyl storage, retrieval, decisions, hashes, verified receipts</dd></div><div><dt>SIMULATED</dt><dd>Telemetry, mitigations, outcomes, recovery times</dd></div><div><dt>DEFERRED</dt><dd>Virtuals ACP specialist integration</dd></div></dl></aside>
    </section>

    <div className="docsLayout">
      <aside className="docsToc"><small>ON THIS PAGE</small><a href="#thesis">01 · Thesis</a><a href="#architecture">02 · Architecture</a><a href="#incident">03 · Incident lifecycle</a><a href="#memory">04 · Sibyl memory</a><a href="#decision">05 · Decision engine</a><a href="#proof">06 · Cross-session proof</a><a href="#safety">07 · Safety</a><a href="#provenance">08 · Base provenance</a><a href="#api">09 · Public API</a><a href="#functions">10 · Functions</a><a href="#hosting">11 · Hosting</a><a href="#testing">12 · Testing</a></aside>
      <article className="docsContent">
        <section id="thesis"><Title n="01" title="Product thesis" copy="Operational experience must change future eligibility—not decorate a history panel."/><div className="docCallout"><b>LOAD-BEARING MEMORY</b><p>Remove Sibyl and the incident returns to <code>restart_worker</code>. Retrieve the qualifying failure and MERCURY selects <code>drain_queue_then_rollback</code>. No LLM exists in this critical path.</p></div></section>

        <section id="architecture"><Title n="02" title="System architecture" copy="One browser, one stateless API, one durable application store, and optional chain proof."/><div className="architectureFlow"><span>OPERATOR UI<small>Next.js · wagmi · viem</small></span><i>→</i><span>FASTAPI<small>validation · orchestration</small></span><i>→</i><span>SIBYL<small>SQLite · FTS5 · journal</small></span><i>→</i><span>BASE<small>verified receipts only</small></span></div><p>Next.js proxies same-origin API requests to FastAPI. The API opens <code>MemoryClient.local(...)</code>. Incidents, outcomes, feedback, traces, proof runs, and verified receipts are Sibyl records. React state is display-only.</p></section>

        <section id="incident"><Title n="03" title="Incident lifecycle" copy="Every transition is validated, explainable, and persisted."/><ol className="timeline"><li><b>CREATE</b><p>Validate input, reject unknown actions, assign an ID, fingerprint the incident, and persist it as open.</p></li><li><b>ANALYZE</b><p>Produce the baseline. FORGET bypasses Sibyl; REMEMBER performs real retrieval, scoring, influence, then safety classification.</p></li><li><b>APPROVE</b><p>High-risk and destructive recommendations wait for explicit operator approval.</p></li><li><b>RESOLVE</b><p>Persist outcome, feedback, recovery time, reuse quality, and explicit supersession.</p></li><li><b>ANCHOR</b><p>Create commitments after resolution and mark VERIFIED only after receipt verification.</p></li></ol></section>

        <section id="memory"><Title n="04" title="Sibyl memory" copy="The official local-first SDK is the only durable cross-session incident store."/><div className="twoCol"><div><h3>Entity tier</h3><p>Category <code>incident</code>, keyed by incident ID. It stores fingerprints, attempts, outcomes, feedback, confidence, reuse, supersession, trace, and receipts.</p></div><div><h3>Journal tier</h3><p>Records creation, analysis, resolution, proof writes, and retrieval events. Journal IDs appear in technical evidence.</p></div></div><p>Search terms come from normalized service, category, symptoms, dependency, and error signature. Only resolved, non-superseded memories influence decisions. Failure produces a visible degraded state.</p><div className="confidence"><span>START <b>0.80</b></span><span>SUCCESS <b>+0.05 · MAX 0.98</b></span><span>FAILURE <b>−0.15 · MIN 0.10</b></span></div></section>

        <section id="decision"><Title n="05" title="Deterministic decision engine" copy="Every score component, action adjustment, and policy result is inspectable."/><div className="weights"><div><b>35%</b><span>Service</span></div><div><b>30%</b><span>Symptoms</span></div><div><b>20%</b><span>Category</span></div><div><b>10%</b><span>Error</span></div><div><b>5%</b><span>Dependency</span></div></div><p>The relevance gate is <code>0.55</code>. Worse outcomes penalize matching actions by relevance × confidence; validated alternatives receive a stronger boost. Without qualifying evidence, memory cannot change the result.</p><pre><code>baseline  restart_worker · 0.72<br/>memory    INC-104 · score 1.00 · confidence 0.80<br/>penalty   restart_worker<br/>boost     drain_queue_then_rollback<br/>result    drain_queue_then_rollback · 0.91</code></pre></section>

        <section id="proof"><Title n="06" title="Real cross-session proof" copy="The hosted flow demonstrates process termination and retrieval—not browser continuity."/><div className="proofSteps"><div><span>A</span><b>Session A</b><p>Runs FORGET, records the bad restart, confirms Sibyl read-after-write, and exits.</p></div><div><span>×</span><b>Termination</b><p>The orchestrator records PID, exit code, and time before enabling Session B.</p></div><div><span>B</span><b>Fresh Session B</b><p>Uses a new UUID and PID, queries Sibyl, cites Session A, and proves the action change.</p></div></div><p>Each judge has a random proof ID and dedicated Sibyl tenant. Refresh uses the URL only as a locator and reconstructs all evidence from Sibyl. A lock coordinates duplicate requests but contains no incident state.</p></section>

        <section id="safety"><Title n="07" title="Safety policy" copy="Memory may inform an action but can never weaken its risk classification."/><table><thead><tr><th>Class</th><th>Rule</th><th>Example</th></tr></thead><tbody><tr><td>Safe observation</td><td>May proceed autonomously</td><td><code>observe_metrics</code></td></tr><tr><td>Reversible</td><td>Follows configured policy</td><td><code>restart_worker</code></td></tr><tr><td>High risk</td><td>Human approval mandatory</td><td><code>drain_queue_then_rollback</code></td></tr><tr><td>Destructive</td><td>Human approval mandatory</td><td><code>flush_cache</code></td></tr></tbody></table><div className="docWarning"><b>SIMULATION BOUNDARY</b><p>No production infrastructure action is executed in this release.</p></div></section>

        <section id="provenance"><Title n="08" title="Base provenance" copy="Base proves integrity after resolution; it does not store incident data or choose an action."/><div className="commitGrid"><div><b>01</b><span>Incident ID</span></div><div><b>02</b><span>Memory snapshot</span></div><div><b>03</b><span>Decision + policy</span></div><div><b>04</b><span>Final outcome</span></div></div><p>Commitments are Keccak-256 over versioned canonical UTF-8 JSON. The operator wallet calls <code>recordIncident</code> on Base Sepolia, chain <code>84532</code>. Verification requires success, the configured contract, the correct event, and four exact commitments. Anything else remains UNANCHORED.</p></section>

        <section id="api"><Title n="09" title="Public API" copy="Validated interfaces used by the dashboard, proof workflow, and external clients."/><div className="endpoints">{endpoints.map(([method,path,description])=><div key={path}><b className={method.toLowerCase()}>{method}</b><code>{path}</code><p>{description}</p></div>)}</div></section>

        <section id="functions"><Title n="10" title="Function reference" copy="Responsibilities of the principal implementation functions."/><div className="functions">{functions.map(([file,name,description])=><details key={`${file}-${name}`}><summary><code>{file}</code><b>{name}</b><span>+</span></summary><p>{description}</p></details>)}</div></section>

        <section id="hosting"><Title n="11" title="Hosting and persistence" copy="The runtime must respect Sibyl's local SQLite architecture."/><div className="twoCol"><div><h3>Immediate judge path</h3><p>Production Next.js + FastAPI + real Sibyl file through one Cloudflare HTTPS tunnel. Data survives browser and API restarts.</p></div><div><h3>Stable hosted path</h3><p>One FastAPI container and one persistent <code>/data</code> volume. Vercel may host the frontend, but its ephemeral function filesystem cannot host Sibyl safely.</p></div></div><p>Docker Compose and native reproduction remain supported. Railway configuration is included for a single persistent-volume backend; replicas remain disabled while one SQLite file is authoritative.</p></section>

        <section id="testing"><Title n="12" title="Testing and evaluation" copy="Correctness is exercised at storage, engine, API, browser-contract, and benchmark levels."/><ul className="testList"><li>Real Sibyl SDK with temporary SQLite databases</li><li>Separate-process Session A / Session B smoke proof</li><li>Concurrent judge isolation and duplicate-phase rejection</li><li>FORGET, irrelevant memory, quality updates, and supersession</li><li>Safety invariants and Base rejection paths</li><li>TypeScript, ESLint, Ruff, mypy, production build, and UI assertions</li><li>20-case MERCURY-MEM-20 generated benchmark</li></ul><div className="docActions"><Link href="/">RUN COMMAND CENTER</Link><a href="https://github.com/0xNexuz/mercury" target="_blank" rel="noreferrer">VIEW SOURCE ↗</a></div></section>
      </article>
    </div>
    <footer className="docsFooter"><span>MERCURY · PERSISTENT INCIDENT INTELLIGENCE</span><Link href="/">BACK TO COMMAND CENTER ↑</Link></footer>
  </main>;
}
