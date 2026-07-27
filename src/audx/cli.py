"""audx command-line interface."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import typer
from rich.console import Console

from audx import __version__
from audx.config import CONFIG_DIR, DEFAULT_BPM, PROJECTS_DIR, SAMPLES_DIR
from audx.engine import get_engine, init_engine
from audx.pattern import Pattern, get_pattern_engine
from audx.project import (
    Project,
    diff_projects,
    init_project,
    list_projects,
)
from audx.sampler import SampleLibrary
from audx.ui.app import DAWApp

console = Console()

app = typer.Typer(help="audx — code your music, own your sound.")
pattern_app = typer.Typer(help="Pattern commands")
samples_app = typer.Typer(help="Sample library commands (alias: stems)")
projects_app = typer.Typer(help="Project commands")
track_app = typer.Typer(help="Track add/remove")
mix_app = typer.Typer(help="Mixer commands")
plugin_app = typer.Typer(help="Plugin discovery commands")
push2_app = typer.Typer(help="Push 2 mapping commands")
heartmula_app = typer.Typer(help="Heartmula bridge commands")
sadact_app = typer.Typer(help="Sadact bridge commands")
daemon_app = typer.Typer(help="audxd daemon commands")
ai_app = typer.Typer(help="AI-assisted composition and analysis (optional extras)")
midi_app = typer.Typer(help="MIDI clock out, input recording")
macro_app = typer.Typer(help="Macro registers (vim-style qa…q…@a)")
slot_app = typer.Typer(help="Pattern slots A/B/C/D")
export_app = typer.Typer(help="Export to other formats")
song_app = typer.Typer(help="Song rendering and arrangement commands")
app.add_typer(pattern_app, name="pattern")
app.add_typer(samples_app, name="samples")
app.add_typer(samples_app, name="stems")  # spec uses `audx stems`
app.add_typer(projects_app, name="projects")
app.add_typer(track_app, name="track")
app.add_typer(mix_app, name="mix")
app.add_typer(plugin_app, name="plugins")
app.add_typer(push2_app, name="push2")
app.add_typer(heartmula_app, name="heartmula")
app.add_typer(sadact_app, name="sadact")
app.add_typer(daemon_app, name="daemon")
app.add_typer(ai_app, name="ai")
app.add_typer(midi_app, name="midi")
app.add_typer(macro_app, name="macro")
app.add_typer(slot_app, name="slot")
app.add_typer(export_app, name="export")
app.add_typer(song_app, name="song")
pattern_app.add_typer(slot_app, name="slot")  # `audx pattern slot ...`


def _pattern_payload() -> list[dict]:
    return [
        {
            "name": name,
            "dsl": pattern.dsl,
            "length_beats": pattern.length_beats,
            "channel": pattern.channel,
            "swing": pattern.swing,
        }
        for name, pattern in get_pattern_engine().patterns.items()
    ]


def _load_project(path: Path) -> Project:
    if not path.exists():
        typer.echo(f"Project not found: {path}", err=True)
        raise typer.Exit(1)
    project = Project.load(path)
    project.apply_to_engine()
    init_engine().set_bpm(project.bpm)
    return project


@app.command()
def launch(
    project: Path | None = typer.Argument(None, help="Path to .audx project file"),
    samples: Path | None = typer.Option(None, "--samples", "-s", help="Samples directory"),
) -> None:
    """Launch the audx TUI."""
    if samples:
        os.environ["AUDX_SAMPLES_DIR"] = str(samples)
    if project is not None:
        loaded = _load_project(project)
        typer.echo(f"Loaded project: {loaded.name}")
    else:
        last = CONFIG_DIR / "last.audx"
        if last.exists():
            try:
                loaded = _load_project(last)
                typer.echo(f"Auto-loaded last project: {loaded.name}")
            except typer.Exit:
                raise
            except Exception as exc:
                typer.echo(f"Could not auto-load last project: {exc}", err=True)
    DAWApp(project=project, samples_dir=samples).run()


@app.command()
def init(
    name: str = typer.Argument(..., help="Project folder name"),
    template: str = typer.Option("empty", "--template", "-t", help="Starter template: empty | techno | hip-hop | demo"),
    parent: Path = typer.Option(Path.cwd(), "--parent", "-p", help="Parent directory"),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git init"),
) -> None:
    """Scaffold a new project folder (spec §06).

    Creates ``<parent>/<name>/`` with ``project.audx``, ``stems/``, ``renders/``
    and (unless ``--no-git``) ``git init``.
    """
    try:
        path = init_project(name=name, parent=parent, template=template, git=not no_git)
    except FileExistsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"  ✓ created {path.parent}/project.audx")
    typer.echo(f"  ✓ created {path.parent}/stems/")
    typer.echo(f"  ✓ created {path.parent}/renders/")


@app.command()
def open(
    project: Path | None = typer.Argument(None, help="Path to .audx project file or folder"),
    samples: Path | None = typer.Option(None, "--samples", "-s", help="Samples directory"),
    web: bool = typer.Option(False, "--web", "-w", help="Open playable browser UI in localhost web companion"),
) -> None:
    """Open the TUI or Web companion on a project."""
    if web:
        import webbrowser

        from audx.web import serve

        url = "http://127.0.0.1:8080/app"
        if project:
            proj_path = project / "project.audx" if project.is_dir() else project
            url += f"?project={proj_path.resolve()}"
        typer.echo(f"  ✓ Serving web UI on {url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        serve(host="127.0.0.1", port=8080)
        return

    if project and project.is_dir():
        project = project / "project.audx"
    launch(project=project, samples=samples)


@app.command("jam")
def jam_command(
    genre: str | None = typer.Option(None, "--genre", "-g", help="Genre preset: techno | house | hiphop | ukg | ambient"),
    chromatic: bool = typer.Option(False, "--chromatic", "-c", help="Chromatic mode for sample/synth play"),
    auto: bool = typer.Option(False, "--auto", "-a", help="Auto-build track on the spot"),
    bpm: float | None = typer.Option(None, "--bpm", "-b", help="Tempo BPM"),
    project: Path | None = typer.Option(None, "--project", "-p", help="Project file"),
    once: bool = typer.Option(False, "--once", help="Run single loop iteration and exit (for non-blocking tests)"),
) -> None:
    """Start an interactive live jam session with pattern sequencing and drum pads."""
    import time

    from rich.panel import Panel

    from audx.generator import Genre, generate_track
    from audx.sampler import get_sample_library

    lib = get_sample_library()
    selected_genre = Genre.TECHNO
    if genre:
        try:
            selected_genre = Genre(genre.lower().strip())
        except ValueError:
            selected_genre = Genre.TECHNO

    if auto or genre or project is None:
        jam_bpm, patterns = generate_track(selected_genre, library=lib)
    else:
        proj = _load_project(project)
        jam_bpm = proj.bpm
        patterns = list(get_pattern_engine().patterns.values())

    effective_bpm = bpm or jam_bpm
    get_pattern_engine().set_bpm(effective_bpm)

    console.print(
        Panel(
            f"[bold green]🎵 audx live jam session[/bold green]\n"
            f"BPM: [cyan]{effective_bpm:.1f}[/cyan]  |  Genre: [magenta]{selected_genre.value.upper()}[/magenta]  |  Patterns: {len(patterns)}\n"
            f"[dim]Press Ctrl-C to stop jamming.[/dim]",
            title="audx jam",
            border_style="green",
        )
    )

    for p in patterns:
        console.print(f"  • [yellow]{p.name}[/yellow]: [dim]{p.dsl}[/dim]")

    from audx.push2 import find_push2_input, find_push2_output, light_push2_pads

    push_out = find_push2_output()
    if push_out:
        light_push2_pads(push_out)

    push_in_name = find_push2_input()
    active_hits: dict[str, float] = {}

    def _get_midi_note_sample(note: int) -> tuple[str, int]:
        if note in (35, 36):
            return ("kick", 0)
        elif note in (37, 38, 40):
            return ("snare", 1)
        elif note in (42, 44, 46):
            return ("hh", 2)
        elif note == 39:
            return ("clap", 1)
        elif note in (41, 43, 45, 47, 48):
            return ("perc", 3)
        elif note in (49, 51, 52):
            return ("crash", 2)
        else:
            notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            octave = (note // 12) - 1
            note_name = notes[note % 12]
            return (f"{note_name}{octave}", 3)

    if push_in_name:
        import threading

        def _push2_listener() -> None:
            try:
                import mido

                with mido.open_input(push_in_name) as port:
                    for msg in port:
                        if msg.type == "note_on" and msg.velocity > 0:
                            sample_name, ch = _get_midi_note_sample(msg.note)
                            # Loud, punchy velocity curve (0.6..1.0 gain)
                            scaled_gain = 0.6 + 0.4 * (msg.velocity / 127.0)
                            eng = get_engine()
                            if eng:
                                eng.trigger_hit(sample_name, channel=ch, velocity=scaled_gain)
                            active_hits[sample_name] = time.time()
            except Exception:
                pass

        t = threading.Thread(target=_push2_listener, daemon=True)
        t.start()

    try:
        eng = init_engine()
        get_pattern_engine().start()
        eng.start()
    except Exception as exc:
        console.print(f"[yellow]Audio stream notice: {exc}[/yellow]")

    if once:
        time.sleep(0.2)
        get_pattern_engine().stop()
        active_engine = get_engine()
        if active_engine is not None:
            active_engine.stop()
        console.print("[dim]Jam loop complete.[/dim]")
        return

    from rich.live import Live
    from rich.table import Table

    def _render_jam_dashboard() -> Panel:
        now = time.time()
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Track", style="cyan", width=12)
        table.add_column("Pad Hit", width=10)
        table.add_column("DSL Pattern", style="dim")

        for p in patterns:
            last_hit = active_hits.get(p.name, 0)
            hit_active = (now - last_hit) < 0.25
            hit_badge = "[bold black on bright_green] ⚡ HIT! [/bold black on bright_green]" if hit_active else "[dim]· idle[/dim]"
            table.add_row(p.name, hit_badge, p.dsl)

        push_status = f"[bold green]✓ '{push_in_name}' active[/bold green]" if push_in_name else "[yellow]· No Push 2 detected[/yellow]"
        body = Table.grid(padding=1)
        body.add_row(f"BPM: [cyan]{effective_bpm:.1f}[/cyan]  |  Genre: [magenta]{selected_genre.value.upper()}[/magenta]  |  Push 2: {push_status}")
        body.add_row(table)
        body.add_row("[dim]Press Ctrl-C to stop jamming.[/dim]")

        return Panel(body, title="🎵 audx live jam session & pad grid", border_style="green")

    try:
        with Live(_render_jam_dashboard(), refresh_per_second=10, console=console) as live:
            while True:
                time.sleep(0.1)
                live.update(_render_jam_dashboard())
    except KeyboardInterrupt:
        active_engine = get_engine()
        if active_engine is not None:
            active_engine.stop()
        get_pattern_engine().stop()
        console.print("\n[bold green]Jam session stopped.[/bold green]")


@app.command()
def doctor() -> None:
    """Run diagnostics and check setup."""
    from rich.panel import Panel
    from rich.table import Table

    table = Table(title="audx doctor diagnostics", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold green")
    table.add_column("Details")

    table.add_row("audx Version", "✓ OK", __version__)
    table.add_row("Python Version", "✓ OK", sys.version.split()[0])
    table.add_row("CLI Framework", "✓ OK", "click, typer, rich active")

    audio_ok = True
    audio_detail = ""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        audio_detail = f"{len(devices)} device(s) found (default: {sd.default.device})"
    except Exception as exc:
        audio_ok = False
        audio_detail = f"PortAudio error: {exc}"

    if audio_ok:
        table.add_row("Audio Subsystem", "✓ OK", audio_detail)
    else:
        table.add_row("Audio Subsystem", "[bold red]✗ Error[/bold red]", audio_detail)

    try:
        from audx.midi import list_inputs, list_outputs
        from audx.push2 import find_push2_input, find_push2_output

        ins, outs = list_inputs(), list_outputs()
        push_in = find_push2_input()
        push_out = find_push2_output()
        if push_in or push_out:
            table.add_row("MIDI / Push 2", "✓ OK", f"Push 2 detected (in: {push_in or 'none'}, out: {push_out or 'none'})")
        else:
            table.add_row("MIDI Ports", "✓ OK" if (ins or outs) else "· None detected", f"inputs: {len(ins)}, outputs: {len(outs)}")
    except Exception as exc:
        table.add_row("MIDI Ports", "[yellow]· Warning[/yellow]", str(exc))

    table.add_row("Samples Dir", "✓ OK" if SAMPLES_DIR.exists() else "· Scaffold", str(SAMPLES_DIR))
    table.add_row("Projects Dir", "✓ OK", str(PROJECTS_DIR))
    table.add_row("Config Dir", "✓ OK", str(CONFIG_DIR))

    console.print(table)

    if not audio_ok:
        console.print(
            Panel(
                "[bold red]PortAudio library missing or audio device unavailable.[/bold red]\n\n"
                "Fix for macOS (Homebrew):\n"
                "  [bold green]brew install portaudio[/bold green]\n\n"
                "Fix for Linux (Ubuntu/Debian):\n"
                "  [bold green]sudo apt install libportaudio2[/bold green]",
                title="Fix Native Audio Dependencies",
                border_style="red",
            )
        )


@app.command()
def save(
    path: Path = typer.Argument(..., help="Project file path (.audx)"),
    name: str | None = typer.Option(None, "--name", "-n", help="Project name"),
) -> None:
    """Save current in-process state to a project file."""
    project = Project(name=name or path.stem, bpm=get_pattern_engine().bpm, patterns=_pattern_payload())
    project.save(path)
    typer.echo(f"Saved project to {path} ({len(project.patterns)} patterns)")


@app.command()
def load(
    path: Path = typer.Argument(..., help="Project .audx path or audio file to load"),
    ch: int | None = typer.Option(None, "--ch", help="Load audio onto this project channel"),
    project: Path = typer.Option(Path("project.audx"), "--project", "-p", help="Project file for audio loads"),
    name: str | None = typer.Option(None, "--name", "-n", help="Track name for audio loads"),
) -> None:
    """Load a project, or load an audio file into a project channel."""
    if ch is not None:
        if not project.exists():
            typer.echo(f"Project not found: {project}", err=True)
            raise typer.Exit(1)
        loaded_project = Project.load(project)
        rel_path = loaded_project.add_stem(project, path, channel=ch, name=name)
        loaded_project.save(project)
        typer.echo(f"  ✓ loaded {rel_path} onto ch {ch} in {project}")
        return

    loaded = _load_project(path)
    typer.echo(f"Loaded '{loaded.name}'")
    typer.echo(f"BPM: {loaded.bpm}")
    typer.echo(f"Patterns: {', '.join(p['name'] for p in loaded.patterns) or 'none'}")


@app.command()
def play() -> None:
    """Start audio playback in this process."""
    engine = init_engine()
    get_pattern_engine().start()
    engine.start()
    typer.echo("Playing. Press Ctrl-C to stop.")
    try:
        while True:
            import time

            time.sleep(0.25)
    except KeyboardInterrupt:
        engine.stop()
        get_pattern_engine().stop()
        typer.echo("Stopped.")


@app.command()
def stop() -> None:
    """Stop audio playback in this process."""
    engine = get_engine()
    if engine is None:
        typer.echo("Engine not running.")
        return
    engine.stop()
    get_pattern_engine().stop()
    typer.echo("Stopped.")


@app.command()
def version() -> None:
    """Print version."""
    typer.echo(f"audx {__version__}")


@pattern_app.command("create")
def pattern_create(
    name: str = typer.Argument(..., help="Pattern name"),
    dsl: str = typer.Argument(..., help="Pattern DSL, e.g. 'kick 4/4'"),
) -> None:
    """Create a pattern in the current process and print its parsed steps."""
    pattern = Pattern(name=name, dsl=dsl, length_beats=4)
    try:
        pattern.parse_dsl()
    except Exception as exc:
        typer.echo(f"DSL parse error: {exc}", err=True)
        raise typer.Exit(1) from exc
    get_pattern_engine().set_bpm(DEFAULT_BPM)
    get_pattern_engine().add_pattern(pattern)
    typer.echo(f"Pattern '{name}' created ({len(pattern.steps)} steps)")
    for step in pattern.steps:
        typer.echo(f"  beat {step.beat:.2f}: {step.sample} vel={step.velocity:.2f} ch={step.channel}")


@pattern_app.command("list")
def pattern_list() -> None:
    """List patterns in the current process."""
    engine = get_pattern_engine()
    if not engine.patterns:
        typer.echo("No patterns defined in this process.")
        return
    for name, pattern in engine.patterns.items():
        typer.echo(f"{name}: {pattern.dsl} ({len(pattern.steps)} steps)")


@pattern_app.command("delete")
def pattern_delete(name: str) -> None:
    """Delete a pattern from the current process."""
    deleted = get_pattern_engine().remove_pattern(name)
    typer.echo(f"Deleted {name}" if deleted else f"Pattern not found: {name}")


def _dsl_with_channel(dsl: str, channel: int) -> str:
    if re.search(r"\|\s*(?:ch|channel)\s+", dsl):
        return dsl
    return f"{dsl} | channel {channel}"


def _pattern_for_channel(channel: int) -> Pattern | None:
    for name, pattern in get_pattern_engine().patterns.items():
        if name == f"ch{channel}" or pattern.channel == channel or any(step.channel == channel for step in pattern.steps):
            return pattern
    return None


def _source_for_pattern(pattern: Pattern) -> str:
    if pattern.steps:
        return pattern.steps[0].sample
    if "[" in pattern.dsl:
        source = pattern.dsl.split("[", 1)[0].split("|", 1)[0].strip()
        if source:
            parts = source.split()
            return parts[-1] if parts else pattern.name
    return pattern.name


def _grid_from_pattern(pattern: Pattern, cells: int = 16) -> list[str]:
    grid = ["0"] * cells
    for step in pattern.steps:
        index = round((step.beat % pattern.length_beats) / pattern.length_beats * cells)
        if 0 <= index < cells:
            grid[index] = "1"
    return grid


@pattern_app.command("set")
def pattern_set(
    channel: int = typer.Argument(..., help="Channel index"),
    dsl: str = typer.Argument(..., help="Pattern DSL line"),
) -> None:
    """Replace a channel's DSL line (spec §06)."""
    pattern = Pattern(name=f"ch{channel}", dsl=_dsl_with_channel(dsl, channel), length_beats=4, channel=channel)
    try:
        pattern.parse_dsl()
    except Exception as exc:
        typer.echo(f"DSL parse error: {exc}", err=True)
        raise typer.Exit(1) from exc
    get_pattern_engine().add_pattern(pattern)
    typer.echo(f"  ✓ ch {channel} pattern set ({len(pattern.steps)} steps)")


