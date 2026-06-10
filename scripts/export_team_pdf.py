from __future__ import annotations

import argparse
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Iterable, List, Tuple

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".tmp" / "matplotlib"))

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image

from common.dashboard_app import build_space_frame, fix_mojibake, load_all_team_reports, load_reports, sprint_num


PAGE = "#0b111e"
PANEL = "#111827"
PANEL_2 = "#162033"
TEXT = "#f8fafc"
MUTED = "#a8b3c7"
GRID = "#344052"
RED = "#ff4b4b"
BLUE = "#7cc7ff"
GREEN = "#22c55e"
ORANGE = "#f59e0b"
PURPLE = "#8b5cf6"

SPACE_ORDER = [
    "SPACE-W (Satisfaction & Well-Being)",
    "SPACE-P (Performance)",
    "SPACE-C (Communication & Collaboration)",
    "SPACE-E (Efficiency & Flow)",
]
SPACE_SHORT = {
    "SPACE-W (Satisfaction & Well-Being)": "SPACE-W\nSatisfaction",
    "SPACE-P (Performance)": "SPACE-P\nPerformance",
    "SPACE-C (Communication & Collaboration)": "SPACE-C\nCommunication",
    "SPACE-E (Efficiency & Flow)": "SPACE-E\nEfficiency",
}
SPACE_TAG = {
    "SPACE-W (Satisfaction & Well-Being)": "W",
    "SPACE-P (Performance)": "P",
    "SPACE-C (Communication & Collaboration)": "C",
    "SPACE-E (Efficiency & Flow)": "E",
}
SPACE_COLORS = [RED, ORANGE, BLUE, "#18c48f"]
ASSETS_DIR = ROOT / "assets"

QUESTION_DIMENSION_RULES = [
    (r"satisfacao|frustracao|desanimo|tensoes|conflitos|motivacao|fatores externos|bem-estar", "SPACE-W (Satisfaction & Well-Being)"),
    (r"cumprimento|cumprir|comprometeu a realizar|qualidade|formacao|engenharia de software|conhecimentos", "SPACE-P (Performance)"),
    (r"comunicacao|colaboracao|informacoes|transparencia|intermediarios|participacao|solucao|proposta", "SPACE-C (Communication & Collaboration)"),
    (r"foco|bloqueios|tarefas nao planejadas|distribuicao|distribuidas|fluxo", "SPACE-E (Efficiency & Flow)"),
]

DIMENSION_SHORT = {
    "SPACE-W (Satisfaction & Well-Being)": "SPACE-W · Satisfaction & Well-Being",
    "SPACE-P (Performance)": "SPACE-P · Performance",
    "SPACE-C (Communication & Collaboration)": "SPACE-C · Communication & Collaboration",
    "SPACE-E (Efficiency & Flow)": "SPACE-E · Efficiency & Flow",
}


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.facecolor": PANEL,
            "figure.facecolor": PAGE,
            "savefig.facecolor": PAGE,
            "axes.labelcolor": TEXT,
            "xtick.color": TEXT,
            "ytick.color": TEXT,
            "text.color": TEXT,
            "axes.edgecolor": GRID,
        }
    )


def read_team_metadata(team_dir: Path) -> dict[str, str]:
    metadata = {"Professor(a)": "n/d", "Período": "n/d", "Alunos": "n/d"}
    readme = team_dir / "README.md"
    if not readme.exists():
        return metadata
    text = fix_mojibake(readme.read_text(encoding="utf-8", errors="replace"))
    for line in text.splitlines():
        match = re.match(r"^-\s*(Professor\(a\)|Período|Alunos):\s*(.+)$", line.strip())
        if match:
            metadata[match.group(1)] = match.group(2).strip()
    return metadata


def wrap_lines(text: str, width: int) -> List[str]:
    return textwrap.wrap(str(text), width=width, replace_whitespace=False, drop_whitespace=True) or [""]


