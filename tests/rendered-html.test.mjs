import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("MERCURY renders the load-bearing proof and real integration labels", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.match(page, /MEMORY CHANGED/);
  assert.match(page, /RUN SESSION A/);
  assert.match(page, /START FRESH SESSION B/);
  assert.match(page, /REAL · SIBYL PERSISTENCE/);
  assert.match(page, /SIMULATED · INCIDENT TELEMETRY/);
  assert.match(page, /BASE INCIDENT RECEIPT/);
});

test("hosted proof does not use browser persistence tricks", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(page, /localStorage|sessionStorage|document\.cookie/);
  assert.match(page, /\/api\/proof-runs/);
  assert.match(page, /VIEW PROOF/);
});

test("browser metadata uses the MERCURY icon and social card", async () => {
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  assert.match(layout, /favicon\.png/);
  assert.match(layout, /og\.png/);
  assert.match(layout, /Persistent Incident Intelligence/);
});