@pattern_app.command("step")
def pattern_step(
    channel: int = typer.Argument(..., help="Channel index"),
    step: int = typer.Argument(..., help="1-based step number"),
    state: str | None = typer.Argument(None, help="on | off; omitted toggles"),
) -> None:
    """Toggle or set a single step in a channel pattern (spec §06)."""
    pattern = _pattern_for_channel(channel)
    if pattern is None:
        typer.echo(f"No pattern on ch {channel}. Use `audx pattern set {channel} \"kick [0000]\"` first.", err=True)
        raise typer.Exit(1)
    grid = _grid_from_pattern(pattern, cells=16)
    if "[" in pattern.dsl and "]" in pattern.dsl:
        inner = pattern.dsl.split("[", 1)[1].split("]", 1)[0]
        cells = [char for char in inner if char in {"0", "1", ".", "x", "X", "-"}]
        if cells:
            grid = ["1" if char.lower() in {"1", "x"} else "0" for char in cells]

    index = step - 1
    if index < 0 or index >= len(grid):
        typer.echo(f"Step {step} outside 1..{len(grid)}", err=True)
        raise typer.Exit(1)

    if state is None:
        grid[index] = "0" if grid[index] == "1" else "1"
    elif state.lower() in {"on", "1", "true", "yes"}:
        grid[index] = "1"
    elif state.lower() in {"off", "0", "false", "no"}:
        grid[index] = "0"
    else:
        typer.echo("State must be on or off.", err=True)
        raise typer.Exit(1)

    source = _source_for_pattern(pattern)
    pattern.dsl = _dsl_with_channel(f"{source} [{''.join(grid)}]", channel)
    pattern.parse_dsl()
    typer.echo(f"  ✓ ch {channel} step {step} {grid[index] == '1'}")