def add_wrapped(
    fig,
    x: float,
    y: float,
    text: str,
    width: int = 90,
    size: float = 10,
    color: str = MUTED,
    weight: str = "normal",
    line_height: float = 0.026,
) -> float:
    for line in wrap_lines(text, width):
        fig.text(x, y, line, fontsize=size, color=color, weight=weight, va="top")
        y -= line_height
    return y


def page(title: str, subtitle: str | None = None):
    fig = plt.figure(figsize=(8.27, 11.69), facecolor=PAGE)
    fig.text(0.07, 0.925, title, fontsize=25, weight="bold", color=TEXT, va="top")
    if subtitle:
        fig.text(0.07, 0.885, subtitle, fontsize=11, color=MUTED, va="top")
    return fig


def render_title_cover(pdf: PdfPages, team_label: str, selected_report) -> None:
    fig = plt.figure(figsize=(8.27, 11.69), facecolor=PAGE)
    fig.text(0.07, 0.78, "Relatório NES SPACE", fontsize=31, weight="bold", color=TEXT, va="top")
    fig.text(0.07, 0.715, f"{team_label.upper()} · {selected_report.sprint} · Survey Alunos", fontsize=16, color=MUTED, va="top")
    fig.text(0.07, 0.62, "Relatório para compartilhamento com a equipe", fontsize=18, weight="bold", color=TEXT)
    add_wrapped(
        fig,
        0.07,
        0.575,
        "Material de apoio para conversa sobre produtividade, comunicação, fluxo de trabalho, satisfação e melhoria contínua.",
        width=78,
        size=11,
        color=MUTED,
    )
    add_logo(fig, ASSETS_DIR / "ufms_original.png", (0.62, 0.765, 0.20, 0.075))
    add_logo(fig, ASSETS_DIR / "facom_light_transparent.png", (0.84, 0.745, 0.10, 0.105))
    fig.text(0.07, 0.10, "A leitura deve ser contextual e não representa ranking entre equipes.", fontsize=9.5, color=MUTED)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def cropped_logo(path: Path) -> Image.Image | None:
    if not path.exists():
        return None
    image = Image.open(path).convert("RGBA")
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    return image


def add_logo(fig, path: Path, box: tuple[float, float, float, float]) -> None:
    image = cropped_logo(path)
    if image is None:
        return
    ax = fig.add_axes(list(box), zorder=5)
    ax.imshow(image)
    ax.axis("off")


def rounded_panel(fig, x: float, y: float, w: float, h: float, color: str = PANEL, edge: str = "#243047"):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        transform=fig.transFigure,
        facecolor=color,
        edgecolor=edge,
        linewidth=1.1,
        zorder=0,
    )
    fig.add_artist(patch)
    return patch


def metric_card(fig, x: float, y: float, w: float, h: float, label: str, value: str, accent: str) -> None:
    rounded_panel(fig, x, y, w, h, PANEL_2)
    fig.add_artist(Rectangle((x, y), 0.008, h, transform=fig.transFigure, color=accent, ec=accent))
    fig.text(x + 0.025, y + h - 0.028, label.upper(), fontsize=8.5, color=MUTED, weight="bold", va="top")
    fig.text(x + 0.025, y + 0.025, value, fontsize=22, color=TEXT, weight="bold", va="bottom")


def note_panel(fig, x: float, y: float, w: float, h: float, text: str) -> None:
    rounded_panel(fig, x, y, w, h, "#101827", "#243047")
    add_wrapped(fig, x + 0.018, y + h - 0.018, text, width=108, size=8.2, color=MUTED, line_height=0.019)


def score_text(value: float | None) -> str:
    return "n/d" if value is None or pd.isna(value) else f"{value:.2f}"


