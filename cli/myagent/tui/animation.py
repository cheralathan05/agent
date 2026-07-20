"""Animation system, mascot character, and visual effects for MyAgent premium TUI.

Provides:
- Animated AI agent mascot with state-based expressions
- Particle/sparkle effects for decorative flair
- Color gradient utilities
- Frame animation helpers
"""

import math
import random
import sys
import time

from rich.text import Text

# ── Detect Unicode support ────────────────────────

_SUPPORTS_UNICODE = not (
    sys.platform == "win32" and (
        "cmd" in sys.stdout.encoding or
        getattr(sys.stdout, "encoding", "").lower() in ("cp437", "cp850", "latin-1")
    )
)


# ── Mascot: Animated AI Character ──────────────────

class Mascot:
    """Animated AI agent character that changes expression based on agent state.
    
    Expressions:
      idle    → 😊  Ready
      thinking→ 🤔  Processing  
      working → 🛠️  Building
      reading → 📖  Reading
      testing → 🔬  Testing
      done    → 😎  Complete!
      error   → 😰  Error
      typing  → ✍️  Typing
      waiting → ⏳  Waiting
    """

    # ASCII art faces for each state (fallback when Unicode limited)
    ASCII_FACES = {
        "idle":     ["(◕‿◕)", "(◠‿◠)", "(＾▽＾)"],
        "thinking": ["(◔_◔)", "(◉_◉)", "(⊙_⊙)", "(◕_◕?)"],
        "working":  ["(◣_◢)", "(◗_◖)", "(⚆_⚆)"],
        "reading":  ["(◕‿◕)", "(◕◡◕)", "(◕‿◕)"],
        "testing":  ["(◕‿◕)", "(◠‿◠)", "(⌐■_■)"],
        "done":     ["(◕‿◕✿)", "(ᵔ◡◡◕)", "(◠‿◠✿)"],
        "error":    ["(◕︵◕)", "(◕﹏◕)", "(◕‸◕)"],
        "typing":   ["(◕‿◕)", "(◕‿◕)", "(◕‿◕)"],
        "waiting":  ["(◕‿◕)", "(◕_◕)", "(◕‿◕)"],
        "sparkle":  ["✨", "🌟", "💫", "✨"],
    }

    # Unicode emoji states (primary)
    EMOJI_STATES = {
        "ready":     "✨",
        "completed": "🎯",
        "thinking":  "🤔",
        "planning":  "📋",
        "reading":   "📖",
        "editing":   "✏️",
        "running":   "⚡",
        "testing":   "🔬",
        "reviewing": "👁️",
        "waiting_approval": "⏳",
        "error":     "⚠️",
        "typing":    "✍️",
    }

    # Blinking animation frames
    BLINK_FRAMES = ["(◕‿◕)", "(◕_◕)", "(◕‿◕)"]

    def __init__(self):
        self.current_state = "ready"
        self._frame = 0
        self._blink_counter = 0
        self._blink_every = 15  # Blink every 15 frames

    def set_state(self, state: str):
        """Update the mascot's state/expression."""
        self.current_state = state

    def tick(self):
        """Advance animation by one frame."""
        self._frame += 1
        self._blink_counter = (self._blink_counter + 1) % self._blink_every

    @property
    def emoji(self) -> str:
        """Get the emoji for the current state."""
        return self.EMOJI_STATES.get(self.current_state, "✨")

    @property
    def face(self) -> str:
        """Get the animated ASCII face for the current state."""
        if self.current_state in ("ready", "completed"):
            # Show blinking animation
            if self._blink_counter == self._blink_every - 1:
                return self.BLINK_FRAMES[1]  # Blink
            return self.BLINK_FRAMES[0]

        faces = self.ASCII_FACES.get(self.current_state, self.ASCII_FACES["idle"])
        idx = self._frame % len(faces)
        return faces[idx]

    def render_compact(self) -> Text:
        """Render a compact mascot emoji with state color."""
        emoji = self.emoji
        colors = {
            "ready": "bold green",
            "completed": "bold green",
            "thinking": "bold cyan",
            "planning": "bold blue",
            "reading": "bold cyan",
            "editing": "bold yellow",
            "running": "bold yellow",
            "testing": "bold magenta",
            "reviewing": "bold blue",
            "waiting_approval": "bold yellow",
            "error": "bold red",
            "typing": "bold green",
        }
        color = colors.get(self.current_state, "bold white")
        return Text(f" {emoji} ", style=color)


# ── Sparkle / Particle System ─────────────────────

class Sparkle:
    """A single sparkle particle with position and lifecycle."""

    def __init__(self, x: int, y: int, lifetime: int = 20):
        self.x = x
        self.y = y
        self.lifetime = lifetime
        self.age = 0
        self.alive = True
        # Random sparkle character
        self.chars = ["✦", "✧", "⋆", "⋅", "∙", "◦", "°", "✴"]
        self.char = random.choice(self.chars) if _SUPPORTS_UNICODE else "*"
        # Color - cycle through bright colors
        self.colors = ["bright_yellow", "bright_white", "bright_cyan", "bright_green", "bright_magenta"]
        self.color = random.choice(self.colors)

    def tick(self) -> bool:
        """Advance one frame. Returns False if particle should be removed."""
        self.age += 1
        if self.age >= self.lifetime:
            self.alive = False
            return False
        # Float upward and fade
        self.y -= 0.3
        return True

    def render(self) -> Text:
        """Render the sparkle at its current lifecycle stage."""
        if not self.alive:
            return Text("")
        # Fade out in last third of life
        if self.age > self.lifetime * 2 // 3:
            dim_factor = (self.lifetime - self.age) / (self.lifetime / 3)
            style = f"dim {self.color}"
        else:
            style = self.color
        return Text(self.char, style=style)