# Backwards-compatible flat command names from the earlier sprint.
@app.command("pattern-create")
def pattern_create_flat(name: str, dsl: str) -> None:
    pattern_create(name, dsl)


@app.command("patterns-list")
def pattern_list_flat() -> None:
    pattern_list()


@samples_app.command("index")
def samples_index(
    directory: Path = typer.Argument(..., help="Directory to index"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive"),
) -> None:
    """Index a sample directory."""
    library = SampleLibrary(directory)
    result = library.build_index(recursive=recursive)
    typer.echo(f"Indexed {len(result)} samples under {directory}")


@samples_app.command("list")
def samples_list(
    query: str = typer.Option("", "--query", "-q", help="Search filter"),
    limit: int = typer.Option(20, "--limit", "-l"),
) -> None:
    """List indexed samples."""
    library = SampleLibrary(SAMPLES_DIR)
    results = library.search(query=query, limit=limit)
    if not results:
        typer.echo("No samples found.")
        return
    for sample in results:
        typer.echo(f"{sample['name']} ({sample['duration']:.1f}s) tags={sample['tags']}")


# Backwards-compatible flat names.
@app.command("samples-index")
def samples_index_flat(directory: Path, recursive: bool = typer.Option(True, "--recursive/--no-recursive")) -> None:
    samples_index(directory, recursive)


@app.command("samples-list")
def samples_list_flat(query: str = "", limit: int = 20) -> None:
    samples_list(query=query, limit=limit)


@projects_app.command("list")
def projects_list() -> None:
    """List saved project files."""
    projects = list_projects()
    if not projects:
        typer.echo("No projects found.")
        return
    for project in projects:
        typer.echo(f"{project.name} ({project.stat().st_size / 1024:.1f} KB)")


@app.command("projects-list")
def projects_list_flat() -> None:
    projects_list()


@app.command("render")
def render_pattern(
    dsl: str = typer.Argument(..., help="Pattern DSL to render"),
    output: Path = typer.Option(Path("render.wav"), "--output", "-o", help="Output WAV path"),
    sample: Path = typer.Option(..., "--sample", help="Sample file to trigger"),
    bpm: float = typer.Option(128.0, "--bpm", help="BPM"),
    bars: int = typer.Option(4, "--bars", help="Number of bars"),
    stems: bool = typer.Option(False, "--stems", help="Render each pattern to its own WAV"),
    variations: int = typer.Option(0, "--variations", help="Render N stochastic variations"),
) -> None:
    """Render a single pattern to WAV offline.

    With ``--variations N`` renders N copies suffixed ``_v01.wav``..``_vNN.wav``.
    With ``--stems`` writes one file per active in-process pattern.
    """
    from audx.arrangement import Arrangement, render_arrangement

    library = SampleLibrary(sample.parent)
    library.build_index(recursive=False)

    if stems:
        engine = get_pattern_engine()
        if not engine.patterns:
            typer.echo("No patterns in current process. Run `audx pattern create ...` first.", err=True)
            raise typer.Exit(1)
        out_dir = output.parent / "stems" if output.parent.exists() else Path("renders/stems")
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, pat in engine.patterns.items():
            arrangement = Arrangement(bpm=bpm)
            arrangement.add(pat, start_bar=0, bars=bars)
            target = out_dir / f"{name}.wav"
            render_arrangement(arrangement, library, target)
            typer.echo(f"  ✓ {target}")
        return

    if variations and variations > 0:
        for i in range(1, variations + 1):
            pat = Pattern(name=sample.stem, dsl=dsl)
            pat.parse_dsl()
            arrangement = Arrangement(bpm=bpm)
            arrangement.add(pat, start_bar=0, bars=bars)
            target = output.with_name(f"{output.stem}_v{i:02d}{output.suffix}")
            render_arrangement(arrangement, library, target)
            typer.echo(f"  ✓ {target}")
        return

    pattern = Pattern(name=sample.stem, dsl=dsl)
    pattern.parse_dsl()
    arrangement = Arrangement(bpm=bpm)
    arrangement.add(pattern, start_bar=0, bars=bars)
    path = render_arrangement(arrangement, library, output)
    typer.echo(f"Rendered {path}")


@app.command("render-project")
def render_project_command(
    project: Path = typer.Argument(..., help="Project .audx file"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output WAV path"),
    bars: int = typer.Option(4, "--bars", help="Number of bars to render"),
) -> None:
    """Render a saved .audx project to a stereo WAV."""
    if not project.exists():
        typer.echo(f"Project not found: {project}", err=True)
        raise typer.Exit(1)
    from audx.arrangement import render_project

    loaded = Project.load(project)
    target = output or project.parent / "renders" / f"{loaded.name}.wav"
    path = render_project(project, target, bars=bars)
    typer.echo(f"Rendered project to {path}")


@app.command("diff")
def diff_command(
    a: Path = typer.Argument(..., help="First .audx project file"),
    b: Path = typer.Argument(..., help="Second .audx project file"),
) -> None:
    """Print a human-readable diff between two project snapshots (spec §11)."""
    if not a.exists() or not b.exists():
        typer.echo("Both project files must exist.", err=True)
        raise typer.Exit(1)
    lines = diff_projects(a, b)
    if not lines:
        typer.echo("No differences.")
        return
    for line in lines:
        typer.echo(line)


@app.command("finish")
def finish_command(
    project: Path = typer.Argument(..., help="Project .audx file"),
    profile: str | None = typer.Option(None, "--profile", help="house | ukg | custom"),
    platform: str | None = typer.Option(None, "--platform", help="spotify | apple | bandcamp | club"),
    loudness: str | None = typer.Option(None, "--loudness", help="streaming | club | bandcamp"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Print finisher command without running"),
) -> None:
    """Open finish mode: render + master via sadact-finisher (spec §12)."""
    if not project.exists():
        typer.echo(f"Project not found: {project}", err=True)
        raise typer.Exit(1)
    proj = Project.load(project)
    finisher = {**proj.finisher}
    if profile:
        finisher["profile"] = profile
    if platform:
        finisher["platform"] = platform
    if loudness:
        finisher["loudness"] = loudness

    typer.echo(f"  audx · finish mode  ·  {proj.name}")
    typer.echo(f"  profile: {finisher.get('profile')}  platform: {finisher.get('platform')}  loudness: {finisher.get('loudness')}")

    cmd = [
        "finisher", "process",
        "--profile", str(finisher.get("profile", "house")),
        "--platform", str(finisher.get("platform", "spotify")),
        "--loudness", str(finisher.get("loudness", "streaming")),
    ]
    if finisher.get("use_stems"):
        cmd.append("--use-stems")
    if finisher.get("reference"):
        cmd.extend(["--use-reference", str(finisher["reference"])])

    if dry_run:
        typer.echo("  $ " + " ".join(cmd))
        return

    from audx.sadact import SadactClient

    client = SadactClient()
    status_check = client.status()
    if not status_check.available:
        typer.echo(f"  ✗ finisher unavailable: {status_check.detail}", err=True)
        typer.echo("    Start sadact-finisher locally (default http://localhost:5742).")
        raise typer.Exit(1)
    typer.echo(f"  ✓ finisher available: {status_check.detail[:80]}")

    # Render → bundle → POST. Renders the in-process pattern engine; expects
    # the caller to have loaded the project (via `audx load` or watch).
    from audx.arrangement import Arrangement, render_arrangement

    project.parent.mkdir(parents=True, exist_ok=True)
    proj.apply_to_engine()
    pattern_engine = get_pattern_engine()
    if not pattern_engine.patterns:
        typer.echo("  · no patterns in project; nothing to finish.", err=True)
        raise typer.Exit(1)
    stems_dir = project.parent / "renders" / "stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    library = SampleLibrary(SAMPLES_DIR)
    library.build_index(recursive=True)
    for name, pat in pattern_engine.patterns.items():
        arrangement = Arrangement(bpm=proj.bpm)
        arrangement.add(pat, start_bar=0, bars=4)
        render_arrangement(arrangement, library, stems_dir / f"{name}.wav")

    import shutil

    zip_path = project.parent / "renders" / f"{proj.name}-stems.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", stems_dir)
    typer.echo(f"  ✓ bundled {zip_path}")
    try:
        out = client.process(
            zip_path,
            output_path=project.parent / "renders" / f"{proj.name}-mastered.zip",
            preset=str(finisher.get("loudness", "streaming")),
        )
        typer.echo(f"  ✓ mastered → {out}")
    except Exception as exc:
        typer.echo(f"  ✗ master failed: {exc}", err=True)
        raise typer.Exit(1) from exc


@track_app.command("add")
def track_add(
    name: str = typer.Argument(..., help="Track / pattern name"),
    dsl: str = typer.Argument("", help="Optional DSL line"),
    channel: int = typer.Option(0, "--channel", "-c"),
) -> None:
    """Add a track to the in-process pattern engine."""
    if not dsl:
        dsl = f"{name} 4/4 | channel {channel}"
    pattern = Pattern(name=name, dsl=dsl, length_beats=4, channel=channel)
    pattern.parse_dsl()
    get_pattern_engine().add_pattern(pattern)
    typer.echo(f"  ✓ track '{name}' added on channel {channel} ({len(pattern.steps)} steps)")


@track_app.command("rm")
def track_rm(name: str = typer.Argument(..., help="Track / pattern name")) -> None:
    """Remove a track from the in-process pattern engine."""
    removed = get_pattern_engine().remove_pattern(name)
    typer.echo(f"  ✓ removed '{name}'" if removed else f"  · not found: {name}")


@mix_app.command("set")
def mix_set(
    channel: int = typer.Argument(..., help="Channel index (0-based)"),
    param: str = typer.Argument(..., help="gain | mute"),
    value: str = typer.Argument(..., help="dB for gain, on/off for mute"),
) -> None:
    """Set a mixer parameter (spec §06)."""
    engine = get_engine() or init_engine()
    if param == "gain":
        try:
            db = float(value)
        except ValueError as exc:
            typer.echo(f"Invalid dB value: {value}", err=True)
            raise typer.Exit(1) from exc
        engine.channel_gain[channel] = 10 ** (db / 20)
        typer.echo(f"  ✓ ch {channel} gain {db:+.1f} dB")
    elif param == "mute":
        engine.channel_mute[channel] = value.lower() in {"on", "1", "true", "yes"}
        typer.echo(f"  ✓ ch {channel} mute {engine.channel_mute[channel]}")
    else:
        typer.echo(f"Unknown param: {param}. Use gain or mute.", err=True)
        raise typer.Exit(1)


@app.command("mute")
def mute_channel(channel: int = typer.Argument(..., help="Channel index (0-based)")) -> None:
    """Toggle mute on a channel."""
    engine = get_engine() or init_engine()
    engine.channel_mute[channel] = not bool(engine.channel_mute[channel])
    typer.echo(f"  ✓ ch {channel} mute {bool(engine.channel_mute[channel])}")


@samples_app.command("scan")
def samples_scan() -> None:
    """Scan standard hard drive directories for usable audio samples."""
    from rich.table import Table

    library = SampleLibrary(SAMPLES_DIR)
    results = library.auto_scan_hd()

    table = Table(title="audx sample scanner results", show_header=True)
    table.add_column("Category / Tag", style="cyan")
    table.add_column("Samples Found", style="green")

    table.add_row("Total Indexed", str(results.get("total", 0)))
    top_tags = ["kick", "snare", "hat", "hihat", "clap", "bass", "synth", "perc", "vocal", "909", "808"]
    for tag in top_tags:
        if tag in results:
            table.add_row(tag, str(results[tag]))

    console.print(table)


@push2_app.command("lights")
def push2_lights() -> None:
    """Test and control Push 2 pad LED lighting grid."""
    from rich.panel import Panel

    from audx.push2 import find_push2_output, light_push2_pads

    out_port = find_push2_output()
    lit = light_push2_pads(out_port)

    grid = "\n".join(["[green]●[/green] [red]●[/red] [blue]●[/blue] [yellow]●[/yellow] [cyan]●[/cyan] [magenta]●[/magenta] [white]●[/white] [green]●[/green]" for _ in range(8)])
    console.print(Panel(grid, title="Push 2 LED Pad Grid Test", border_style="cyan"))

    if lit:
        console.print(f"  [bold green]✓ Push 2 pad LED light pattern sent to '{out_port}'![/bold green]")
    else:
        console.print("  [yellow]· Push 2 hardware not detected on MIDI output ports.[/yellow]")
        console.print("    [dim]Tip: Connect Push 2 USB & ensure Ableton Live is closed (or releasing MIDI ports).[/dim]")


@push2_app.command("display")
def push2_display() -> None:
    """Test and render live frame to Push 2 onboard 960x160 color LCD screen."""
    from audx.push2 import Push2DisplayDriver, render_push2_display_frame

    driver = Push2DisplayDriver()
    frame = render_push2_display_frame(bpm=128.0, genre="TECHNO", channel_levels=[0.9, 0.7, 0.5, 0.8])
    sent = driver.send_frame(frame)

    if sent:
        console.print("[bold green]✓ Push 2 onboard LCD display frame sent over USB (960x160 BGR565 XOR 0xE73C)![/bold green]")
    else:
        console.print("[yellow]· Push 2 USB display interface not active.[/yellow]")
        console.print("  [dim]Tip: Connect Push 2 USB power/cable. Install libusb if needed: `brew install libusb`.[/dim]")


@song_app.command("render")
def song_render(
    project: Path = typer.Argument(..., help="Path to .audx project file"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output WAV path"),
    bars: int = typer.Option(4, "--bars", help="Number of bars to render"),
) -> None:
    """Render a song / project to WAV (alias for `render-project`)."""
    render_project_command(project=project, output=output, bars=bars)


@samples_app.command("search")
def samples_search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(20, "--limit", "-l"),
) -> None:
    """Fuzzy-search the sample index (spec §06: `audx stems search`)."""
    library = SampleLibrary(SAMPLES_DIR)
    results = library.search(query=query, limit=limit)
    if not results:
        typer.echo("No samples found.")
        return
    for sample in results:
        typer.echo(f"{sample['path']}  ({sample['duration']:.1f}s)")


@plugin_app.command("scan")
def plugins_scan() -> None:
    """Scan AU/VST/VST3 plugin directories. Discovery only, no hosting yet."""
    from audx.plugins import scan_plugins

    plugins = scan_plugins()
    if not plugins:
        typer.echo("No plugins found.")
        return
    for plugin in plugins:
        typer.echo(f"{plugin.kind}\t{plugin.name}\t{plugin.path}")


@push2_app.command("map")
def push2_map() -> None:
    """Print the default Push 2 MIDI mapping scaffold."""
    from audx.push2 import list_push2_map

    for control in list_push2_map():
        typer.echo(f"{control.name}\t{control.midi_type}\t{control.number}\t{control.description}")


@heartmula_app.command("status")
def heartmula_status() -> None:
    """Check whether the local Heartmula bridge is available."""
    from audx.heartmula import status

    check = status()
    typer.echo(f"{'available' if check.available else 'unavailable'}: {check.reason}")


@heartmula_app.command("generate")
def heartmula_generate(
    prompt: str,
    output: Path = typer.Option(Path("heartmula-output.wav"), "--output", "-o"),
    bpm: int = typer.Option(128, "--bpm"),
    bars: int = typer.Option(4, "--bars"),
) -> None:
    """Generate a stem via local heartlib if available."""
    from audx.heartmula import generate

    path = generate(prompt, output, bpm=bpm, bars=bars)
    typer.echo(f"Generated {path}")


@sadact_app.command("status")
def sadact_status(base_url: str = typer.Option("http://localhost:5742", "--url")) -> None:
    """Check sadact-finisher HTTP bridge."""
    from audx.sadact import SadactClient

    check = SadactClient(base_url=base_url).status()
    typer.echo(f"{'available' if check.available else 'unavailable'}: {check.detail}")


@sadact_app.command("process")
def sadact_process(
    stems_zip: Path,
    output: Path | None = typer.Option(None, "--output", "-o"),
    preset: str = typer.Option("loudness-14", "--preset"),
    base_url: str = typer.Option("http://localhost:5742", "--url"),
) -> None:
    """Send stems zip to sadact-finisher and write mastered output."""
    from audx.sadact import SadactClient

    path = SadactClient(base_url=base_url).process(stems_zip, output_path=output, preset=preset)
    typer.echo(f"Wrote {path}")


@daemon_app.command("serve")
def daemon_serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(5744, "--port"),
) -> None:
    """Run the minimal audxd local daemon."""
    from audx.daemon import run_daemon

    run_daemon(host=host, port=port)


@daemon_app.command("status")
def daemon_status() -> None:
    """Check audxd status."""
    from audx.daemon_client import daemon_status as get_status

    typer.echo(get_status())


@daemon_app.command("pattern")
def daemon_pattern(name: str, dsl: str) -> None:
    """Add a pattern to audxd."""
    from audx.daemon_client import daemon_add_pattern

    typer.echo(daemon_add_pattern(name, dsl))


@daemon_app.command("save")
def daemon_save(path: str, name: str | None = None) -> None:
    """Save audxd state to a project file."""
    from audx.daemon_client import daemon_save as save_state

    typer.echo(save_state(path, name=name))



# ── AI commands ───────────────────────────────────────────────────────────────

@ai_app.command("pattern")
def ai_pattern(
    description: str = typer.Argument(..., help="Text description, e.g. 'dark halftime techno groove'"),
    channel: int = typer.Option(0, "--channel", "-c", help="Mixer channel to assign"),
) -> None:
    """Generate a pattern from a text description using local AI or heuristics."""
    from audx.ai.generator import generate, pattern_to_grid

    result = generate(description, channel=channel)
    print(f"Engine: {result.engine}")
    print(f"Instrument: {result.params.instrument}")
    print(f"Subdivision: {result.params.subdivision}")
    print(f"Swing: {result.params.swing}")
    print(f"Density: {result.params.density:.2f}")
    print()
    print(f"Grid (16): {pattern_to_grid(result.pattern, 16)}")
    print(f"Hit count: {len(result.pattern.steps)}")
@ai_app.command("similar")
def ai_similar(
    sample: Path = typer.Argument(..., help="Path to a sample to use as query"),
    samples_dir: Path = typer.Option(None, "--dir", "-d", help="Sample library directory"),
    limit: int = typer.Option(5, "--limit", "-l"),
) -> None:
    """Find the K most similar samples in the local library."""
    try:
        from audx.ai.similarity import EmbeddingIndex, compute_embedding
    except ImportError as err:
        console.print("[red]librosa not installed. uv sync --extra ai[/red]")
        raise typer.Exit(1) from err

    dir_ = samples_dir or Path(os.getenv("AUDX_SAMPLES", str(SAMPLES_DIR)))
    index = EmbeddingIndex.load_or_build(dir_)
    query_vec = compute_embedding(sample)
    matches = index.search(query_vec, limit=limit)
    console.print(f"Top {len(matches)} matches for [cyan]{sample.name}[/cyan]:")
    for m in matches:
        console.print(f"  {m.path}  [dim](distance {m.distance:.3f})[/dim]")

@ai_app.command("tag")
def ai_tag(
    sample: Path = typer.Argument(..., help="Sample file to tag"),
) -> None:
    """Auto-tag a sample with timbre descriptors."""
    try:
        from audx.ai.tagger import tag_sample
    except ImportError as err:
        console.print("[red]librosa not installed. uv sync --extra ai[/red]")
        raise typer.Exit(1) from err

    tags = tag_sample(sample)
    console.print(f"Tags: [cyan]{', '.join(tags)}[/cyan]")

@ai_app.command("groove")
def ai_groove(
    reference: Path = typer.Argument(..., help="Reference loop to analyse"),
    instrument: str = typer.Option("hh", "--inst", "-i"),
) -> None:
    """Extract groove (BPM, swing, velocity) from a reference loop."""
    try:
        from audx.ai.groove import extract_groove, groove_to_dsl
    except ImportError as err:
        console.print("[red]librosa not installed. uv sync --extra ai[/red]")
        raise typer.Exit(1) from err

    profile = extract_groove(reference)
    if profile is None:
        console.print("[red]Groove extraction failed (librosa missing?)[/red]")
        raise typer.Exit(1)

    console.print(f"BPM: [green]{profile.bpm:.1f}[/green]")
    console.print(f"Swing: {profile.swing:.2f}")
    console.print()
    console.print(groove_to_dsl(profile, instrument=instrument))

# ── fork / export / watch / serve ──────────────────────────────────────────────


@app.command("fork")
def fork_command(
    source: Path = typer.Argument(..., help="Existing .audx file or project folder"),
    new_name: str = typer.Argument(..., help="Name of the new fork"),
) -> None:
    """Cheap branching: copy a project to a new name (spec §06)."""
    import shutil

    src_path = source / "project.audx" if source.is_dir() else source
    if not src_path.exists():
        typer.echo(f"Source not found: {src_path}", err=True)
        raise typer.Exit(1)
    dst_dir = (source.parent if source.is_dir() else src_path.parent) / new_name
    if dst_dir.exists():
        typer.echo(f"Destination already exists: {dst_dir}", err=True)
        raise typer.Exit(1)
    if source.is_dir():
        shutil.copytree(source, dst_dir)
    else:
        dst_dir.mkdir(parents=True)
        shutil.copy2(src_path, dst_dir / "project.audx")
    proj = Project.load(dst_dir / "project.audx")
    proj.name = new_name
    proj.save(dst_dir / "project.audx")
    typer.echo(f"  ✓ forked to {dst_dir}/project.audx")


@export_app.command("midi")
def export_midi(
    output: Path = typer.Argument(..., help="Output .mid path"),
    bars: int = typer.Option(1, "--bars"),
    bpm: float = typer.Option(128.0, "--bpm"),
) -> None:
    """Export current in-process patterns to a Standard MIDI File."""
    from audx.midi_export import patterns_to_midi

    engine = get_pattern_engine()
    if not engine.patterns:
        typer.echo("No patterns in current process. Run `audx pattern create ...` first.", err=True)
        raise typer.Exit(1)
    path = patterns_to_midi(engine.patterns, output, bpm=bpm, bars=bars)
    typer.echo(f"  ✓ wrote {path}")


@export_app.command("als")
@export_app.command("ableton")
def export_als(
    project: Path = typer.Argument(..., help="Path to .audx project file"),
    output: Path = typer.Option(Path("session.als"), "--output", "-o", help="Output .als file path"),
) -> None:
    """Export project to a native Ableton Live Set (.als) file."""
    from audx.als_export import project_to_als

    if not project.exists():
        typer.echo(f"Project file not found: {project}", err=True)
        raise typer.Exit(1)

    loaded = Project.load(project)
    written = project_to_als(loaded, output)
    typer.echo(f"  ✓ exported Ableton Live Set to {written}")


@app.command("watch")
def watch_command(
    project: Path = typer.Argument(..., help="project.audx to watch"),
    once: bool = typer.Option(False, "--once", help="Apply once and exit (testing)"),
) -> None:
    """Watch a project file and hot-reload its patterns when it changes."""
    if not project.exists():
        typer.echo(f"Project not found: {project}", err=True)
        raise typer.Exit(1)

    def _on_change(path: Path, loaded: Project) -> None:
        loaded.apply_to_engine()
        typer.echo(f"  ↻ reloaded {path} ({len(loaded.patterns)} patterns)")

    _on_change(project, Project.load(project))
    if once:
        return
    from audx.watch import FileWatcher

    watcher = FileWatcher(project, _on_change)
    watcher.start()
    typer.echo(f"  ✓ watching {project} (Ctrl-C to stop)")
    try:
        import time

        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        watcher.stop()


@app.command("serve")
def serve_command(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8080, "--port"),
) -> None:
    """Serve the localhost monitor and playable browser UI (spec §11)."""
    from audx.web import serve

    typer.echo(f"  ✓ audx browser on http://{host}:{port}/app  (Ctrl-C to stop)")
    serve(host=host, port=port)