def comparison_frame(team_dir: Path, team_label: str, selected_sprint: str) -> pd.DataFrame:
    all_reports = load_all_team_reports(team_dir)
    all_agg = build_space_frame(all_reports)
    if all_agg.empty:
        return pd.DataFrame()
    sprint_df = all_agg[all_agg["Sprint"] == selected_sprint].copy()
    current_team = team_label.upper()
    current = (
        sprint_df[sprint_df["Equipe"] == current_team]
        .groupby("Dimensão", as_index=False)["Nota"]
        .mean()
        .rename(columns={"Nota": "Equipe atual"})
    )
    mean = (
        sprint_df.groupby("Dimensão", as_index=False)["Nota"]
        .mean()
        .rename(columns={"Nota": "Média das equipes"})
    )
    merged = current.merge(mean, on="Dimensão", how="outer")
    merged["Ordem"] = merged["Dimensão"].map(lambda value: SPACE_ORDER.index(value) if value in SPACE_ORDER else 99)
    return merged.sort_values(["Ordem", "Dimensão"])


def team_space_history(reports) -> pd.DataFrame:
    rows = []
    for report in reports:
        for dim, score in report.space.items():
            if dim in SPACE_ORDER:
                rows.append({"Sprint": report.sprint, "Sprint Nº": sprint_num(report.sprint), "Dimensão": dim, "Nota": score})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["Ordem"] = df["Dimensão"].map(lambda value: SPACE_ORDER.index(value) if value in SPACE_ORDER else 99)
    return df.sort_values(["Sprint Nº", "Ordem"])


def clean_question_label(label: str) -> tuple[str, bool]:
    label = fix_mojibake(label)
    inverse = "(item inverso)" in label.lower()
    label = re.sub(r"\s*\(item inverso\)\s*$", "", label, flags=re.I).strip()
    label = re.sub(r"^\d+(?:\.\d+)?\.\s*", "", label).strip()
    label = re.sub(r"\s*Marque apenas uma opção\.?", "", label, flags=re.I).strip()
    label = re.sub(r"\s*Escolha uma alternativa:?\s*", "", label, flags=re.I).strip()
    label = label.replace(" ?", "?")

    bracket = re.search(r"\[(.+?)\]\s*$", label)
    if "Avaliação Geral da Satisfação" in label and bracket:
        label = f"Satisfação: {bracket.group(1)}"
    if "(Se respondeu \"Sim\")" in label:
        label = "Discussão da solução com o time"
    if len(label) > 150:
        label = label[:147].rstrip() + "..."
    return label, inverse


def infer_question_dimension(label: str) -> str:
    normalized = fix_mojibake(label).lower()
    normalized = normalized.translate(str.maketrans("áàãâéêíóôõúç", "aaaaeeiooouc"))
    for pattern, dimension in QUESTION_DIMENSION_RULES:
        if re.search(pattern, normalized):
            return DIMENSION_SHORT[dimension]
    return "Dimensão não identificada"


def card(fig, x: float, y: float, w: float, h: float, accent: str, title: str, note: str, score: float) -> None:
    rounded_panel(fig, x, y, w, h, PANEL_2, "#253248")
    fig.add_artist(Rectangle((x, y), 0.008, h, transform=fig.transFigure, color=accent, ec=accent))
    fig.text(x + 0.026, y + h - 0.026, title, fontsize=8.8, color=TEXT, weight="bold", va="top")
    note_lines = wrap_lines(note, 96)[:2]
    note_y = y + 0.040
    for line in note_lines:
        fig.text(x + 0.026, note_y, line, fontsize=7.1, color=MUTED, va="bottom")
        note_y -= 0.014
    fig.text(x + w - 0.03, y + h / 2, f"{score:.2f}", fontsize=18, color=TEXT, weight="bold", ha="right", va="center")


