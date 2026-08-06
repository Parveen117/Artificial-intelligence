#!/usr/bin/env python3
"""No-dependency local web interface for the Formal Proof Gate challenge."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from .verifier import tamper_one_step, verify_proof
except ImportError:
    from verifier import tamper_one_step, verify_proof

ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = ROOT / "fixtures"
MAX_REQUEST_BYTES = 1_000_000

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Break the Formal Proof Gate</title>
<style>
:root{font-family:Inter,system-ui,sans-serif;color-scheme:dark;background:#090b10;color:#f4f7fb}
body{margin:0;background:radial-gradient(circle at top,#182035,#090b10 55%);min-height:100vh}
main{max-width:1100px;margin:auto;padding:32px 18px 60px}
h1{font-size:clamp(2rem,6vw,4.4rem);line-height:.95;margin:.3em 0}.tag{color:#9fb6ff;font-weight:700}
p{color:#c3cad8;max-width:760px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:820px){.grid{grid-template-columns:1fr}}
.card{background:rgba(16,20,30,.92);border:1px solid #30384c;border-radius:18px;padding:18px;box-shadow:0 15px 60px #0008}
textarea,pre,select{width:100%;box-sizing:border-box;background:#080a0f;color:#e9eef9;border:1px solid #384158;border-radius:12px;padding:12px;font:13px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}
textarea{min-height:520px;resize:vertical}pre{min-height:520px;overflow:auto;white-space:pre-wrap}.row{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
button,select{width:auto;cursor:pointer}button{border:0;border-radius:999px;padding:11px 17px;font-weight:800;background:#d9e2ff;color:#11182a}button.secondary{background:#272f43;color:#eff3ff}button.danger{background:#ff6877;color:#21070a}
.status{font-size:1.2rem;font-weight:900;margin:8px 0}.valid{color:#77f2b0}.rejected{color:#ff8994}.muted{font-size:.9rem;color:#99a4b9}code{color:#b8c8ff}
</style>
</head>
<body><main>
<div class="tag">CLOSURE BEFORE COMMIT</div>
<h1>Break the<br>Formal Proof Gate</h1>
<p>Submit a proof in the declared finite grammar. A real break is an invalid derivation that receives <code>VALID_PROOF</code>. Strange prose or unsupported syntax correctly returns <code>PARSE_NOT_ADMITTED</code>.</p>
<div class="row"><select id="fixture"></select><button id="load" class="secondary">Load fixture</button><button id="verify">Verify proof</button><button id="tamper" class="danger">Tamper one step</button></div>
<div class="grid"><section class="card"><h2>Proof JSON</h2><textarea id="proof" spellcheck="false"></textarea></section><section class="card"><h2>Certificate</h2><div id="status" class="status muted">Not evaluated</div><pre id="result">Select a fixture and verify it.</pre></section></div>
</main>
<script>
const fixture=document.querySelector('#fixture'),proof=document.querySelector('#proof'),result=document.querySelector('#result'),statusEl=document.querySelector('#status');
async function request(path,body){const r=await fetch(path,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw new Error(j.error||r.statusText);return j}
async function loadFixtures(){const r=await fetch('/api/fixtures');const j=await r.json();fixture.innerHTML=j.fixtures.map(x=>`<option value="${x}">${x}</option>`).join('');await loadFixture()}
async function loadFixture(){const r=await fetch('/api/fixtures/'+encodeURIComponent(fixture.value));const j=await r.json();proof.value=JSON.stringify(j,null,2);statusEl.textContent='Loaded '+fixture.value;statusEl.className='status muted';result.textContent='Ready.'}
async function verify(){try{const cert=await request('/api/verify',JSON.parse(proof.value));render(cert)}catch(e){renderError(e)}}
async function tamper(){try{const out=await request('/api/tamper',JSON.parse(proof.value));proof.value=JSON.stringify(out.proof,null,2);render(out.certificate)}catch(e){renderError(e)}}
function render(cert){statusEl.textContent=cert.status;statusEl.className='status '+(cert.status==='VALID_PROOF'?'valid':'rejected');result.textContent=JSON.stringify(cert,null,2)}
function renderError(e){statusEl.textContent='REQUEST ERROR';statusEl.className='status rejected';result.textContent=String(e)}
document.querySelector('#load').onclick=loadFixture;document.querySelector('#verify').onclick=verify;document.querySelector('#tamper').onclick=tamper;loadFixtures();
</script></body></html>"""


class ChallengeHandler(BaseHTTPRequestHandler):
    server_version = "FormalProofGate/1.0"

    def _json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/fixtures":
            self._json({"fixtures": sorted(path.name for path in FIXTURE_DIR.glob("*.json"))})
            return
        prefix = "/api/fixtures/"
        if self.path.startswith(prefix):
            name = self.path[len(prefix):]
            path = FIXTURE_DIR / Path(name).name
            if not path.is_file() or path.suffix != ".json":
                self._json({"error": "fixture not found"}, HTTPStatus.NOT_FOUND)
                return
            self._json(json.loads(path.read_text(encoding="utf-8")))
            return
        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("request body size is invalid")
            raw = json.loads(self.rfile.read(length).decode("utf-8"))
            if self.path == "/api/verify":
                self._json(asdict(verify_proof(raw)))
                return
            if self.path == "/api/tamper":
                proof = tamper_one_step(raw)
                self._json({"proof": proof, "certificate": asdict(verify_proof(proof))})
                return
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[formal-proof-gate] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Formal Proof Gate challenge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ChallengeHandler)
    print(f"Formal Proof Gate running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