@app.command("voice")
def voice_command() -> None:
    """Probe on-device voice control (spec §11)."""
    from audx.voice import status

    check = status()
    typer.echo(f"  {'✓' if check.available else '·'} voice: {check.detail}")
    if not check.available:
        typer.echo("    Stub: install whispercpp + a wake-word engine to enable.")


@app.command("rec")
def rec_command(
    channel: int = typer.Option(0, "--ch", help="Record onto this channel"),
    length: int = typer.Option(1, "--length", help="Bars to record"),
    calibrate: bool = typer.Option(False, "--calibrate", help="Measure round-trip latency and store"),
) -> None:
    """Record live audio onto a channel, or run latency calibration (spec §11)."""
    if calibrate:
        from audx.calibration import measure_impulse, save

        latency = measure_impulse()
        path = save(latency, notes=f"channel {channel}")
        typer.echo(f"  ✓ latency {latency:.2f} ms (saved to {path})")
        return
    typer.echo(f"  · rec stub: would record {length} bars onto ch {channel}")
    typer.echo("    Live recording requires sounddevice input wiring -- on the v0.5 milestone.")


# ── midi / macros / slots / ai key ────────────────────────────────────────────


@midi_app.command("out")
def midi_out_command(
    port: str = typer.Argument("", help="MIDI output port name. Leave empty to list"),
    bpm: float = typer.Option(128.0, "--bpm"),
) -> None:
    """Send MIDI clock to an output port (spec §11)."""
    from audx.midi import MidiClock, list_outputs

    if not port:
        names = list_outputs()
        if not names:
            typer.echo("No MIDI output ports.")
            return
        typer.echo("Available MIDI outputs:")
        for name in names:
            typer.echo(f"  · {name}")
        return
    clock = MidiClock(bpm=bpm, port_name=port)
    clock.start()
    typer.echo(f"  ✓ MIDI clock @ {bpm} BPM on '{port}'  (Ctrl-C to stop)")
    try:
        import time

        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        clock.stop()


