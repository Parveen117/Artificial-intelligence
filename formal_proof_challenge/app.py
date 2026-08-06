#!/usr/bin/env python3
"""No-dependency hosted/local interface for the Formal Proof Gate challenge."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    from .anchor import build_external_anchor
    from .finality import FormalProofFinalityLedger, tamper_receipt, verify_receipt
    from .verifier import tamper_one_step, verify_proof
except ImportError:
    from anchor import build_external_anchor
    from finality import FormalProofFinalityLedger, tamper_receipt, verify_receipt
    from verifier import tamper_one_step, verify_proof

ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = ROOT / "fixtures"
OUTPUT_DIR = ROOT / "outputs"
MAX_REQUEST_BYTES = 1_000_000


def _flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_ledger_path() -> Path:
    configured = os.getenv("FPG_LEDGER_PATH")
    if configured:
        return Path(configured)
    data_dir = Path("/data")
    if _flag("FPG_PUBLIC_MODE") and data_dir.is_dir() and os.access(data_dir, os.W_OK):
        return data_dir / "formal_proof_public_receipts.jsonl"
    return OUTPUT_DIR / "formal_proof_public_receipts.jsonl"


LEDGER_PATH = _default_ledger_path()
PUBLIC_MODE = _flag("FPG_PUBLIC_MODE")
ALLOW_SEAL = _flag("FPG_ALLOW_SEAL", True)
MAX_LEDGER_ENTRIES = max(1, int(os.getenv("FPG_MAX_LEDGER_ENTRIES", "10000")))
PUBLIC_APP_URL = os.getenv("FPG_PUBLIC_APP_URL", "").rstrip("/")
PUBLIC_ANCHOR_URL = os.getenv("FPG_PUBLIC_ANCHOR_URL", "").rstrip("/")
RED_TEAM_URL = os.getenv(
    "FPG_RED_TEAM_URL",
    "https://github.com/Parveen117/Artificial-intelligence/issues/new?template=formal-proof-gate-break.yml",
)
SOURCE_REVISION = os.getenv("FPG_SOURCE_REVISION", "")
PERSISTENCE_MODE = os.getenv(
    "FPG_PERSISTENCE_MODE",
    "persistent-volume" if str(LEDGER_PATH).startswith("/data/") else "local-or-ephemeral",
)

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Break the Formal Proof Gate</title>
<style>
:root{font-family:Inter,system-ui,sans-serif;color-scheme:dark;background:#090b10;color:#f4f7fb}
body{margin:0;background:radial-gradient(circle at top,#182035,#090b10 55%);min-height:100vh}
main{max-width:1180px;margin:auto;padding:32px 18px 60px}
h1{font-size:clamp(2rem,6vw,4.4rem);line-height:.95;margin:.3em 0}.tag{color:#9fb6ff;font-weight:700}
p{color:#c3cad8;max-width:900px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:820px){.grid{grid-template-columns:1fr}}
.card{background:rgba(16,20,30,.92);border:1px solid #30384c;border-radius:18px;padding:18px;box-shadow:0 15px 60px #0008}
textarea,pre,select{width:100%;box-sizing:border-box;background:#080a0f;color:#e9eef9;border:1px solid #384158;border-radius:12px;padding:12px;font:13px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}
textarea{min-height:560px;resize:vertical}pre{min-height:560px;overflow:auto;white-space:pre-wrap}.row{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0;align-items:center}
button,select{width:auto;cursor:pointer}button,a.pill{border:0;border-radius:999px;padding:11px 17px;font-weight:800;background:#d9e2ff;color:#11182a;text-decoration:none}button.secondary,a.secondary{background:#272f43;color:#eff3ff}button.danger{background:#ff6877;color:#21070a}button.commit{background:#77f2b0;color:#062114}
.status{font-size:1.2rem;font-weight:900;margin:8px 0}.valid{color:#77f2b0}.rejected{color:#ff8994}.muted{font-size:.9rem;color:#99a4b9}code{color:#b8c8ff}.badge{padding:9px 13px;border:1px solid #30384c;border-radius:999px;color:#aab5cb}.hash{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
</style>
</head>
<body><main>
<div class="tag">CLOSURE BEFORE COMMIT · PUBLIC RED TEAM</div>
<h1>Break the<br>Formal Proof Gate</h1>
<p>Submit a proof in the declared finite grammar. A real break is an invalid derivation that receives <code>VALID_PROOF</code>. Seal a result to receive an ECL decision, IEL audit transition, and SHA-256 tamper/replay receipt. The public anchor separately checkpoints the ledger head.</p>
<div class="row"><span id="ledger" class="badge">Ledger loading…</span><span id="anchor" class="badge hash">Anchor loading…</span><span id="mode" class="badge">Mode loading…</span></div>
<div class="row"><a id="submitBreak" class="pill secondary" target="_blank" rel="noopener">Submit a reproducible break</a><a id="anchorPage" class="pill secondary" target="_blank" rel="noopener" hidden>View external anchor</a></div>
<div class="row">
<select id="fixture"></select><button id="load" class="secondary">Load fixture</button><button id="verify">Verify proof</button><button id="tamper" class="danger">Tamper proof</button><button id="seal" class="commit">Seal public receipt</button>
</div>
<div class="row"><button id="verifyReceipt" class="secondary">Verify receipt</button><button id="tamperReceipt" class="danger">Tamper receipt</button><button id="download" class="secondary">Download receipt</button></div>
<div class="grid"><section class="card"><h2>Proof JSON</h2><textarea id="proof" spellcheck="false"></textarea></section><section class="card"><h2>Certificate / Receipt</h2><div id="status" class="status muted">Not evaluated</div><pre id="result">Select a fixture and verify it.</pre></section></div>
</main>
<script>
const fixture=document.querySelector('#fixture'),proof=document.querySelector('#proof'),result=document.querySelector('#result'),statusEl=document.querySelector('#status'),ledgerEl=document.querySelector('#ledger'),anchorEl=document.querySelector('#anchor'),modeEl=document.querySelector('#mode'),submitBreak=document.querySelector('#submitBreak'),anchorPage=document.querySelector('#anchorPage');
let currentReceipt=null;
async function request(path,body){const r=await fetch(path,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw new Error(j.error||r.statusText);return j}
async function refreshMeta(){const [ledgerR,anchorR,configR]=await Promise.all([fetch('/api/ledger'),fetch('/api/anchor'),fetch('/api/config')]);const ledger=await ledgerR.json(),anchor=await anchorR.json(),config=await configR.json();ledgerEl.textContent=`Ledger: ${ledger.checked||0} entries · ${ledger.status}`;anchorEl.textContent=`Anchor: ${(anchor.anchor_hash||'').slice(0,16)}… · ${anchor.anchor?.receipt_count||0} receipts`;modeEl.textContent=`${config.public_mode?'public':'local'} · ${config.persistence_mode}`;submitBreak.href=config.red_team_url;if(config.anchor_page_url){anchorPage.href=config.anchor_page_url;anchorPage.hidden=false}document.querySelector('#seal').disabled=!config.allow_seal}
async function loadFixtures(){const r=await fetch('/api/fixtures');const j=await r.json();fixture.innerHTML=j.fixtures.map(x=>`<option value="${x}">${x}</option>`).join('');await loadFixture();await refreshMeta()}
async function loadFixture(){const r=await fetch('/api/fixtures/'+encodeURIComponent(fixture.value));const j=await r.json();proof.value=JSON.stringify(j,null,2);currentReceipt=null;statusEl.textContent='Loaded '+fixture.value;statusEl.className='status muted';result.textContent='Ready.'}
async function verify(){try{const cert=await request('/api/verify',JSON.parse(proof.value));currentReceipt=null;render(cert,cert.status)}catch(e){renderError(e)}}
async function tamper(){try{const out=await request('/api/tamper',JSON.parse(proof.value));proof.value=JSON.stringify(out.proof,null,2);currentReceipt=null;render(out.certificate,out.certificate.status)}catch(e){renderError(e)}}
async function seal(){try{const out=await request('/api/seal',JSON.parse(proof.value));if(out.receipt)currentReceipt=out.receipt;const label=out.action?`${out.status} · ${out.action}`:out.status;render(out,label);await refreshMeta()}catch(e){renderError(e)}}
async function verifyReceipt(){try{if(!currentReceipt)throw new Error('Seal a receipt first');const out=await request('/api/verify-receipt',currentReceipt);render(out,out.status)}catch(e){renderError(e)}}
async function tamperReceipt(){try{if(!currentReceipt)throw new Error('Seal a receipt first');const out=await request('/api/tamper-receipt',currentReceipt);currentReceipt=out.receipt;render(out,out.verification.status)}catch(e){renderError(e)}}
function downloadReceipt(){if(!currentReceipt){renderError(new Error('Seal a receipt first'));return}const blob=new Blob([JSON.stringify(currentReceipt,null,2)+'\n'],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(currentReceipt.proof_certificate?.proof_id||'formal-proof')+'-receipt.json';a.click();URL.revokeObjectURL(a.href)}
function render(payload,label){statusEl.textContent=label;const good=['VALID_PROOF','VALID_RECEIPT','SEALED','COMMIT'].some(x=>String(label).includes(x))&&!String(label).includes('REJECT');statusEl.className='status '+(good?'valid':'rejected');result.textContent=JSON.stringify(payload,null,2)}
function renderError(e){statusEl.textContent='REQUEST ERROR';statusEl.className='status rejected';result.textContent=String(e)}
document.querySelector('#load').onclick=loadFixture;document.querySelector('#verify').onclick=verify;document.querySelector('#tamper').onclick=tamper;document.querySelector('#seal').onclick=seal;document.querySelector('#verifyReceipt').onclick=verifyReceipt;document.querySelector('#tamperReceipt').onclick=tamperReceipt;document.querySelector('#download').onclick=downloadReceipt;loadFixtures();
</script></body></html>"""


