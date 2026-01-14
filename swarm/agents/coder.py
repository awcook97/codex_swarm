from __future__ import annotations

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
        deliverable = _determine_deliverable(context.objective, research)
        files = _build_project_files(context.objective, task, research, deliverable)
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
        return {"artifact": str(artifact_dir), "files": list(files.keys()), "content": summary}


def _build_project_files(
    objective: str, task: str, research: str, deliverable: str
) -> dict[str, str | bytes]:
    if deliverable == "gif":
        return _animation_project(objective, task, research)
    return _landing_page_project(objective, task, research)


def _landing_page_project(objective: str, task: str, research: str) -> dict[str, str]:
    title = _title_from_objective(objective)
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
    <main class="page">
      <header class="hero">
        <p class="eyebrow">Project</p>
        <h1>{title}</h1>
        <p class="subtitle">{objective}</p>
        <div class="actions">
          <button class="primary">Launch</button>
          <button class="ghost">Learn more</button>
        </div>
      </header>
      <section class="grid">
        <article>
          <h2>Focus</h2>
          <p>Clear structure, bold typography, and a single narrative.</p>
        </article>
        <article>
          <h2>Experience</h2>
          <p>Snappy layout, purposeful spacing, and scalable sections.</p>
        </article>
        <article>
          <h2>Output</h2>
          <p>Project-ready HTML/CSS with a light JS scaffold.</p>
        </article>
      </section>
    </main>
    <script src="script.js"></script>
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
  background: radial-gradient(circle at top, #f9fafb, #e5e7eb);
  color: #111827;
  min-height: 100vh;
}

.page {
  max-width: 980px;
  margin: 0 auto;
  padding: 72px 24px;
  display: flex;
  flex-direction: column;
  gap: 48px;
}

.hero {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 12px;
  color: #6b7280;
}

h1 {
  font-size: clamp(2.5rem, 6vw, 4rem);
  font-weight: 700;
}

.subtitle {
  font-size: 1.1rem;
  color: #374151;
  max-width: 60ch;
}

.actions {
  display: flex;
  gap: 16px;
  margin-top: 12px;
}

button {
  border: none;
  padding: 12px 20px;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
}

.primary {
  background: #111827;
  color: #f9fafb;
}

.ghost {
  background: transparent;
  border: 1px solid #9ca3af;
  color: #111827;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 24px;
}

.grid article {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}
""",
        "script.js": """document.querySelectorAll("button").forEach((button) => {
  button.addEventListener("click", () => {
    button.textContent = "Queued";
  });
});
""",
        "README.md": _readme_text(objective, task, research),
    }


def _animation_project(objective: str, task: str, research: str) -> dict[str, str | bytes]:
    title = _title_from_objective(objective)
    gif_bytes = _generate_scene_gif(objective, width=180, height=260, frames=48)
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


def _generate_scene_gif(objective: str, width: int, height: int, frames: int) -> bytes:
    palette = [
        (0, 0, 0),
        (224, 228, 248),
        (249, 115, 22),
        (56, 189, 248),
        (34, 197, 94),
    ]
    frame_data: list[list[int]] = []
    lowered = objective.lower()
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


def _determine_deliverable(objective: str, research: str) -> str:
    combined = f"{objective}\n{research}".lower()
    if "deliverable:" in combined and "gif" in combined:
        return "gif"
    if "gif encoder" in combined or "animated gif" in combined:
        return "gif"
    if "movie" in combined or "animation" in combined:
        return "gif"
    return "html"