@midi_app.command("rec")
def midi_rec_command(
    name: str = typer.Argument("rec", help="Name of the captured pattern"),
    bars: int = typer.Option(1, "--bars"),
    bpm: float = typer.Option(128.0, "--bpm"),
    channel: int = typer.Option(0, "--ch"),
    no_quant: bool = typer.Option(False, "--no-quant", help="Preserve human timing"),
    port: str = typer.Option("", "--port", help="MIDI input port; first available if empty"),
) -> None:
    """Record incoming MIDI as a pattern (spec §11)."""
    from audx.midi import notes_to_pattern, record_midi

    notes = record_midi(port_name=port or None, bars=bars, bpm=bpm, quantize=None if no_quant else 16)
    pattern = notes_to_pattern(notes, name=name, channel=channel)
    get_pattern_engine().add_pattern(pattern)
    typer.echo(f"  ✓ captured {len(notes)} note(s) → pattern '{name}' ({len(pattern.steps)} steps)")


@midi_app.command("list")
def midi_list_command() -> None:
    """List MIDI input and output ports."""
    from audx.midi import list_inputs, list_outputs

    typer.echo("inputs:")
    for name in list_inputs() or ["  (none)"]:
        typer.echo(f"  · {name}")
    typer.echo("outputs:")
    for name in list_outputs() or ["  (none)"]:
        typer.echo(f"  · {name}")