def _public_payload(value: Any) -> Any:
    """Remove local filesystem details from hosted responses."""
    if not PUBLIC_MODE:
        return value
    if isinstance(value, dict):
        return {key: _public_payload(item) for key, item in value.items() if key != "ledger_path"}
    if isinstance(value, list):
        return [_public_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_public_payload(item) for item in value]
    return value


class ChallengeHandler(BaseHTTPRequestHandler):
    server_version = "FormalProofGate/3.0"

    def _headers(self, content_type: str, length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cache-Control", "no-store")

    def _json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(_public_payload(payload), indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self._headers("application/json; charset=utf-8", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._headers("text/html; charset=utf-8", len(body))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/healthz":
            audit = FormalProofFinalityLedger(LEDGER_PATH).verify()
            self._json({
                "ok": audit.ok,
                "service": "FormalProofGate",
                "version": self.server_version,
                "ledger_status": audit.status,
                "receipt_count": audit.checked,
                "public_mode": PUBLIC_MODE,
                "allow_seal": ALLOW_SEAL,
            }, HTTPStatus.OK if audit.ok else HTTPStatus.SERVICE_UNAVAILABLE)
            return
        if path == "/api/config":
            self._json({
                "public_mode": PUBLIC_MODE,
                "allow_seal": ALLOW_SEAL,
                "max_ledger_entries": MAX_LEDGER_ENTRIES,
                "persistence_mode": PERSISTENCE_MODE,
                "public_app_url": PUBLIC_APP_URL,
                "anchor_page_url": PUBLIC_ANCHOR_URL,
                "red_team_url": RED_TEAM_URL,
                "source_revision": SOURCE_REVISION,
            })
            return
        if path == "/api/fixtures":
            self._json({"fixtures": sorted(item.name for item in FIXTURE_DIR.glob("*.json"))})
            return
        if path == "/api/ledger":
            self._json(asdict(FormalProofFinalityLedger(LEDGER_PATH).verify()))
            return
        if path == "/api/anchor":
            try:
                self._json(build_external_anchor(LEDGER_PATH, public_app_url=PUBLIC_APP_URL, source_revision=SOURCE_REVISION))
            except ValueError as exc:
                self._json({"error": str(exc)}, HTTPStatus.CONFLICT)
            return
        if path == "/api/stats":
            try:
                anchor = build_external_anchor(LEDGER_PATH, public_app_url=PUBLIC_APP_URL, source_revision=SOURCE_REVISION)
                payload = anchor["anchor"]
                self._json({
                    "receipt_count": payload["receipt_count"],
                    "action_counts": payload["action_counts"],
                    "last_entry_hash": payload["last_entry_hash"],
                    "anchor_hash": anchor["anchor_hash"],
                    "final_state": payload["final_state"],
                })
            except ValueError as exc:
                self._json({"error": str(exc)}, HTTPStatus.CONFLICT)
            return
        prefix = "/api/fixtures/"
        if path.startswith(prefix):
            name = path[len(prefix):]
            fixture_path = FIXTURE_DIR / Path(name).name
            if not fixture_path.is_file() or fixture_path.suffix != ".json":
                self._json({"error": "fixture not found"}, HTTPStatus.NOT_FOUND)
                return
            self._json(json.loads(fixture_path.read_text(encoding="utf-8")))
            return
        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("request body size is invalid")
            raw = json.loads(self.rfile.read(length).decode("utf-8"))
            if path == "/api/verify":
                self._json(asdict(verify_proof(raw)))
                return
            if path == "/api/tamper":
                proof_value = tamper_one_step(raw)
                self._json({"proof": proof_value, "certificate": asdict(verify_proof(proof_value))})
                return
            if path == "/api/seal":
                if not ALLOW_SEAL:
                    self._json({"error": "receipt sealing is disabled for this deployment"}, HTTPStatus.FORBIDDEN)
                    return
                ledger = FormalProofFinalityLedger(LEDGER_PATH)
                audit = ledger.verify()
                if not audit.ok:
                    self._json({"error": "ledger is not valid", "ledger": asdict(audit)}, HTTPStatus.CONFLICT)
                    return
                if audit.checked >= MAX_LEDGER_ENTRIES:
                    self._json({"error": "public ledger entry limit reached"}, HTTPStatus.SERVICE_UNAVAILABLE)
                    return
                self._json(ledger.seal_proof(raw))
                return
            if path == "/api/verify-receipt":
                self._json(asdict(verify_receipt(raw)))
                return
            if path == "/api/tamper-receipt":
                receipt = tamper_receipt(raw)
                self._json({"receipt": receipt, "verification": asdict(verify_receipt(receipt))})
                return
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[formal-proof-gate] {self.address_string()} {fmt % args}")


def main() -> None:
    global LEDGER_PATH, PUBLIC_MODE, ALLOW_SEAL, MAX_LEDGER_ENTRIES
    global PUBLIC_APP_URL, PUBLIC_ANCHOR_URL, RED_TEAM_URL, SOURCE_REVISION, PERSISTENCE_MODE

    hosted_default = bool(os.getenv("SPACE_ID") or _flag("FPG_PUBLIC_MODE"))
    default_host = os.getenv("FPG_HOST", "0.0.0.0" if hosted_default else "127.0.0.1")
    default_port = int(os.getenv("PORT", os.getenv("FPG_PORT", "7860" if hosted_default else "8081")))

    parser = argparse.ArgumentParser(description="Run the Formal Proof Gate challenge")
    parser.add_argument("--host", default=default_host)
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument("--public", action="store_true", default=PUBLIC_MODE)
    parser.add_argument("--read-only", action="store_true", default=not ALLOW_SEAL)
    parser.add_argument("--max-ledger-entries", type=int, default=MAX_LEDGER_ENTRIES)
    parser.add_argument("--app-url", default=PUBLIC_APP_URL)
    parser.add_argument("--anchor-url", default=PUBLIC_ANCHOR_URL)
    parser.add_argument("--red-team-url", default=RED_TEAM_URL)
    parser.add_argument("--source-revision", default=SOURCE_REVISION)
    parser.add_argument("--persistence-mode", default=PERSISTENCE_MODE)
    args = parser.parse_args()

    LEDGER_PATH = args.ledger
    PUBLIC_MODE = bool(args.public)
    ALLOW_SEAL = not bool(args.read_only)
    MAX_LEDGER_ENTRIES = max(1, args.max_ledger_entries)
    PUBLIC_APP_URL = args.app_url.rstrip("/")
    PUBLIC_ANCHOR_URL = args.anchor_url.rstrip("/")
    RED_TEAM_URL = args.red_team_url
    SOURCE_REVISION = args.source_revision
    PERSISTENCE_MODE = args.persistence_mode

    server = ThreadingHTTPServer((args.host, args.port), ChallengeHandler)
    print(f"Formal Proof Gate running at http://{args.host}:{args.port}")
    print(f"Receipt ledger: {LEDGER_PATH}")
    print(f"Public mode: {PUBLIC_MODE}; sealing: {ALLOW_SEAL}; persistence: {PERSISTENCE_MODE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
