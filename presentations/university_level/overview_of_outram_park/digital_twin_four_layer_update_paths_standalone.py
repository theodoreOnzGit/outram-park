#!/usr/bin/env python3
"""
Full-spectrum digital twin architecture diagram.

Usage:
    python digital_twin_four_layer_update_paths_standalone.py
    python digital_twin_four_layer_update_paths_standalone.py --screenshot path/to/screenshot.png
    python digital_twin_four_layer_update_paths_standalone.py --output my_diagram.png
    python digital_twin_four_layer_update_paths_standalone.py --dpi 150

Dependencies:
    pip install matplotlib pillow
"""

from pathlib import Path
import argparse
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from PIL import Image


# The figure is 24x16 inches over a 24x16 data space, so one data unit is
# exactly one inch (72 points). Text heights can therefore be converted with
# fontsize / PT_PER_UNIT.
PT_PER_UNIT = 72.0

# Horizontal padding between a panel border and its text.
PAD = 0.18


class TextFitter:
    """Measures, wraps and shrinks text to fit a given width in data units.

    The original layout placed every string at a fixed font size and trusted
    it to fit; several titles and body lines silently overflowed into their
    neighbours. Measuring against the real renderer removes the guesswork.
    """

    # Tokens that should never start a line -- they are glued to the word
    # before them so a break happens after the separator, not before it.
    GLUE = {"•", "|", "/"}

    def __init__(self, ax, renderer):
        self.ax = ax
        self.renderer = renderer
        self._cache = {}

    def width(self, text, fontsize, weight="normal"):
        key = (text, fontsize, weight)

        if key not in self._cache:
            probe = self.ax.text(
                0, 0, text,
                fontsize=fontsize,
                fontweight=weight,
            )
            bbox = probe.get_window_extent(renderer=self.renderer)
            probe.remove()

            self._cache[key] = bbox.transformed(
                self.ax.transData.inverted()
            ).width

        return self._cache[key]

    def wrap(self, text, max_width, fontsize, weight="normal"):
        """Greedy word wrap to max_width, preserving explicit newlines."""
        lines = []

        for paragraph in text.split("\n"):
            tokens = []

            for token in paragraph.split():
                if token in self.GLUE and tokens:
                    tokens[-1] += " " + token
                else:
                    tokens.append(token)

            if not tokens:
                lines.append("")
                continue

            line = tokens[0]

            for token in tokens[1:]:
                candidate = line + " " + token

                if self.width(candidate, fontsize, weight) > max_width:
                    lines.append(line)
                    line = token
                else:
                    line = candidate

            lines.append(line)

        return "\n".join(lines)

    def fit(
        self, text, max_width, fontsize,
        weight="bold", min_fontsize=8.0, max_lines=2,
    ):
        """Wrap a heading, shrinking only if wrapping alone cannot fit it.

        Returns (wrapped_text, fontsize).
        """
        size = fontsize

        while size >= min_fontsize:
            wrapped = self.wrap(text, max_width, size, weight)
            lines = wrapped.split("\n")

            fits = len(lines) <= max_lines and all(
                self.width(line, size, weight) <= max_width for line in lines
            )

            if fits:
                return wrapped, size

            size -= 0.5

        return self.wrap(text, max_width, min_fontsize, weight), min_fontsize


def line_height(fontsize, linespacing):
    return fontsize / PT_PER_UNIT * linespacing




# ----------------------------------------------------------------------
# Layout grid
#
# All geometry lives here so the stack can be re-proportioned without
# hunting for coordinates in the drawing code. Vertical bands are listed
# top-down; every panel and arrow below derives from these.
# ----------------------------------------------------------------------

LEFT = 0.35
RIGHT = 23.60
GUTTER = 0.45

# Relative widths of the four layer 2 stages left of the spine. Actual
# widths are solved from these against GUTTER, so changing the spacing
# re-flows the row instead of needing every x re-derived by hand.
STAGE_WEIGHTS = (3.05, 6.35, 3.05, 3.05)

