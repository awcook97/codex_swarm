from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from swarm.agents.base import AgentContext, BaseAgent


class CoderAgent(BaseAgent):
    def __init__(self, instructions: str | None = None) -> None:
        super().__init__(
            name="coder",
            role="Coder",
            instructions=instructions or "Create artifacts or code changes based on tasks.",
        )

    async def run(self, task: str, context: AgentContext) -> dict[str, Any]:
        self.log(context, f"Coding task: {task}")
        research = context.short_term.get(context.run_id, "researcher", "research") or ""
        deliverable = context.short_term.get(context.run_id, "researcher", "deliverable")
        needs = context.short_term.get(context.run_id, "researcher", "needs") or []
        handoff = _read_json(context, context.output_dir / "handoff.json")
        plan_payload = _read_json(context, context.output_dir / "plan.json")
        plan_text = _read_text(context, context.output_dir / "plan.json")
        if handoff:
            research = handoff.get("summary") or research
            deliverable = handoff.get("deliverable") or deliverable
            needs = handoff.get("needs") or needs
        if plan_payload:
            deliverable = plan_payload.get("deliverable") or deliverable
            project_type = plan_payload.get("project_type")
            artifacts = plan_payload.get("artifacts") or []
        else:
            project_type = None
            artifacts = []
        if deliverable is None:
            prompt = "\n".join(
                [
                    "ROLE: Coder",
                    "Return JSON with fields: deliverable, subject, project_type.",
                    f"Objective: {context.objective}",
                    f"Research: {research}",
                    f"Plan: {plan_text}",
                ]
            )
            response_text = await self.complete(context, prompt)
            try:
                payload = json.loads(response_text)
                deliverable = payload.get("deliverable")
                subject = payload.get("subject") or context.objective
                project_type = payload.get("project_type")
            except json.JSONDecodeError:
                deliverable = None
                subject = context.objective
                project_type = project_type
        else:
            subject = context.objective
            project_type = project_type

        deliverable = deliverable or _determine_deliverable(research)
        landing_spec = None
        if _is_landing_page(deliverable, project_type):
            landing_spec = await _landing_page_spec(self, context, context.objective, task, research)
        files = _build_project_files(
            context.objective,
            task,
            research,
            deliverable,
            subject=subject,
            project_type=project_type,
            landing_spec=landing_spec,
        )
        artifact_dir = context.output_dir
        if not context.dry_run:
            for name, file_content in files.items():
                output_path = artifact_dir / name
                if isinstance(file_content, bytes):
                    context.filesystem.write_bytes(output_path, file_content)
                else:
                    context.filesystem.write_text(output_path, file_content)
            created_at = datetime.now(timezone.utc).isoformat()
            context.persistent.put_artifact(
                context.run_id,
                name="project",
                path=str(artifact_dir),
                created_at=created_at,
            )
        else:
            files = {
                name: (file_content if isinstance(file_content, bytes) else f"[dry-run]\n{file_content}")
                for name, file_content in files.items()
            }
        context.short_term.put(context.run_id, self.name, "artifact", str(artifact_dir))
        summary = "\n".join([f"{name}" for name in files.keys()])
        manifest_path = context.output_dir / "artifact_manifest.json"
        if not context.dry_run:
            context.filesystem.write_text(
                manifest_path,
                json.dumps(
                    {
                        "deliverable": deliverable,
                        "project_type": project_type,
                        "requested_artifacts": artifacts,
                        "produced_files": list(files.keys()),
                        "needs": needs,
                    },
                    indent=2,
                ),
            )
        return {
            "artifact": str(artifact_dir),
            "files": list(files.keys()),
            "content": summary,
            "needs": needs,
            "deliverable": deliverable,
            "manifest": str(manifest_path),
        }


def _build_project_files(
    objective: str,
    task: str,
    research: str,
    deliverable: str,
    subject: str,
    project_type: str | None,
    landing_spec: dict[str, Any] | None = None,
) -> dict[str, str | bytes]:
    if deliverable == "gif" or project_type == "animation":
        return _animation_project(objective, task, research, subject)
    if deliverable == "python" or project_type == "python":
        return _python_game_project(objective, task, research)
    if deliverable == "image_edit" or project_type == "image_edit":
        return _image_edit_project(objective, task, research)
    return _landing_page_project(objective, task, research, landing_spec)