_macro_store_cache: dict[str, list[str]] = {}


@macro_app.command("record")
def macro_record(register: str, keys: str) -> None:
    """Save a macro into ``register`` (spec §11). KEYS is a space-separated list."""
    _macro_store_cache[register[:1].lower()] = keys.split()
    typer.echo(f"  ✓ macro '{register[:1]}' stored ({len(keys.split())} keys)")


@macro_app.command("replay")
def macro_replay(register: str) -> None:
    """Print the keys stored in ``register`` (TUI replays them)."""
    keys = _macro_store_cache.get(register[:1].lower(), [])
    if not keys:
        typer.echo(f"  · register '{register[:1]}' empty")
        return
    typer.echo(" ".join(keys))


@macro_app.command("list")
def macro_list() -> None:
    """List stored macro registers."""
    if not _macro_store_cache:
        typer.echo("(no macros)")
        return
    for name, keys in _macro_store_cache.items():
        typer.echo(f"@{name}  {' '.join(keys)}")


@slot_app.command("set")
def slot_set(
    project: Path = typer.Argument(..., help="project.audx"),
    slot: str = typer.Argument(..., help="Slot name: A | B | C | D"),
) -> None:
    """Copy the current ``patterns`` array into a slot (spec §11 chaining)."""
    if not project.exists():
        typer.echo(f"Project not found: {project}", err=True)
        raise typer.Exit(1)
    proj = Project.load(project)
    slot_key = slot.upper()[:1]
    if slot_key not in {"A", "B", "C", "D"}:
        typer.echo(f"Invalid slot '{slot}'. Use A, B, C, or D.", err=True)
        raise typer.Exit(1)
    proj.slots[slot_key] = list(proj.patterns)
    proj.save(project)
    typer.echo(f"  ✓ slot {slot_key} ← {len(proj.patterns)} patterns")


