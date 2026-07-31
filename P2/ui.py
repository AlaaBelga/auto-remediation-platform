import json
from pathlib import Path


BASE = Path(__file__).resolve().parent


def _load_example(name: str) -> dict:
    return json.loads((BASE / "examples" / name).read_text())


def render_dashboard_html() -> str:
    valid_sample = json.dumps(_load_example("event_valid.json"), indent=2)
    invalid_sample = json.dumps(_load_example("event_invalid.json"), indent=2)

    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Console P2 d'auto-remediation</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Source+Code+Pro:wght@400;600&display=swap');

    :root {{
      --bg: #07111f;
      --bg-2: #0c1b2f;
      --card: rgba(12, 27, 47, 0.82);
      --card-strong: #10233d;
      --line: rgba(180, 206, 255, 0.14);
      --text: #eaf2ff;
      --muted: #9bb0d1;
      --accent: #7ee2c1;
      --accent-2: #6aa9ff;
      --warning: #ffd166;
      --danger: #ff6b7a;
      --shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(110, 168, 255, 0.22), transparent 35%),
        radial-gradient(circle at 85% 15%, rgba(126, 226, 193, 0.16), transparent 28%),
        radial-gradient(circle at 70% 75%, rgba(255, 107, 122, 0.12), transparent 25%),
        linear-gradient(160deg, var(--bg), var(--bg-2));
      color: var(--text);
      font-family: 'Manrope', sans-serif;
    }}

    .noise {{
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.06;
      background-image:
        linear-gradient(rgba(255,255,255,0.18) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.18) 1px, transparent 1px);
      background-size: 32px 32px;
      mask-image: linear-gradient(to bottom, rgba(0,0,0,.85), transparent 92%);
    }}

    .shell {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 36px 24px 40px;
    }}

    .hero {{
      display: grid;
      grid-template-columns: 1.5fr 0.9fr;
      gap: 20px;
      margin-bottom: 20px;
      align-items: stretch;
    }}

    .panel {{
      background: var(--card);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
      border-radius: 24px;
    }}

    .headline {{
      padding: 30px;
      position: relative;
      overflow: hidden;
    }}

    .headline::after {{
      content: '';
      position: absolute;
      inset: auto -80px -120px auto;
      width: 300px;
      height: 300px;
      background: radial-gradient(circle, rgba(126,226,193,.3), transparent 60%);
      pointer-events: none;
    }}

    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 14px;
      border-radius: 999px;
      background: rgba(126, 226, 193, 0.1);
      color: var(--accent);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 18px 0 14px;
      font-size: clamp(2.4rem, 4vw, 4.7rem);
      line-height: 0.98;
      letter-spacing: -0.05em;
      max-width: 12ch;
    }}

    .lead {{
      margin: 0;
      max-width: 64ch;
      color: var(--muted);
      font-size: 1.02rem;
      line-height: 1.7;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-top: 22px;
    }}

    .stat {{
      padding: 16px;
      border-radius: 18px;
      background: rgba(16, 35, 61, 0.65);
      border: 1px solid rgba(180, 206, 255, 0.1);
    }}

    .stat strong {{
      display: block;
      font-size: 1.2rem;
      margin-bottom: 6px;
    }}

    .stat span {{
      color: var(--muted);
      font-size: 0.9rem;
    }}

    .side-card {{
      padding: 22px;
      display: grid;
      gap: 16px;
    }}

    .meter {{
      border-radius: 20px;
      background: linear-gradient(180deg, rgba(16,35,61,0.92), rgba(8,18,31,0.78));
      border: 1px solid var(--line);
      padding: 18px;
    }}

    .meter-label {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 10px;
      color: var(--muted);
      font-size: 0.9rem;
    }}

    .bar {{
      height: 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.08);
      overflow: hidden;
    }}

    .bar > div {{
      width: 74%;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      box-shadow: 0 0 18px rgba(126, 226, 193, 0.45);
    }}

    .layout {{
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 20px;
    }}

    .composer, .result {{
      padding: 22px;
    }}

    .section-title {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }}

    .section-title h2 {{
      margin: 0;
      font-size: 1.05rem;
      letter-spacing: 0.02em;
    }}

    .section-title p {{
      margin: 0;
      color: var(--muted);
      font-size: 0.9rem;
    }}

    .pills {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}

    .pill, button.pill {{
      appearance: none;
      border: 1px solid rgba(180, 206, 255, 0.15);
      background: rgba(255,255,255,0.04);
      color: var(--text);
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
      cursor: pointer;
      transition: transform .18s ease, border-color .18s ease, background .18s ease;
    }}

    .pill:hover {{ transform: translateY(-1px); border-color: rgba(126,226,193,0.45); }}

    textarea {{
      width: 100%;
      min-height: 460px;
      resize: vertical;
      background: #081627;
      color: #eaf2ff;
      border: 1px solid rgba(180,206,255,0.12);
      border-radius: 20px;
      padding: 18px;
      font-family: 'Source Code Pro', monospace;
      font-size: 0.88rem;
      line-height: 1.6;
      outline: none;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
    }}

    input[type="password"] {{
      width: 100%;
      background: #081627;
      color: #eaf2ff;
      border: 1px solid rgba(180,206,255,0.12);
      border-radius: 14px;
      padding: 12px 14px;
      font-family: 'Manrope', sans-serif;
      font-size: 0.92rem;
      outline: none;
      margin-bottom: 14px;
    }}

    input[type="password"]:focus {{
      border-color: rgba(126,226,193,0.55);
      box-shadow: 0 0 0 4px rgba(126,226,193,0.08);
    }}

    textarea:focus {{
      border-color: rgba(126,226,193,0.55);
      box-shadow: 0 0 0 4px rgba(126,226,193,0.08);
    }}

    .actions {{
      display: flex;
      gap: 12px;
      margin-top: 14px;
      flex-wrap: wrap;
    }}

    .primary {{
      background: linear-gradient(90deg, #7ee2c1, #6aa9ff);
      color: #07111f;
      border: 0;
      font-weight: 800;
      padding: 12px 18px;
      border-radius: 14px;
      cursor: pointer;
    }}

    .ghost {{
      background: rgba(255,255,255,0.06);
      color: var(--text);
      border: 1px solid rgba(180,206,255,0.14);
      font-weight: 700;
      padding: 12px 18px;
      border-radius: 14px;
      cursor: pointer;
    }}

    .result-box {{
      min-height: 320px;
      border-radius: 20px;
      background: linear-gradient(180deg, rgba(8,22,39,0.92), rgba(4,10,18,0.88));
      border: 1px solid rgba(180,206,255,0.12);
      padding: 18px;
      white-space: pre-wrap;
      font-family: 'Source Code Pro', monospace;
      font-size: 0.86rem;
      line-height: 1.6;
      overflow: auto;
    }}

    .result-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 800;
      letter-spacing: 0.03em;
      background: rgba(126, 226, 193, 0.1);
      color: var(--accent);
      border: 1px solid rgba(126,226,193,0.22);
    }}

    .badge.warn {{ color: var(--warning); background: rgba(255, 209, 102, 0.1); border-color: rgba(255,209,102,0.22); }}
    .badge.danger {{ color: var(--danger); background: rgba(255, 107, 122, 0.1); border-color: rgba(255,107,122,0.22); }}

    .footnote {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.88rem;
    }}

    @media (max-width: 1080px) {{
      .hero, .layout {{ grid-template-columns: 1fr; }}
      .stats {{ grid-template-columns: 1fr; }}
      textarea {{ min-height: 340px; }}
    }}
  </style>