class SparkleManager:
    """Manages a collection of sparkle particles."""

    def __init__(self, max_particles: int = 8):
        self.particles: list[Sparkle] = []
        self.max_particles = max_particles
        self._spawn_counter = 0

    def add_burst(self, x: int, y: int, count: int = 3):
        """Create a burst of sparkles at position."""
        for _ in range(count):
            if len(self.particles) < self.max_particles:
                lifetime = random.randint(10, 25)
                offset_x = random.randint(-2, 2)
                self.particles.append(Sparkle(x + offset_x, y, lifetime))

    def tick(self):
        """Advance all particles and remove dead ones."""
        self.particles = [p for p in self.particles if p.tick()]
        self._spawn_counter += 1

    @property
    def has_particles(self) -> bool:
        return len(self.particles) > 0

    def render_all(self) -> list[Text]:
        """Render all active particles."""
        return [p.render() for p in self.particles if p.alive]


# ── Progress Bar with Animation ───────────────────

class AnimatedBar:
    """An animated progress bar with pulse effect."""

    BLOCK_FULL = "█"
    BLOCK_EMPTY = "░"
    BLOCK_MED = "▒"

    def __init__(self, length: int = 10):
        self.length = length
        self._frame = 0

    def tick(self):
        """Advance animation frame."""
        self._frame += 1

    def render(self, pct: float, pulse: bool = False) -> Text:
        """Render the animated progress bar.
        
        Args:
            pct: 0.0 to 100.0
            pulse: If True, add a pulsing glow effect
        """
        filled = int(self.length * pct / 100)
        bar = self.BLOCK_FULL * filled + self.BLOCK_EMPTY * (self.length - filled)

        if pulse and filled > 0 and filled < self.length:
            # Add pulse at the current fill boundary
            pulse_pos = filled
            pulse_char = "▓" if (self._frame // 3) % 2 == 0 else "▒"
            if pulse_pos > 0 and pulse_pos <= self.length:
                bar = bar[:pulse_pos - 1] + pulse_char + bar[pulse_pos:]

        # Color based on percentage
        if pct < 50:
            color = "green"
        elif pct < 80:
            color = "yellow"
        else:
            color = "red"

        return Text(bar, style=f"bold {color}")


# ── Color / Gradient Utilities ────────────────────

# Rich color names for gradient effects
_GRADIENT_COLORS = {
    "cyberpunk": ["bright_magenta", "bright_cyan", "bright_blue", "bright_magenta"],
    "sunset":    ["bright_red", "bright_yellow", "bright_magenta", "bright_red"],
    "ocean":     ["bright_cyan", "bright_blue", "bright_green", "bright_cyan"],
    "neon":      ["bright_green", "bright_yellow", "bright_cyan", "bright_green"],
    "fire":      ["bright_red", "bright_yellow", "bright_red", "bright_yellow"],
    "royal":     ["bright_magenta", "bright_blue", "bright_cyan", "bright_magenta"],
}


def cycle_colors(scheme: str = "cyberpunk", frame: int = 0) -> list[str]:
    """Get a color scheme, optionally cycled by frame."""
    colors = _GRADIENT_COLORS.get(scheme, _GRADIENT_COLORS["cyberpunk"])
    shift = frame % len(colors)
    return colors[shift:] + colors[:shift]


def gradient_text(text: str, scheme: str = "cyberpunk", frame: int = 0, bold: bool = False) -> Text:
    """Create text with gradient color effect."""
    colors = cycle_colors(scheme, frame)
    bold_prefix = "bold " if bold else ""
    result = Text()
    for i, ch in enumerate(text):
        color = colors[i % len(colors)]
        result.append(ch, style=f"{bold_prefix}{color}")
    return result


def pulsing_style(frame: int, base_color: str = "cyan", speed: float = 0.1) -> str:
    """Create a pulsing style name that oscillates between dim and bright."""
    phase = math.sin(frame * speed)
    if phase > 0.5:
        return f"bold {base_color}"
    elif phase > -0.3:
        return base_color
    else:
        return f"dim {base_color}"


# ── Frame Rate & Time Utils ───────────────────────

class FrameCounter:
    """Simple frame counter for animations."""

    def __init__(self):
        self.frame = 0
        self._start = time.monotonic()

    def tick(self) -> int:
        """Advance and return current frame number."""
        self.frame += 1
        return self.frame

    @property
    def elapsed(self) -> float:
        """Seconds since start."""
        return time.monotonic() - self._start

    @property
    def fps(self) -> float:
        """Calculated FPS."""
        if self.elapsed > 0:
            return self.frame / self.elapsed
        return 0.0

    def format_elapsed(self) -> str:
        """Format elapsed time as MM:SS."""
        total = int(self.elapsed)
        m, s = divmod(total, 60)
        return f"{m:02d}:{s:02d}"