def _is_landing_page(deliverable: str | None, project_type: str | None) -> bool:
    if project_type in {"animation", "python", "image_edit"}:
        return False
    if deliverable in {"gif", "python", "image_edit"}:
        return False
    return True


async def _landing_page_spec(
    agent: BaseAgent,
    context: AgentContext,
    objective: str,
    task: str,
    research: str,
) -> dict[str, Any]:
    if context.dry_run:
        return {}
    prompt = "\n".join(
        [
            "ROLE: Coder",
            "Return strict JSON only. No markdown.",
            "Use ASCII characters only.",
            "Create copy for a single-page landing page.",
            "Fields: name, eyebrow, tagline, cta_primary, cta_secondary, hours, location, footer_note.",
            "highlights: array of 3 objects with title, body.",
            "events: array of 3 objects with date, title, detail.",
            "membership: object with title, body, cta.",
            "shelf: array of 3 objects with title, subtitle.",
            f"Objective: {objective}",
            f"Task: {task}",
            f"Research: {research}",
        ]
    )
    response_text = await agent.complete(context, prompt)
    payload = _extract_json(response_text)
    return payload if isinstance(payload, dict) else {}


def _landing_page_project(
    objective: str, task: str, research: str, landing_spec: dict[str, Any] | None
) -> dict[str, str]:
    resolved = _normalize_landing_spec(objective, landing_spec)
    name = _escape(resolved["name"])
    eyebrow = _escape(resolved["eyebrow"])
    tagline = _escape(resolved["tagline"])
    cta_primary = _escape(resolved["cta_primary"])
    cta_secondary = _escape(resolved["cta_secondary"])
    hours = _escape(resolved["hours"])
    location = _escape(resolved["location"])
    footer_note = _escape(resolved["footer_note"])
    membership = resolved["membership"]
    membership_title = _escape(membership["title"])
    membership_body = _escape(membership["body"])
    membership_cta = _escape(membership["cta"])
    highlights = resolved["highlights"]
    events = resolved["events"]
    shelf = resolved["shelf"]
    is_bookish = any(word in objective.lower() for word in ["book", "bookstore", "library"])
    highlights_eyebrow = "Inside the shop" if is_bookish else "Inside the studio"
    highlights_title = "Find your next favorite" if is_bookish else "Build a focused experience"
    events_eyebrow = "Events" if is_bookish else "Calendar"
    events_title = "This week's gatherings" if is_bookish else "Upcoming moments"
    badge_text = "Curated weekly" if is_bookish else "Fresh releases"

    shelf_cards = "\n".join(
        "\n".join(
            [
                f"            <div class=\"book book-{index}\">",
                f"              <span class=\"book-title\">{_escape(item['title'])}</span>",
                f"              <span class=\"book-subtitle\">{_escape(item['subtitle'])}</span>",
                "            </div>",
            ]
        )
        for index, item in enumerate(shelf, start=1)
    )

    highlight_cards = "\n".join(
        "\n".join(
            [
                "        <article class=\"card reveal\">",
                f"          <h3>{_escape(item['title'])}</h3>",
                f"          <p>{_escape(item['body'])}</p>",
                "        </article>",
            ]
        )
        for item in highlights
    )

    event_rows = "\n".join(
        "\n".join(
            [
                "        <div class=\"event reveal\">",
                f"          <div class=\"event-date\">{_escape(item['date'])}</div>",
                "          <div class=\"event-info\">",
                f"            <h3>{_escape(item['title'])}</h3>",
                f"            <p>{_escape(item['detail'])}</p>",
                "          </div>",
                "        </div>",
            ]
        )
        for item in events
    )

    return {
        "index.html": f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{name}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Space+Grotesk:wght@400;500;600&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <div class="background">
      <span class="orb orb-one"></span>
      <span class="orb orb-two"></span>
      <span class="orb orb-three"></span>
    </div>
    <main class="page">
      <header class="hero">
        <div class="hero-text">
          <p class="eyebrow reveal">{eyebrow}</p>
          <h1 class="reveal">{name}</h1>
          <p class="tagline reveal">{tagline}</p>
          <div class="actions reveal">
            <button class="primary" type="button">{cta_primary}</button>
            <button class="secondary" type="button">{cta_secondary}</button>
          </div>
          <div class="meta reveal">
            <div>
              <span class="label">Hours</span>
              <span class="value">{hours}</span>
            </div>
            <div>
              <span class="label">Find us</span>
              <span class="value">{location}</span>
            </div>
          </div>
        </div>
        <div class="hero-visual reveal">
          <div class="stack">
{shelf_cards}
          </div>
          <div class="badge">{badge_text}</div>
        </div>
      </header>

      <section class="highlights">
        <div class="section-title">
          <p class="eyebrow">{highlights_eyebrow}</p>
          <h2>{highlights_title}</h2>
        </div>
        <div class="cards">
{highlight_cards}
        </div>
      </section>

      <section class="events">
        <div class="section-title">
          <p class="eyebrow">{events_eyebrow}</p>
          <h2>{events_title}</h2>
        </div>
        <div class="event-list">
{event_rows}
        </div>
      </section>

      <section class="membership">
        <div class="membership-card reveal">
          <h2>{membership_title}</h2>
          <p>{membership_body}</p>
          <button class="primary" type="button">{membership_cta}</button>
        </div>
        <div class="membership-note reveal">
          <p>{footer_note}</p>
        </div>
      </section>

      <footer class="footer">
        <p>{footer_note}</p>
      </footer>
    </main>
    <script src="script.js"></script>
  </body>
</html>
""",
        "styles.css": """:root {
  --paper: #f7efe6;
  --ink: #2a1d14;
  --ink-soft: #5a4536;
  --accent: #d27e5a;
  --accent-2: #7aa18c;
  --accent-3: #b58b62;
  --surface: #fffaf2;
  --shadow: 0 24px 60px rgba(37, 26, 19, 0.18);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  background: var(--paper);
  color: var(--ink);
  min-height: 100vh;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  background:
    radial-gradient(600px 480px at 10% 5%, rgba(210, 126, 90, 0.35), transparent 60%),
    radial-gradient(520px 440px at 90% 0%, rgba(122, 161, 140, 0.28), transparent 60%),
    repeating-linear-gradient(
      0deg,
      rgba(42, 29, 20, 0.06),
      rgba(42, 29, 20, 0.06) 1px,
      transparent 1px,
      transparent 6px
    );
  pointer-events: none;
  z-index: -2;
}

.background {
  position: fixed;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: -1;
}

.orb {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(255, 250, 242, 0.9), rgba(210, 126, 90, 0.3));
  opacity: 0.65;
  animation: float 12s ease-in-out infinite;
}