</head>
<body>
  <div class="noise"></div>
  <main class="shell">
    <section class="hero">
      <div class="panel headline">
        <div class="eyebrow">Console P2 d'auto-remediation</div>
        <h1>Pilotage operationnel des evenements de risque emis par le Pilier 1.</h1>
        <p class="lead">
          Collez un evenement, validez-le avec le contrat strict, puis declenchez une simulation de remediation lorsque la decision demande une auto-remediation.
          L'interface sert de cockpit incident compact : une entree, une decision, un resultat visible.
        </p>
        <div class="stats">
          <div class="stat"><strong>Schema strict</strong><span>Validation des evenements par JSON Schema v1.</span></div>
          <div class="stat"><strong>Retour rapide</strong><span>Validation et reponse de remediation immediates.</span></div>
          <div class="stat"><strong>Execution maitrisee</strong><span>Runtime distroless non privilegie avec verifications de sante.</span></div>
        </div>
      </div>

      <aside class="panel side-card">
        <div class="meter">
          <div class="meter-label"><span>Preparation auto-remediation</span><span>74%</span></div>
          <div class="bar"><div></div></div>
        </div>
        <div class="meter">
          <div class="meter-label"><span>Couverture du contrat</span><span>100%</span></div>
          <div class="bar"><div style="width:100%"></div></div>
        </div>
        <div class="meter">
          <div class="meter-label"><span>Posture d'execution</span><span>nonroot</span></div>
          <div class="bar"><div style="width:88%"></div></div>
        </div>
        <p class="footnote">Astuce : utilisez les boutons d'exemple pour passer d'un incident valide a une charge invalide.</p>
      </aside>
    </section>

    <section class="layout">
      <div class="panel composer">
        <div class="section-title">
          <div>
            <h2>Evenement entrant</h2>
            <p>Soumettre un evenement de risque machine directement a l'API.</p>
          </div>
          <span class="badge">/events</span>
        </div>

        <div class="pills">
          <button class="pill" data-sample="valid">Charger exemple valide</button>
          <button class="pill" data-sample="invalid">Charger exemple invalide</button>
          <button class="pill" data-sample="clean">Reinitialiser</button>
        </div>

        <input id="apiKey" type="password" autocomplete="off" placeholder="Cle API optionnelle pour X-API-Key" />
        <textarea id="payload" spellcheck="false">{valid_sample}</textarea>

        <div class="actions">
          <button class="primary" id="submitBtn">Valider et executer</button>
          <button class="ghost" id="prettyBtn">Formater JSON</button>
        </div>
      </div>

      <div class="panel result">
        <div class="result-header">
          <div>
            <h2>Resultat</h2>
            <p>Reponse en direct de l'API d'auto-remediation.</p>
          </div>
          <span class="badge warn" id="statusBadge">En attente</span>
        </div>
        <div class="result-box" id="resultBox">Soumettez un evenement pour afficher ici la validation et la sortie d'action.</div>
        <div class="footnote">Point d'entree de sante : <code>/health</code>. Si la decision vaut <code>trigger_self_healing</code>, le panneau affiche le resultat du playbook simule.</div>
      </div>
    </section>
  </main>

  <script>
    const samples = {{
      valid: `{valid_sample}`,
      invalid: `{invalid_sample}`,
      clean: `{{
  "event_id": "evt-20260518-0002",
  "event_type": "machine_risk_assessed",
  "timestamp": "2026-05-18T10:20:00Z",
  "source": "pilier_1",
  "correlation_id": "corr-new-001",
  "machine_id": "unit_07",
  "prediction": 0,
  "risk_score": 0.2,
  "decision": "observe",
  "schema_version": "1.0"
}}`
    }};

    const payload = document.getElementById('payload');
    const apiKey = document.getElementById('apiKey');
    const resultBox = document.getElementById('resultBox');
    const statusBadge = document.getElementById('statusBadge');
    const submitBtn = document.getElementById('submitBtn');
    const prettyBtn = document.getElementById('prettyBtn');

    function setBadge(kind, text) {{
      statusBadge.className = 'badge ' + (kind || '');
      statusBadge.textContent = text;
    }}

    function showResult(title, body, kind) {{
      setBadge(kind, title);
      resultBox.textContent = body;
    }}

    document.querySelectorAll('[data-sample]').forEach((button) => {{
      button.addEventListener('click', () => {{
        payload.value = samples[button.dataset.sample];
        setBadge('warn', button.dataset.sample === 'valid' ? 'Exemple charge' : button.dataset.sample === 'invalid' ? 'Exemple invalide' : 'Reinitialise');
        resultBox.textContent = 'Exemple charge. Verifiez le JSON puis soumettez-le quand il est pret.';
      }});
    }});

    prettyBtn.addEventListener('click', () => {{
      try {{
        payload.value = JSON.stringify(JSON.parse(payload.value), null, 2);
        setBadge('', 'Formate');
      }} catch (error) {{
        showResult('Erreur de format', String(error), 'danger');
      }}
    }});

    submitBtn.addEventListener('click', async () => {{
      try {{
        const data = JSON.parse(payload.value);
        setBadge('', 'Validation...');
        resultBox.textContent = 'Envoi de l\\'evenement vers /events ...';

        const headers = {{ 'Content-Type': 'application/json' }};
        if (apiKey.value.trim()) {{
          headers['X-API-Key'] = apiKey.value.trim();
        }}

        const response = await fetch('/events', {{
          method: 'POST',
          headers,
          body: JSON.stringify(data),
        }});

        const contentType = response.headers.get('content-type') || '';
        const body = contentType.includes('application/json') ? await response.json() : await response.text();

        if (!response.ok) {{
          showResult('Rejete', JSON.stringify(body, null, 2), 'danger');
          return;
        }}

        const summary = JSON.stringify(body, null, 2);
        const kind = body.status === 'action_triggered' ? 'warn' : '';
        showResult('Accepte', summary, kind);
      }} catch (error) {{
        showResult('Erreur client', String(error), 'danger');
      }}
    }});
  </script>
</body>
</html>"""