@slot_app.command("next")
def slot_next(
    project: Path = typer.Argument(..., help="project.audx"),
    slot: str = typer.Argument(..., help="Slot name: A | B | C | D"),
) -> None:
    """Queue a slot to become active (spec §11 ``:next B``)."""
    if not project.exists():
        typer.echo(f"Project not found: {project}", err=True)
        raise typer.Exit(1)
    proj = Project.load(project)
    slot_key = slot.upper()[:1]
    if slot_key not in proj.slots:
        typer.echo(f"Slot {slot_key} not defined yet. Set it first with `audx slot set ...`.", err=True)
        raise typer.Exit(1)
    proj.active_slot = slot_key
    proj.patterns = list(proj.slots[slot_key])
    proj.save(project)
    typer.echo(f"  ✓ active slot now {slot_key} ({len(proj.patterns)} patterns)")


@slot_app.command("list")
def slot_list(project: Path = typer.Argument(..., help="project.audx")) -> None:
    """List slot contents."""
    proj = Project.load(project)
    for key in ("A", "B", "C", "D"):
        marker = "▸" if key == proj.active_slot else " "
        count = len(proj.slots.get(key, []))
        typer.echo(f"  {marker} {key}  {count} patterns")


@ai_app.command("key")
def ai_key(
    secret: str = typer.Argument("", help="API key; leave empty to print the current backend"),
    account: str = typer.Option("anthropic", "--account"),
    show: bool = typer.Option(False, "--show", help="Print the stored value"),
) -> None:
    """Store or rotate the AI API key in the OS keychain (spec §06)."""
    from audx.keystore import get_key, set_key

    if show:
        value = get_key(account)
        typer.echo(value if value else "(not set)")
        return
    if not secret:
        existing = get_key(account)
        typer.echo(f"  · account '{account}': {'set' if existing else 'not set'}")
        return
    backend = set_key(account, secret)
    typer.echo(f"  ✓ stored '{account}' via {backend}")


if __name__ == "__main__":
    app()