# Layer 1 — physical feedback & learning.
L1_Y, L1_H = 12.20, 1.95

# The asset bridge sits in its own band between layer 1 and layer 2: it is
# the cyber-physical boundary, not a modelling stage inside either layer.
BRIDGE_Y, BRIDGE_H = 10.00, 1.55

# Layer 2 — digital twin engineering & operation.
L2_Y, L2_H = 5.80, 3.55

# Layer 3 — trust, safety & digital infrastructure.
L3_Y, L3_H = 3.45, 1.75

# Layer 4 — implementation reference, held to ~15% of the canvas so the
# footnotes stay visually secondary to the architecture above.
L4_Y, L4_H = 0.45, 2.40

# Right-hand column shared by the real asset, the bridge and the twin, so
# the three form one vertical cyber-physical spine.
SPINE_X, SPINE_W = 16.85, RIGHT - 16.85


def build_diagram(
    screenshot_path: Path,
    output_png: Path,
    output_svg: Path,
    dpi: int = 270,
) -> None:
    fig, ax = plt.subplots(figsize=(24, 16), facecolor="#181818")
    ax.set_facecolor("#181818")
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 16)
    ax.axis("off")

    fig.canvas.draw()
    fitter = TextFitter(ax, fig.canvas.get_renderer())

    FG = "#e0e0e0"
    MUTED = "#a0a0a0"
    GRID = "#3b3b3b"
    BLUE = "#2f9bd3"
    HOT = "#c97b4b"
    CYAN = "#54b6d8"
    PANEL = "#202020"

    # Panel geometry is recorded here so arrows can be anchored to named
    # edges instead of repeating hardcoded coordinates.
    rects = {}

    # Vertical fit is still governed by the fixed layout grid, so report
    # rather than silently clip when a panel's body outgrows its box.
    overflows = []

    def panel(
        name, x, y, w, h, title, subtitle="", body="",
        edge=GRID, title_color=FG, fs=9.0, title_lines=2
    ):
        rects[name] = (x, y, w, h)

        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h,
                boxstyle="round,pad=0.10,rounding_size=0.10",
                fc=PANEL, ec=edge, lw=1.3
            )
        )

        inner = w - 2 * PAD
        cursor = y + h - 0.30

        title_text, title_size = fitter.fit(
            title, inner, 12.5, max_lines=title_lines
        )

        ax.text(
            x + PAD, cursor, title_text,
            color=title_color, fontsize=title_size,
            fontweight="bold", va="center", linespacing=1.15
        )

        cursor -= title_text.count("\n") * line_height(title_size, 1.15)

        if subtitle:
            subtitle_text = fitter.wrap(subtitle, inner, 9.0)
            cursor -= 0.37

            ax.text(
                x + PAD, cursor, subtitle_text,
                color=MUTED, fontsize=9.0, va="center", linespacing=1.15
            )

            cursor -= subtitle_text.count("\n") * line_height(9.0, 1.15)

        if body:
            body_text = fitter.wrap(body, inner, fs)
            body_top = cursor - 0.30

            ax.text(
                x + PAD, body_top, body_text,
                color=FG, fontsize=fs, va="top", linespacing=1.28
            )

            n_lines = body_text.count("\n") + 1
            bottom = body_top - n_lines * line_height(fs, 1.28)

            if bottom < y + 0.10:
                overflows.append(
                    f"{name}: body overruns the panel by "
                    f"{y + 0.10 - bottom:.2f} units"
                )

    # -- Named anchor points on registered panels ----------------------

    def left_of(name, frac=0.5):
        x, y, w, h = rects[name]
        return (x, y + h * frac)

    def right_of(name, frac=0.5):
        x, y, w, h = rects[name]
        return (x + w, y + h * frac)

    def top_of(name, frac=0.5):
        x, y, w, h = rects[name]
        return (x + w * frac, y + h)

    def bottom_of(name, frac=0.5):
        x, y, w, h = rects[name]
        return (x + w * frac, y)

    def arrow(
        a, b, label=None, color=FG, lw=1.6,
        ls="-", style="-|>", connectionstyle="arc3,rad=0",
        label_gap=0.12, label_frac=0.5, label_side="right",
    ):
        ax.add_patch(
            FancyArrowPatch(
                a, b,
                arrowstyle=style,
                mutation_scale=14,
                lw=lw,
                color=color,
                linestyle=ls,
                connectionstyle=connectionstyle,
            )
        )

        if not label:
            return

        mx = a[0] + (b[0] - a[0]) * label_frac
        my = a[1] + (b[1] - a[1]) * label_frac

        # Vertical runs get their label beside the shaft; everything else
        # sits above it. This replaces the manual per-arrow nudges the
        # earlier version needed to dodge collisions.
        if abs(b[0] - a[0]) < abs(b[1] - a[1]):
            on_left = label_side == "left"

            ax.text(
                mx - label_gap if on_left else mx + label_gap, my, label,
                color=color, fontsize=8.2,
                ha="right" if on_left else "left",
                va="center", linespacing=1.25,
                bbox=dict(fc="#181818", ec="none", pad=1.2),
            )
        else:
            ax.text(
                mx, my + label_gap, label,
                color=color, fontsize=8.2,
                ha="center", va="bottom", linespacing=1.25,
                bbox=dict(fc="#181818", ec="none", pad=1.2),
            )

    def layer_label(y, text):
        ax.text(
            LEFT, y, text,
            color=MUTED, fontsize=9, fontweight="bold",
        )

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    ax.add_patch(Rectangle((0, 15.25), 24, 0.75, fc="#202020", ec=GRID, lw=1))

    ax.text(
        0.32, 15.66,
        "FULL-SPECTRUM DIGITAL TWIN ARCHITECTURE",
        color=FG, fontsize=20, fontweight="bold", va="center",
    )

    ax.text(
        0.32, 14.96,
        "Four-layer management view — operational data drives learning, "
        "online model updates and first-principles recalibration",
        color=MUTED, fontsize=11.5,
    )

    # ------------------------------------------------------------------
    # LAYER 1 — Physical feedback & learning
    # ------------------------------------------------------------------

    layer_label(L1_Y + L1_H + 0.27, "LAYER 1 — PHYSICAL FEEDBACK & LEARNING")

    panel(
        "model_improvement",
        LEFT, L1_Y, SPINE_X - GUTTER - LEFT, L1_H,
        "MODEL IMPROVEMENT & UPDATES",
        "Evidence-driven model lifecycle",
        "Operational / historian evidence  •  Envelope excursions / "
        "reduced-confidence flags  •  Experimental benchmarks  •  "
        "Calibration & data assimilation  •  Model discrepancy\n"
        "Parameter updating  •  High-fidelity model updating  •  "
        "Surrogate retraining / online updating  •  Revalidation",
        edge=BLUE, title_color=BLUE, fs=8.6,
    )

    panel(
        "real_asset",
        SPINE_X, L1_Y, SPINE_W, L1_H,
        "REAL ASSET",
        "Physical plant / experiment / process",
        "SENSING  Sensors / measurements  •  PLC / DCS / DAQ  •  "
        "historian / alarms / events\n"
        "ACTUATION  Actuators / controllers  •  pumps / valves / rods / "
        "heaters  •  trips / interlocks",
        edge=GRID, title_color=FG, fs=8.6,
    )

    # ------------------------------------------------------------------
    # Cyber-physical boundary, between layer 1 and layer 2
    # ------------------------------------------------------------------

    # The interface is the concept management needs; OPC UA is named as
    # one implementation of it rather than as the thing itself.
    panel(
        "bridge",
        SPINE_X, BRIDGE_Y, SPINE_W, BRIDGE_H,
        "CYBER-PHYSICAL INTERFACE",
        "Bidirectional asset bridge  —  e.g. OPC UA",
        "Telemetry / events  •  Commands / setpoints  •  Address space / "
        "subscriptions  •  Security / methods",
        edge=CYAN, title_color=CYAN, fs=8.4,
    )

    # ------------------------------------------------------------------
    # LAYER 2 — Digital twin engineering & operation
    # ------------------------------------------------------------------

    layer_label(L2_Y + L2_H + 0.27, "LAYER 2 — DIGITAL TWIN ENGINEERING & OPERATION")

    # Stages share the span left of the spine, separated by GUTTER.
    stage_span = (SPINE_X - GUTTER) - LEFT
    stage_scale = (
        stage_span - GUTTER * (len(STAGE_WEIGHTS) - 1)
    ) / sum(STAGE_WEIGHTS)

    stages = [
        (
            "physical_definition",
            "PHYSICAL DEFINITION", "Problem setup",
            "Geometry\n"
            "Materials / nuclear data\n"
            "Mesh / topology\n"
            "Initial conditions\n"
            "Boundary conditions\n"
            "Operating scenarios\n"
            "Uncertainty ranges",
            BLUE, 8.8,
        ),
        (
            "high_fidelity",
            "HIGH-FIDELITY MULTIPHYSICS", "Physics authority",
            "NEUTRONICS  Monte Carlo • transport • diffusion / SP3 • "
            "kinetics • depletion • decay heat\n"
            "THERMAL HYDRAULICS  System TH • CFD • multiphase • "
            "boiling • natural circulation\n"
            "FUEL / STRUCTURES  thermomechanics • swelling • creep • "
            "fission gas • cladding failure\n"
            "CHEMISTRY / MATERIALS  thermochemistry • reaction kinetics • "
            "phase equilibria • oxidation • corrosion • species transport\n"
            "PROCESS / UNIT OPERATIONS  distillation columns • crackers / "
            "reformers • catalytic reactors • heat exchangers • "
            "absorbers / separators • flowsheet convergence\n"
            "SEVERE ACCIDENTS  heat-up • melt • relocation • debris • "
            "corium • MCCI • H₂ • FP / aerosol • containment",
            HOT, 7.9,
        ),
        (
            "campaigns",
            "SIMULATION CAMPAIGNS", "Offline exploration",
            "Design points\n"
            "Normal operation\n"
            "Transients\n"
            "Accident sequences\n"
            "DOE / UQ sampling\n"
            "Sensitivity / validation",
            CYAN, 8.8,
        ),
        (
            "rom",
            "SURROGATE / ROM", "Regime-aware fast models",
            "Operational ROM\n"
            "Transient ROM\n"
            "Accident / safety ROM\n"
            "Validated operating envelope\n"
            "Model selection\n"
            "Fast UQ / model confidence",
            HOT, 8.8,
        ),
    ]

    stage_x = LEFT

    for weight, stage in zip(STAGE_WEIGHTS, stages):
        name, title, subtitle, body, edge, fs = stage
        stage_w = weight * stage_scale

        panel(name, stage_x, L2_Y, stage_w, L2_H, title, subtitle, body,
              edge=edge, title_color=edge, fs=fs)

        stage_x += stage_w + GUTTER

    # Real-time digital twin, carrying the simulator screenshot.
    rects["real_time_twin"] = (SPINE_X, L2_Y, SPINE_W, L2_H)

    ax.add_patch(
        FancyBboxPatch(
            (SPINE_X, L2_Y), SPINE_W, L2_H,
            boxstyle="round,pad=0.10,rounding_size=0.10",
            fc=PANEL, ec=BLUE, lw=1.5,
        )
    )

    dt_caption = "example implementation"
    dt_caption_w = fitter.width(dt_caption, 8.0)

    # One line only -- wrapping would push the title into the screenshot.
    dt_title, dt_title_size = fitter.fit(
        "REAL-TIME DIGITAL TWIN",
        SPINE_W - 2 * PAD - dt_caption_w - 0.40,
        12.5,
        max_lines=1,
    )

    ax.text(
        SPINE_X + PAD, L2_Y + L2_H - 0.30, dt_title,
        color=BLUE, fontsize=dt_title_size, fontweight="bold", va="center",
    )

    ax.text(
        SPINE_X + SPINE_W - PAD, L2_Y + L2_H - 0.30, dt_caption,
        color=MUTED, fontsize=8.0, ha="right", va="center",
    )

    dt_subtitle = fitter.wrap(
        "State estimation • prediction • diagnostics • "
        "model validity monitoring • decision support",
        SPINE_W - 2 * PAD, 9.0,
    )

    ax.text(
        SPINE_X + PAD, L2_Y + L2_H - 0.67, dt_subtitle,
        color=MUTED, fontsize=9.0, va="center", linespacing=1.15,
    )

    with Image.open(screenshot_path) as img:
        img.load()
        aspect = img.size[0] / img.size[1]

        available_w = SPINE_W - 2 * PAD
        available_h = L2_H - 1.15 - dt_subtitle.count("\n") * line_height(
            9.0, 1.15
        )

        draw_w = min(available_w, available_h * aspect)
        draw_h = draw_w / aspect

        image_x = SPINE_X + (SPINE_W - draw_w) / 2
        image_y = L2_Y + 0.13 + (available_h - draw_h) / 2

        ax.imshow(
            img,
            extent=(image_x, image_x + draw_w, image_y, image_y + draw_h),
            aspect="auto", zorder=3,
        )

    # imshow resets the data limits, so restore the fixed drawing frame.
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 16)

    # Main engineering flow, anchored to panel edges.
    for src, dst in [
        ("physical_definition", "high_fidelity"),
        ("high_fidelity", "campaigns"),
        ("campaigns", "rom"),
        ("rom", "real_time_twin"),
    ]:
        arrow(right_of(src), left_of(dst))

    # ------------------------------------------------------------------
    # Cyber-physical spine: twin <-> bridge <-> real asset
    # ------------------------------------------------------------------

    spine_x = SPINE_X + SPINE_W * 0.55

    arrow(
        (spine_x, L2_Y + L2_H),
        (spine_x, BRIDGE_Y),
        label="data / control",
        color=CYAN, lw=2.0, style="<|-|>", label_side="left",
    )

    # Telemetry rises from the asset (downward on the page); commands run
    # the other way. Labelled in page direction so they cannot be misread.
    arrow(
        (spine_x, BRIDGE_Y + BRIDGE_H),
        (spine_x, L1_Y),
        label="TELEMETRY ↓\nCOMMANDS ↑",
        color=CYAN, lw=2.2, style="<|-|>", label_side="left",
    )

    # ------------------------------------------------------------------
    # Model update paths
    # ------------------------------------------------------------------

    # The real asset feeds model improvement through the bridge: the run
    # leaves the bridge's left edge and turns up into layer 1, staying
    # clear of the asset box and of the two update risers.
    feedback_x = bottom_of("model_improvement", 0.92)[0]
    bridge_mid_y = BRIDGE_Y + BRIDGE_H / 2

    arrow(
        (SPINE_X, bridge_mid_y),
        (feedback_x, bridge_mid_y),
        label="operational data / events /\nenvelope excursions",
        color=BLUE, lw=1.7, ls="--", label_frac=0.62,
    )

    arrow(
        (feedback_x, bridge_mid_y),
        (feedback_x, L1_Y),
        color=BLUE, lw=1.7, ls="--",
    )

    # Model improvement -> surrogate: retraining and online adaptation.
    rom_x = rects["rom"][0] + rects["rom"][2] * 0.20

    arrow(
        (rom_x, L1_Y),
        (rom_x, L2_Y + L2_H),
        label="ad-hoc improvements /\nonline updating",
        color=CYAN, lw=1.7, ls="--", label_side="left",
    )

    # Model improvement -> high-fidelity: first-principles recalibration.
    hf_x = top_of("high_fidelity")[0]

    arrow(
        (hf_x, L1_Y),
        (hf_x, L2_Y + L2_H),
        label="reset / update\nmodel parameters",
        color=HOT, lw=1.7, ls="--",
    )

    # ------------------------------------------------------------------
    # LAYER 3 — Trust, safety & digital infrastructure
    # ------------------------------------------------------------------

    layer_label(L3_Y + L3_H + 0.27, "LAYER 3 — TRUST, SAFETY & DIGITAL INFRASTRUCTURE")

    half = (RIGHT - LEFT - GUTTER) / 2

    panel(
        "assurance",
        LEFT, L3_Y, half, L3_H,
        "ASSURANCE & SAFETY BASIS",
        "Why the twin can be trusted",
        "Code & solution verification  •  Experimental validation  •  "
        "Uncertainty quantification  •  Provenance / versioning\n"
        "Reproducibility  •  Validated operating envelopes  •  "
        "Model validity monitoring  •  Safety margins  •  "
        "Acceptance criteria",
        edge=HOT, title_color=HOT, fs=8.6,
    )

    panel(
        "infrastructure",
        RIGHT - half, L3_Y, half, L3_H,
        "DATA / ORCHESTRATION / COMPUTE",
        "How the models operate as one system",
        "Shared geometry / region identity  •  Field mapping / multiphysics "
        "coupling  •  Workflow orchestration / restart\n"
        "Parallel / HPC execution  •  Data lineage / historian  •  "
        "Visualization / reporting  •  Twin lifecycle management",
        edge=CYAN, title_color=CYAN, fs=8.6,
    )

    # Short vertical foundation links only -- these read as "rests on",
    # not as flow between stages.
    for x, src, dst, color in [
        (hf_x, "high_fidelity", "assurance", HOT),
        (spine_x, "real_time_twin", "infrastructure", CYAN),
    ]:
        arrow(
            (x, rects[src][1]),
            (x, rects[dst][1] + rects[dst][3]),
            color=color, lw=1.1, ls="--",
        )

    # ------------------------------------------------------------------
    # LAYER 4 — Implementation reference
    # ------------------------------------------------------------------

    layer_label(L4_Y + L4_H + 0.25, "LAYER 4 — IMPLEMENTATION REFERENCE")

    ax.add_patch(
        Rectangle((LEFT, L4_Y), RIGHT - LEFT, L4_H, fc="#1d1d1d", ec=GRID, lw=1)
    )

    split = 12.60

    ax.plot([split, split], [L4_Y + 0.18, L4_Y + L4_H - 0.18], color=GRID, lw=1)

    heading_y = L4_Y + L4_H - 0.30
    note_y = heading_y - 0.27
    row_y = note_y - 0.26

    ax.text(
        LEFT + 0.27, heading_y, "OUTRAM PARK CAPABILITY MAPPING",
        color=FG, fontsize=10.0, fontweight="bold", va="center",
    )

    ax.text(
        LEFT + 0.27, note_y,
        "Implementation example; crate names are not conceptual layers.",
        color=MUTED, fontsize=7.4, fontstyle="italic", va="center",
    )

    foot = [
        ("Definition / data",
         "cfmesh • foam_mesh • blender • NJOY • steam tables • CoolProp"),
        ("Neutronics / kinetics",
         "outram_mc_libs • foam_appbuilder • teh_o_prke"),
        ("TH / fuel / depletion",
         "tampines • foam_multiphase • bedok • boon_lay • OFFBEAT • ONIX"),
        ("Chemistry / process eng.",
         "Thermochimica • PFLOTRAN • DWSIM • LIGGGHTS • Moltres"),
        ("Orchestration / HPC",
         "digital_twin_engine • outram_park_mpi • foam_basic_lib"),
        ("Knowledge / provenance",
         "Kovan • discovery • literature • metrics • semantics • codegen"),
    ]

    label_x = LEFT + 0.33
    value_x = label_x + max(
        fitter.width(label, 7.2, "bold") for label, _ in foot
    ) + 0.25

    yy = row_y

    for label, text in foot:
        ax.text(label_x, yy, label, color=CYAN, fontsize=7.2,
                fontweight="bold", va="top")
        ax.text(value_x, yy, text, color=MUTED, fontsize=6.9, va="top")
        yy -= 0.23

    ax.text(
        label_x, yy - 0.02,
        "Target architecture; severe-accident capability is composed from "
        "multiple coupled physics capabilities.",
        color=HOT, fontsize=6.6, fontstyle="italic", va="top",
    )

    # Management glossary.
    gx = split + 0.35

    ax.text(gx, heading_y, "MANAGEMENT GLOSSARY",
            color=FG, fontsize=10.0, fontweight="bold", va="center")

    ax.text(gx, note_y, "Acronyms used above",
            color=MUTED, fontsize=7.4, fontstyle="italic", va="center")

    glossary = [
        ("BC", "Boundary Condition"),
        ("CFD", "Computational Fluid Dynamics"),
        ("DAQ", "Data Acquisition"),
        ("DCS", "Distributed Control System"),
        ("DOE", "Design of Experiments"),
        ("FP", "Fission Products"),
        ("HPC", "High-Performance Computing"),
        ("H₂", "Hydrogen"),
        ("MCCI", "Molten Core–Concrete Interaction"),
        ("OOD", "Out-of-Distribution"),
        ("OPC UA", "Open Platform Communications Unified Architecture"),
        ("PLC", "Programmable Logic Controller"),
        ("ROM", "Reduced-Order Model"),
        ("TH", "Thermal Hydraulics"),
        ("UQ", "Uncertainty Quantification"),
        ("V&V", "Verification and Validation"),
    ]

    # Two columns of eight, each indented past its own widest acronym.
    per_column = 8
    column_w = (RIGHT - 0.30 - gx) / 2

    for index, (acronym, meaning) in enumerate(glossary):
        column, row = divmod(index, per_column)
        cx = gx + column * column_w

        if row == 0:
            entries = glossary[index:index + per_column]
            meaning_x = cx + max(
                fitter.width(a, 7.0, "bold") for a, _ in entries
            ) + 0.20

        ax.text(cx, row_y - row * 0.20, acronym,
                color=CYAN, fontsize=7.0, fontweight="bold", va="top")

        ax.text(meaning_x, row_y - row * 0.20,
                fitter.wrap(meaning, cx + column_w - meaning_x - 0.10, 6.4),
                color=FG, fontsize=6.4, va="top", linespacing=1.2)

    for message in overflows:
        print(f"layout warning: {message}", file=sys.stderr)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_svg.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_png, dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.savefig(output_svg, bbox_inches="tight",
                facecolor=fig.get_facecolor())

    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Generate the four-layer digital twin architecture diagram."
    )

    parser.add_argument(
        "--screenshot", type=Path, default=Path("htgr_simulator.png"),
        help="Path to the HTGR/digital-twin simulator screenshot.",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("digital_twin_four_layer_update_paths.png"),
        help="Output PNG path.",
    )
    parser.add_argument(
        "--svg", type=Path, default=None,
        help="Optional SVG output path. Defaults to the PNG name with .svg.",
    )
    parser.add_argument(
        "--dpi", type=int, default=270,
        help="PNG resolution (default: 270).",
    )

    args = parser.parse_args()

    if not args.screenshot.exists():
        raise SystemExit(
            f"Screenshot not found: {args.screenshot}\n\n"
            "Either rename your screenshot to 'htgr_simulator.png' or run:\n"
            "  python digital_twin_four_layer_update_paths_standalone.py "
            "--screenshot path/to/your/screenshot.png"
        )

    build_diagram(
        screenshot_path=args.screenshot,
        output_png=args.output,
        output_svg=args.svg or args.output.with_suffix(".svg"),
        dpi=args.dpi,
    )

    print(f"Wrote: {args.output}")
    print(f"Wrote: {args.svg or args.output.with_suffix('.svg')}")


if __name__ == "__main__":
    main()