def question_cards(fig, title: str, items: Iterable[Tuple[str, float]], x: float, y: float, kind: str) -> None:
    fig.text(x, y, title, fontsize=15, weight="bold", color=TEXT, va="top")
    y -= 0.055
    accent = GREEN if kind == "strength" else "#fb923c"
    for label, score in list(items)[:5]:
        clean, inverse = clean_question_label(label)
        dimension = infer_question_dimension(clean)
        if inverse and kind == "strength":
            note = f"{dimension} | Item inverso tratado: nota alta sugere menor presença do problema."
        elif inverse:
            note = f"{dimension} | Item inverso tratado: nota baixa sugere maior presença do problema."
        elif kind == "strength":
            note = f"{dimension} | Nota maior indica percepção mais positiva."
        else:
            note = f"{dimension} | Nota menor sugere ponto de atenção para conversa."
        title_text = "\n".join(wrap_lines(clean, 78)[:2])
        card(fig, x, y - 0.105, 0.86, 0.105, accent, title_text, note, score)
        y -= 0.122


def render_cover(pdf: PdfPages, team_dir: Path, team_label: str, reports, selected_report) -> None:
    metadata = read_team_metadata(team_dir)
    fig = page(f"Resumo da equipe · {team_label.upper()}", f"{selected_report.sprint} · Survey Alunos")

    fig.text(0.07, 0.80, "Relatório para compartilhamento com a equipe", fontsize=16, weight="bold", color=TEXT)
    y = 0.758
    y = add_wrapped(
        fig,
        0.07,
        y,
        "A comparação contextual usa a média das equipes apenas como referência de leitura, sem representar ranking entre times.",
        width=88,
        size=10.5,
        color=MUTED,
    )

    fig.text(0.07, 0.675, f"Professor(a): {metadata['Professor(a)']} · Período: {metadata['Período']}", fontsize=10.5, color=TEXT)
    add_wrapped(fig, 0.07, 0.646, f"Alunos: {metadata['Alunos']}", width=110, size=9.3, color=MUTED)

    space_mean = pd.Series(selected_report.space, dtype="float64").mean() if selected_report.space else None
    metric_card(fig, 0.07, 0.515, 0.25, 0.10, "Nota do Survey", score_text(selected_report.overall), RED)
    metric_card(fig, 0.375, 0.515, 0.25, 0.10, "Participação", selected_report.participation or "n/d", BLUE)
    metric_card(fig, 0.68, 0.515, 0.25, 0.10, "Média SPACE", score_text(space_mean), PURPLE)

    note_panel(
        fig,
        0.07,
        0.432,
        0.86,
        0.052,
        "Observação: a Nota do Survey é calculada pelo script a partir dos temas ponderados do questionário. "
        "A Média SPACE é uma média simples das dimensões SPACE exibidas no relatório.",
    )

    rounded_panel(fig, 0.07, 0.262, 0.86, 0.13, PANEL_2)
    fig.text(0.095, 0.365, "Relatos considerados", fontsize=12, weight="bold", color=TEXT, va="top")
    headers = ["Sprint", "Participação", "Nota do Survey"]
    x_positions = [0.11, 0.42, 0.70]
    for x, header in zip(x_positions, headers):
        fig.text(x, 0.321, header, fontsize=8.5, weight="bold", color=MUTED)
    y = 0.291
    for report in sorted(reports, key=lambda item: sprint_num(item.sprint)):
        fig.text(x_positions[0], y, report.sprint, fontsize=9, color=TEXT)
        fig.text(x_positions[1], y, report.participation or "n/d", fontsize=9, color=TEXT)
        fig.text(x_positions[2], y, score_text(report.overall), fontsize=9, color=TEXT)
        y -= 0.028

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def render_space_page(pdf: PdfPages, reports, selected_report) -> None:
    fig = page("Evolução SPACE", "Comparação da equipe entre sprints")
    hist = team_space_history(reports)

    if not hist.empty:
        ax = fig.add_axes([0.10, 0.52, 0.80, 0.31], facecolor=PANEL)
        sprint_labels = (
            hist[["Sprint", "Sprint Nº"]]
            .drop_duplicates()
            .sort_values("Sprint Nº")
        )
        start_offsets = {
            0: (-26, -22),
            1: (30, -18),
            2: (14, 16),
            3: (34, 14),
        }
        end_offsets = {
            0: (-8, -20),
            1: (-14, 18),
            2: (-32, -4),
            3: (26, 12),
        }
        for idx, dim in enumerate(SPACE_ORDER):
            part = hist[hist["Dimensão"] == dim]
            if part.empty:
                continue
            ax.plot(part["Sprint Nº"], part["Nota"], marker="o", lw=2.6, color=SPACE_COLORS[idx], label=SPACE_SHORT[dim].replace("\n", " "))
            for point_idx, (_, row) in enumerate(part.iterrows()):
                offsets = start_offsets if point_idx == 0 else end_offsets
                xytext = offsets.get(idx, (0, 12))
                ax.annotate(
                    f"{SPACE_TAG.get(dim, '')} {row['Nota']:.2f}",
                    xy=(row["Sprint Nº"], row["Nota"]),
                    xytext=xytext,
                    textcoords="offset points",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=TEXT,
                    bbox={"boxstyle": "round,pad=0.18", "fc": PANEL, "ec": "none", "alpha": 0.86},
                )
        ax.set_ylim(0, 10)
        ax.set_xlim(sprint_labels["Sprint Nº"].min() - 0.12, sprint_labels["Sprint Nº"].max() + 0.12)
        ax.set_xticks(sprint_labels["Sprint Nº"].tolist(), sprint_labels["Sprint"].tolist())
        ax.set_ylabel("Nota")
        ax.set_title("")
        ax.grid(axis="y", alpha=0.22, color=GRID)
        ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.34), ncol=2, labelcolor=TEXT)
        ax.spines[["top", "right"]].set_visible(False)

    rounded_panel(fig, 0.08, 0.22, 0.84, 0.18, PANEL_2)
    fig.text(0.105, 0.375, "Dimensões do modelo SPACE", fontsize=12.5, weight="bold", color=TEXT, va="top")
    y = 0.342
    for item in [
        "Satisfaction & Well-Being: satisfação, motivação, bem-estar e tensões percebidas.",
        "Performance: percepção de entrega, qualidade e resultado do trabalho.",
        "Activity: atividade registrada no processo; nesta versão, aparece como explicação do modelo, mas ainda não é calculada como série própria.",
        "Communication & Collaboration: comunicação, colaboração, transparência e troca de informações.",
        "Efficiency & Flow: foco, bloqueios, interrupções e fluidez do trabalho.",
    ]:
        y = add_wrapped(fig, 0.105, y, f"• {item}", width=96, size=7.8, color=MUTED, line_height=0.019)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def render_comparison_page(pdf: PdfPages, team_dir: Path, team_label: str, selected_report) -> None:
    fig = page("Comparação Contextual", f"{team_label.upper()} · {selected_report.sprint}")
    y = 0.815
    y = add_wrapped(
        fig,
        0.07,
        y,
        "Esta comparação serve apenas como referência contextual. Diferenças podem refletir participação, composição da equipe, momento da sprint e percepção dos respondentes.",
        width=95,
        size=10,
        color=MUTED,
    )
    y -= 0.02
    add_wrapped(
        fig,
        0.07,
        y,
        "O gráfico compara a equipe atual com a média das equipes na mesma sprint, separado por dimensão SPACE. Ele ajuda a identificar temas para conversa, sem representar ranking entre times.",
        width=95,
        size=9.6,
        color=MUTED,
    )

    comp = comparison_frame(team_dir, team_label, selected_report.sprint)
    if not comp.empty:
        ax = fig.add_axes([0.10, 0.255, 0.80, 0.37], facecolor=PANEL)
        x = range(len(comp))
        width = 0.34
        labels = [SPACE_SHORT.get(dim, dim) for dim in comp["Dimensão"]]
        current = comp["Equipe atual"].fillna(0).tolist()
        mean = comp["Média das equipes"].fillna(0).tolist()
        ax.bar([i - width / 2 for i in x], current, width=width, label="Equipe atual", color=RED)
        ax.bar([i + width / 2 for i in x], mean, width=width, label="Média das equipes", color=BLUE)
        ax.set_xticks(list(x), labels)
        ax.set_ylim(0, 10)
        ax.set_ylabel("Nota")
        ax.set_title("")
        ax.legend(frameon=False, loc="upper right", labelcolor=TEXT)
        ax.grid(axis="y", alpha=0.22, color=GRID)
        ax.spines[["top", "right"]].set_visible(False)
        for i, value in enumerate(current):
            ax.text(i - width / 2, value + 0.15, f"{value:.2f}", ha="center", fontsize=8, color=TEXT)
        for i, value in enumerate(mean):
            ax.text(i + width / 2, value + 0.15, f"{value:.2f}", ha="center", fontsize=8, color=TEXT)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def render_questions_pages(pdf: PdfPages, team_label: str, selected_report) -> None:
    fig = page("Pontos Fortes Percebidos", f"{team_label.upper()} · {selected_report.sprint}")
    add_wrapped(
        fig,
        0.07,
        0.82,
        "Estes itens tiveram as maiores notas normalizadas no survey. Eles ajudam a reconhecer aspectos percebidos como mais positivos pela equipe.",
        width=95,
        size=10,
        color=MUTED,
    )
    question_cards(fig, "Itens com maior pontuação", selected_report.top5, 0.07, 0.715, "strength")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    fig = page("Pontos de Atenção para Conversa", f"{team_label.upper()} · {selected_report.sprint}")
    add_wrapped(
        fig,
        0.07,
        0.82,
        "Estes itens tiveram as menores notas normalizadas no survey. Eles não devem ser lidos como diagnóstico fechado, mas como bons pontos para investigar na conversa com a equipe.",
        width=95,
        size=10,
        color=MUTED,
    )
    question_cards(fig, "Itens que merecem investigação", selected_report.bottom5, 0.07, 0.715, "attention")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def export_team_pdf(team: str, sprint: str | None, output: Path) -> Path:
    setup_style()
    team_label = team.upper()
    team_dir = ROOT / "teams" / team_label.lower()
    reports = load_reports(team_dir / "data" / "relatos", team_label)
    if not reports:
        raise SystemExit(f"Nenhum relato encontrado para {team_label}.")
    if sprint:
        selected = next((report for report in reports if report.sprint.lower() == sprint.lower()), None)
        if selected is None:
            raise SystemExit(f"Sprint '{sprint}' não encontrada para {team_label}.")
    else:
        selected = sorted(reports, key=lambda report: sprint_num(report.sprint))[-1]

    output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output) as pdf:
        render_title_cover(pdf, team_label, selected)
        render_cover(pdf, team_dir, team_label, reports, selected)
        render_space_page(pdf, reports, selected)
        render_comparison_page(pdf, team_dir, team_label, selected)
        render_questions_pages(pdf, team_label, selected)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta um relatório PDF de dashboard por equipe.")
    parser.add_argument("--team", default="T1", help="Equipe, por exemplo T1.")
    parser.add_argument("--sprint", default=None, help="Sprint opcional, por exemplo 'Sprint 1'.")
    parser.add_argument("--output", default=None, help="Caminho do PDF de saída.")
    args = parser.parse_args()

    team = args.team.upper()
    sprint_slug = re.sub(r"\W+", "_", args.sprint or "ultima").strip("_").lower()
    output = Path(args.output) if args.output else ROOT / "exports" / f"relatorio_{team}_{sprint_slug}.pdf"
    result = export_team_pdf(team, args.sprint, output)
    print(result)


if __name__ == "__main__":
    main()