.orb-one {
  width: 280px;
  height: 280px;
  top: -80px;
  left: -40px;
}

.orb-two {
  width: 220px;
  height: 220px;
  right: 10%;
  top: 80px;
  animation-delay: 1s;
}

.orb-three {
  width: 320px;
  height: 320px;
  right: -120px;
  bottom: -80px;
  animation-delay: 2s;
}

.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 80px 24px 96px;
  display: flex;
  flex-direction: column;
  gap: 64px;
}

.hero {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 48px;
  align-items: center;
}

.hero-text {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.25em;
  font-size: 12px;
  color: var(--ink-soft);
}

h1,
h2 {
  font-family: "Fraunces", "Times New Roman", serif;
  letter-spacing: -0.02em;
}

h1 {
  font-size: clamp(2.6rem, 6vw, 4.3rem);
}

.tagline {
  font-size: 1.1rem;
  color: var(--ink-soft);
  max-width: 60ch;
}

.actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

button {
  border: none;
  padding: 12px 22px;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

button:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(37, 26, 19, 0.18);
}

.primary {
  background: var(--ink);
  color: #fff4e8;
}

.secondary {
  background: transparent;
  border: 1px solid var(--ink);
  color: var(--ink);
}

.meta {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  font-size: 0.95rem;
}

.meta .label {
  display: block;
  text-transform: uppercase;
  font-size: 0.7rem;
  letter-spacing: 0.2em;
  color: var(--ink-soft);
}

.meta .value {
  font-weight: 600;
}

.hero-visual {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: flex-start;
}

.stack {
  display: grid;
  gap: 16px;
  width: min(100%, 420px);
}

.book {
  background: var(--surface);
  border-radius: 18px;
  padding: 18px 20px;
  border-left: 6px solid var(--accent);
  box-shadow: var(--shadow);
}

.book-2 {
  border-left-color: var(--accent-2);
}

.book-3 {
  border-left-color: var(--accent-3);
}

.book-title {
  display: block;
  font-weight: 600;
  font-size: 1rem;
}

.book-subtitle {
  display: block;
  color: var(--ink-soft);
  margin-top: 6px;
  font-size: 0.9rem;
}

.badge {
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(42, 29, 20, 0.2);
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 0.65rem;
  color: var(--ink-soft);
}

.highlights,
.events {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-title h2 {
  font-size: clamp(1.8rem, 4vw, 2.6rem);
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 24px;
}

.card {
  background: var(--surface);
  border-radius: 20px;
  padding: 22px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card h3 {
  font-size: 1.2rem;
}

.card p {
  color: var(--ink-soft);
}

.event-list {
  display: grid;
  gap: 16px;
}

.event {
  display: grid;
  grid-template-columns: 86px 1fr;
  gap: 16px;
  align-items: center;
  background: var(--surface);
  border-radius: 18px;
  padding: 16px 20px;
  box-shadow: var(--shadow);
}

.event-date {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.8rem;
  letter-spacing: 0.12em;
  color: var(--ink-soft);
}

.event-info h3 {
  font-size: 1.1rem;
}

.event-info p {
  color: var(--ink-soft);
  margin-top: 4px;
}

.membership {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
  background: #23170f;
  color: #f9efe4;
  border-radius: 26px;
  padding: 32px;
}

.membership-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.membership-card button {
  align-self: flex-start;
  background: #f9efe4;
  color: #23170f;
}

.membership-note {
  display: flex;
  align-items: center;
  font-size: 1rem;
  color: rgba(249, 239, 228, 0.78);
}

.footer {
  text-align: center;
  font-size: 0.9rem;
  color: var(--ink-soft);
}

.reveal {
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.is-ready .reveal {
  opacity: 1;
  transform: translateY(0);
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(12px);
  }
}

@media (max-width: 720px) {
  .page {
    padding: 64px 20px 80px;
  }

  .event {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
    transition: none !important;
  }
}
""",
        "script.js": """document.addEventListener("DOMContentLoaded", () => {
  document.documentElement.classList.add("is-ready");
});
""",
        "README.md": _readme_text(objective, task, research),
    }


def _default_landing_page_spec(objective: str) -> dict[str, Any]:
    lowered = objective.lower()
    if "book" in lowered or "bookstore" in lowered or "library" in lowered:
        return {
            "name": "Hearth & Hallow Books",
            "eyebrow": "Indie Bookstore",
            "tagline": "Slow shelves, bright stories, and handpicked reads for the neighborhood.",
            "cta_primary": "Visit the shop",
            "cta_secondary": "See events",
            "hours": "Tue-Sun 10am-7pm",
            "location": "214 River St, Cedar Alley",
            "footer_note": "Independent, locally owned, and curated weekly.",
            "highlights": [
                {
                    "title": "Staff Picks Wall",
                    "body": "Fresh notes, local voices, and unexpected gems every week.",
                },
                {
                    "title": "Reading Nooks",
                    "body": "Warm light, quiet corners, and a rotating poetry shelf.",
                },
                {
                    "title": "Community Shelf",
                    "body": "Trade a book, leave a note, take a story.",
                },
            ],
            "events": [
                {
                    "date": "Thu 7 PM",
                    "title": "Poetry Night",
                    "detail": "Open mic with neighborhood writers.",
                },
                {
                    "date": "Sat 11 AM",
                    "title": "Kids Story Hour",
                    "detail": "Pillow fort and picture books.",
                },
                {
                    "date": "Sun 4 PM",
                    "title": "Debut Club",
                    "detail": "First novels and fresh voices.",
                },
            ],
            "membership": {
                "title": "Join the Night Owl Club",
                "body": "Members get early holds, quiet hours, and handwritten recs.",
                "cta": "Get the card",
            },
            "shelf": [
                {"title": "New Arrivals", "subtitle": "Fiction, essays, graphic"},
                {"title": "Staff Notes", "subtitle": "Handwritten tags + smiles"},
                {"title": "Local Authors", "subtitle": "Signed copies weekly"},
            ],
        }
    title = _title_from_objective(objective)
    if not title or "landing page" in lowered or lowered.startswith("create"):
        title = "Northwind Studio"
    return {
        "name": title,
        "eyebrow": "Independent Studio",
        "tagline": "Small team, careful craft, and a focused release every season.",
        "cta_primary": "Start a project",
        "cta_secondary": "See the work",
        "hours": "Mon-Fri 9am-6pm",
        "location": "Remote + studio visits",
        "footer_note": "Built for long-term partners.",
        "highlights": [
            {
                "title": "Creative Direction",
                "body": "Brand, tone, and narrative shaped in tight sprints.",
            },
            {
                "title": "Design Systems",
                "body": "Modular components with a calm, confident rhythm.",
            },
            {
                "title": "Launch Support",
                "body": "Clean handoff, production readiness, and QA.",
            },
        ],
        "events": [
            {
                "date": "Wed 10 AM",
                "title": "Open Studio",
                "detail": "Drop in for feedback and coffee.",
            },
            {
                "date": "Fri 1 PM",
                "title": "Process Talk",
                "detail": "Case study on a recent build.",
            },
            {
                "date": "Monthly",
                "title": "Partner Roundtable",
                "detail": "Shared wins and roadmap reviews.",
            },
        ],
        "membership": {
            "title": "Stay in the loop",
            "body": "Monthly notes with updates, releases, and new openings.",
            "cta": "Join the list",
        },
        "shelf": [
            {"title": "Current Work", "subtitle": "Web, brand, motion"},
            {"title": "Research", "subtitle": "Trends and case studies"},
            {"title": "Studio Notes", "subtitle": "Behind the scenes"},
        ],
    }


def _normalize_landing_spec(objective: str, override: dict[str, Any] | None) -> dict[str, Any]:
    base = _default_landing_page_spec(objective)
    if not override:
        return base
    spec = dict(base)
    for key in [
        "name",
        "eyebrow",
        "tagline",
        "cta_primary",
        "cta_secondary",
        "hours",
        "location",
        "footer_note",
    ]:
        if key in override:
            spec[key] = _clean_text(override.get(key), spec[key])
    if isinstance(override.get("membership"), dict):
        membership = dict(base["membership"])
        for key in ["title", "body", "cta"]:
            membership[key] = _clean_text(override["membership"].get(key), membership[key])
        spec["membership"] = membership
    spec["highlights"] = _merge_list(base["highlights"], override.get("highlights"), ["title", "body"])
    spec["events"] = _merge_list(base["events"], override.get("events"), ["date", "title", "detail"])
    spec["shelf"] = _merge_list(base["shelf"], override.get("shelf"), ["title", "subtitle"])
    return spec


def _merge_list(
    defaults: list[dict[str, str]],
    override: Any,
    keys: list[str],
) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    for index, base in enumerate(defaults):
        current = dict(base)
        if isinstance(override, list) and index < len(override) and isinstance(override[index], dict):
            source = override[index]
            for key in keys:
                current[key] = _clean_text(source.get(key), current[key])
        merged.append(current)
    return merged


def _clean_text(value: Any, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    cleaned = _ascii_sanitize(value)
    cleaned = " ".join(cleaned.split())
    return cleaned or fallback


def _ascii_sanitize(value: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "--",
        "\u2013": "-",
    }
    for src, target in replacements.items():
        value = value.replace(src, target)
    return value.encode("ascii", "ignore").decode("ascii")


def _extract_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _animation_project(
    objective: str, task: str, research: str, subject: str
) -> dict[str, str | bytes]:
    title = _title_from_objective(objective)
    gif_bytes = _generate_scene_gif(subject, width=180, height=260, frames=48)
    return {
        "index.html": f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <main class="stage">
      <h1>{title}</h1>
      <p class="subtitle">Animated GIF generated for the project output.</p>
      <figure>
        <img src="animation.gif" alt="Animated scene" />
        <figcaption>Short animated scene derived from the objective.</figcaption>
      </figure>
    </main>
  </body>
</html>
""",
        "styles.css": """* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: "Segoe UI", "Helvetica Neue", sans-serif;
  background: radial-gradient(circle at top, #0f172a, #020617);
  color: #e2e8f0;
  min-height: 100vh;
}

.stage {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 24px;
}

h1 {
  font-size: clamp(2rem, 5vw, 3.5rem);
}

.subtitle {
  color: #94a3b8;
  max-width: 60ch;
  text-align: center;
}

figure {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

img {
  width: min(320px, 80vw);
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.45);
}
""",
        "animation.gif": gif_bytes,
        "README.md": _readme_text(objective, task, research),
    }


def _readme_text(objective: str, task: str, research: str) -> str:
    return "\n".join(
        [
            "# Project Output",
            "",
            f"Objective: {objective}",
            "",
            f"Task: {task}",
            "",
            "Research context:",
            research or "None",
            "",
        ]
    )


def _title_from_objective(objective: str) -> str:
    cleaned = objective.strip()
    if not cleaned:
        return "Swarm Project"
    return cleaned[:60]


def _python_game_project(objective: str, task: str, research: str) -> dict[str, str | bytes]:
    return {
        "main.py": """import random
import time


def render(board_width: int, board_height: int, snake: list[tuple[int, int]], food: tuple[int, int]) -> None:
    print("\\033[2J\\033[H", end="")
    for y in range(board_height):
        row = []
        for x in range(board_width):
            if (x, y) == food:
                row.append("*")
            elif (x, y) == snake[0]:
                row.append("O")
            elif (x, y) in snake:
                row.append("o")
            else:
                row.append(".")
        print("".join(row))


def place_food(board_width: int, board_height: int, snake: list[tuple[int, int]]) -> tuple[int, int]:
    while True:
        spot = (random.randint(0, board_width - 1), random.randint(0, board_height - 1))
        if spot not in snake:
            return spot


def run() -> None:
    board_width = 24
    board_height = 12
    snake = [(5, 5), (4, 5), (3, 5)]
    direction = (1, 0)
    food = place_food(board_width, board_height, snake)

    while True:
        head_x, head_y = snake[0]
        dx, dy = direction
        new_head = (head_x + dx, head_y + dy)
        if (
            new_head[0] < 0
            or new_head[0] >= board_width
            or new_head[1] < 0
            or new_head[1] >= board_height
            or new_head in snake
        ):
            print("Game over.")
            break
        snake.insert(0, new_head)
        if new_head == food:
            food = place_food(board_width, board_height, snake)
        else:
            snake.pop()

        render(board_width, board_height, snake, food)
        time.sleep(0.2)


if __name__ == "__main__":
    run()
""",
        "README.md": _readme_text(objective, task, research),
    }


def _image_edit_project(objective: str, task: str, research: str) -> dict[str, str | bytes]:
    return {
        "edit_image.py": """from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install Pillow: pip install pillow") from exc


def edit_image(input_path: Path, output_path: Path) -> None:
    image = Image.open(input_path)
    edited = ImageOps.autocontrast(image.convert("RGB"))
    edited = ImageOps.posterize(edited, bits=4)
    overlay = ImageDraw.Draw(edited)
    overlay.rectangle([(12, 12), (edited.width - 12, 56)], fill=(15, 23, 42))
    overlay.text((24, 22), "Swarm Edit", fill=(248, 250, 252))
    edited.save(output_path)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("Usage: python edit_image.py input.jpg output.jpg")
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    edit_image(input_path, output_path)


if __name__ == "__main__":
    main()
""",
        "requirements.txt": "pillow>=10.0\n",
        "README.md": "\n".join(
            [
                "# Image Edit Project",
                "",
                f"Objective: {objective}",
                "",
                "Usage:",
                "python edit_image.py input.jpg output.jpg",
                "",
                "This script applies auto-contrast and a posterized stylization.",
                "",
            ]
        ),
    }


def _read_text(context: AgentContext, path: Path) -> str:
    try:
        return context.filesystem.read_text(path)
    except Exception:
        return ""


def _read_json(context: AgentContext, path: Path) -> dict[str, Any]:
    try:
        return json.loads(context.filesystem.read_text(path))
    except Exception:
        return {}


def _generate_scene_gif(subject: str, width: int, height: int, frames: int) -> bytes:
    palette = [
        (0, 0, 0),
        (224, 228, 248),
        (249, 115, 22),
        (56, 189, 248),
        (34, 197, 94),
    ]
    frame_data: list[list[int]] = []
    lowered = subject.lower()
    is_dino = "dinosaur" in lowered or "dino" in lowered
    for index in range(frames):
        pixels = [0] * (width * height)
        _draw_moon(pixels, width, height, cx=135, cy=50, radius=18, color=1)
        if is_dino:
            _draw_ground(pixels, width, height, ground_y=height - 40, color=1)
            _draw_dino(pixels, width, height, frame=index, color_body=4)
        else:
            _draw_rocket(pixels, width, height, frame=index, color_body=2, color_flame=3)
        frame_data.append(pixels)
    return _encode_gif(width, height, palette, frame_data, delay_cs=6)


def _draw_moon(
    pixels: list[int], width: int, height: int, cx: int, cy: int, radius: int, color: int
) -> None:
    r2 = radius * radius
    for y in range(max(0, cy - radius), min(height, cy + radius)):
        for x in range(max(0, cx - radius), min(width, cx + radius)):
            dx = x - cx
            dy = y - cy
            if dx * dx + dy * dy <= r2:
                pixels[y * width + x] = color


def _draw_rect(
    pixels: list[int],
    width: int,
    height: int,
    x: int,
    y: int,
    rect_w: int,
    rect_h: int,
    color: int,
) -> None:
    for row in range(max(0, y), min(height, y + rect_h)):
        row_start = row * width
        for col in range(max(0, x), min(width, x + rect_w)):
            pixels[row_start + col] = color


def _draw_rocket(
    pixels: list[int],
    width: int,
    height: int,
    frame: int,
    color_body: int,
    color_flame: int,
) -> None:
    base_y = height - 60 - frame * 2
    center_x = width // 2 - 12
    stage_height = 10
    stage_width = 26
    for idx in range(5):
        y = base_y - idx * (stage_height + 2)
        _draw_rect(pixels, width, height, center_x, y, stage_width, stage_height, color_body)
    flame_y = base_y + 6
    _draw_rect(pixels, width, height, center_x + 6, flame_y, 14, 8, color_flame)


def _draw_ground(
    pixels: list[int], width: int, height: int, ground_y: int, color: int
) -> None:
    _draw_rect(pixels, width, height, 0, ground_y, width, height - ground_y, color)


def _draw_dino(
    pixels: list[int],
    width: int,
    height: int,
    frame: int,
    color_body: int,
) -> None:
    ground_y = height - 40
    x_offset = 20 + (frame * 3) % (width - 60)
    body_y = ground_y - 28
    _draw_rect(pixels, width, height, x_offset, body_y, 32, 16, color_body)
    _draw_rect(pixels, width, height, x_offset + 20, body_y - 12, 12, 12, color_body)
    _draw_rect(pixels, width, height, x_offset + 6, ground_y - 12, 6, 12, color_body)
    _draw_rect(pixels, width, height, x_offset + 20, ground_y - 12, 6, 12, color_body)
    _draw_rect(pixels, width, height, x_offset - 6, body_y + 4, 6, 6, color_body)


def _encode_gif(
    width: int,
    height: int,
    palette: list[tuple[int, int, int]],
    frames: list[list[int]],
    delay_cs: int,
) -> bytes:
    header = b"GIF89a"
    gct_size = _next_power_of_two(max(2, len(palette)))
    gct_bits = max(0, gct_size.bit_length() - 2)
    packed = 0x80 | (7 << 4) | gct_bits
    lsd = _pack_le(width, 2) + _pack_le(height, 2) + bytes([packed, 0x00, 0x00])
    padded_palette = palette + [(0, 0, 0)] * (gct_size - len(palette))
    gct = b"".join(bytes(rgb) for rgb in padded_palette)
    app_ext = b"".join(
        [
            b"\x21\xFF\x0BNETSCAPE2.0",
            b"\x03\x01",
            _pack_le(0, 2),
            b"\x00",
        ]
    )
    blocks = [header, lsd, gct, app_ext]
    for frame in frames:
        blocks.append(_graphics_control_ext(delay_cs))
        blocks.append(_image_descriptor(width, height))
        blocks.append(_image_data(frame, min_code_size=_min_code_size(len(palette))))
    blocks.append(b"\x3B")
    return b"".join(blocks)


def _graphics_control_ext(delay_cs: int) -> bytes:
    return b"".join(
        [
            b"\x21\xF9\x04",
            b"\x04",
            _pack_le(delay_cs, 2),
            b"\x00",
            b"\x00",
        ]
    )


def _image_descriptor(width: int, height: int) -> bytes:
    return b"".join(
        [
            b"\x2C",
            _pack_le(0, 2),
            _pack_le(0, 2),
            _pack_le(width, 2),
            _pack_le(height, 2),
            b"\x00",
        ]
    )


def _image_data(pixels: list[int], min_code_size: int) -> bytes:
    lzw_bytes = _lzw_encode(pixels, min_code_size)
    return bytes([min_code_size]) + _chunk_subblocks(lzw_bytes) + b"\x00"


def _lzw_encode(pixels: list[int], min_code_size: int) -> bytes:
    clear_code = 1 << min_code_size
    end_code = clear_code + 1
    next_code = end_code + 1
    code_size = min_code_size + 1
    max_code = 1 << code_size
    dictionary = {bytes([i]): i for i in range(clear_code)}

    codes: list[tuple[int, int]] = []

    def emit(code: int) -> None:
        codes.append((code, code_size))

    emit(clear_code)
    w = b""
    for pixel in pixels:
        k = bytes([pixel])
        wk = w + k
        if wk in dictionary:
            w = wk
            continue
        if w:
            emit(dictionary[w])
        dictionary[wk] = next_code
        next_code += 1
        w = k
        if next_code == max_code and code_size < 12:
            code_size += 1
            max_code = 1 << code_size
        if next_code >= 4096:
            emit(clear_code)
            dictionary = {bytes([i]): i for i in range(clear_code)}
            code_size = min_code_size + 1
            max_code = 1 << code_size
            next_code = end_code + 1
    if w:
        emit(dictionary[w])
    emit(end_code)

    bit_buffer = 0
    bit_count = 0
    output = bytearray()
    for code, size in codes:
        bit_buffer |= code << bit_count
        bit_count += size
        while bit_count >= 8:
            output.append(bit_buffer & 0xFF)
            bit_buffer >>= 8
            bit_count -= 8
    if bit_count:
        output.append(bit_buffer & 0xFF)
    return bytes(output)


def _chunk_subblocks(data: bytes) -> bytes:
    blocks = []
    for i in range(0, len(data), 255):
        chunk = data[i : i + 255]
        blocks.append(bytes([len(chunk)]) + chunk)
    return b"".join(blocks)


def _pack_le(value: int, length: int) -> bytes:
    return value.to_bytes(length, byteorder="little")


def _min_code_size(color_count: int) -> int:
    size = 2
    while (1 << size) < color_count:
        size += 1
    return size


def _next_power_of_two(value: int) -> int:
    power = 1
    while power < value:
        power <<= 1
    return power


def _determine_deliverable(research: str) -> str:
    combined = f"{research}".lower()
    if "deliverable:" in combined and "gif" in combined:
        return "gif"
    if "deliverable:" in combined and "python" in combined:
        return "python"
    if "deliverable:" in combined and "image" in combined:
        return "image_edit"
    if "gif encoder" in combined or "animated gif" in combined:
        return "gif"
    return "html"
