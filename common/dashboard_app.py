from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


@dataclass
class Report:
    artifact: str
    sprint: str
    team: Optional[str]
    overall: Optional[float]
    participation: Optional[str]
    space: Dict[str, float]
    themes: Dict[str, float]
    top5: List[Tuple[str, float]]
    bottom5: List[Tuple[str, float]]
    suggestions: List[str]
    source_file: str


SPACE_NAME = {
    "P": "SPACE-P (Performance)",
    "C": "SPACE-C (Communication & Collaboration)",
    "E": "SPACE-E (Efficiency & Flow)",
    "W": "SPACE-W (Satisfaction & Well-Being)",
    "S": "SPACE-W (Satisfaction & Well-Being)",
}

SPACE_PT = {
    "P": "Performance",
    "C": "Comunicação e Colaboração",
    "E": "Eficiência e Flow",
    "W": "Satisfação e Bem-Estar",
    "S": "Satisfação e Bem-Estar",
}

SPACE_ORDER = [
    SPACE_NAME["W"],
    SPACE_NAME["P"],
    SPACE_NAME["C"],
    SPACE_NAME["E"],
]

SPACE_HISTORY_LABELS = {
    SPACE_NAME["W"]: "Bem-estar",
    SPACE_NAME["P"]: "Performance",
    SPACE_NAME["C"]: "Comunicação",
    SPACE_NAME["E"]: "Fluxo",
}

QUESTION_DIMENSION_RULES = [
    (r"satisfacao|frustracao|desanimo|tensoes|conflitos|motivacao|fatores externos|bem-estar", "SPACE-W (Satisfaction & Well-Being)"),
    (r"cumprimento|cumprir|comprometeu a realizar|qualidade|formacao|engenharia de software|conhecimentos", "SPACE-P (Performance)"),
    (r"comunicacao|colaboracao|informacoes|transparencia|intermediarios|participacao|solucao|proposta", "SPACE-C (Communication & Collaboration)"),
    (r"foco|bloqueios|tarefas nao planejadas|distribuicao|distribuidas|fluxo", "SPACE-E (Efficiency & Flow)"),
]

INVERSE_HINTS = [
    "dificuldades de comunicacao",
    "intermediarios",
    "ocultacao",
    "informacoes importantes foram ocultadas",
    "conflitos de transparencia",
    "tarefas nao planejadas",
    "bloqueios",
    "impedido de avancar",
    "frustracao",
    "desanimo",
    "tensoes",
    "conflitos que prejudicaram",
    "fatores externos",
]

MOJIBAKE_DASH_EN = "\u00e2\u20ac\u201c"
MOJIBAKE_DASH_EM = "\u00e2\u20ac\u201d"
MOJIBAKE_CAO = "\u00c3\u00a7\u00c3\u00a3o"
MOJIBAKE_MARKERS = ("\u00c3", "\u00e2\u20ac", "\u00c2")
DASH_PATTERN = "|".join(re.escape(value) for value in ["-", "–", "—", MOJIBAKE_DASH_EN, MOJIBAKE_DASH_EM])

PAT = {
    "title": re.compile(
        rf"^#\s*Relato\s*(?:{DASH_PATTERN})\s*Sprint\s*(?P<sprint>\d+)\s*(?:{DASH_PATTERN})\s*(?P<artifact>.+)$",
        re.I,
    ),
    "overall": re.compile(r"Nota(?:\s+do\s+Survey)?[^:\n]*\*{0,2}\s*:\s*(?P<score>[\d,.]+)", re.I),
    "team": re.compile(r"Equipe\*\*:\s*(?P<team>T\d+)", re.I),
    "participation": re.compile(rf"Participa(?:ção|{MOJIBAKE_CAO})\s+estimada\*\*:\s*(?P<value>.+)$", re.I),
    "h2_temas": re.compile(r"^##\s*Temas", re.I),
    "h2_space": re.compile(r"^##\s*SPACE", re.I),
    "h2_top": re.compile(r"^##\s*(Top\s*5|Pontos\s+Fortes)", re.I),
    "h2_bottom": re.compile(r"^##\s*(Bottom\s*5|Pontos\s+de\s+Aten)", re.I),
    "h2_suggestions": re.compile(r"^##\s*Sugest", re.I),
    "line_qv": re.compile(r"^\-\s+\*?\*?(?P<label>.+?)\*?\*?\s*:\s*(?P<score>[\d,.]+)\s*$"),
    "space_key": re.compile(r"SPACE[\s-]?([PCEWS])", re.I),
}


def fix_mojibake(text: str) -> str:
    """Repair common UTF-8 text that was decoded as cp1252 in old reports."""
    current = text
    for _ in range(3):
        try:
            candidate = current.encode("cp1252").decode("utf-8")
        except UnicodeError:
            break
        if sum(candidate.count(m) for m in MOJIBAKE_MARKERS) < sum(current.count(m) for m in MOJIBAKE_MARKERS):
            current = candidate
        else:
            break
    return current


def to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def score_text(value: object) -> str:
    if value is None or pd.isna(value):
        return "n/d"
    return f"{float(value):.2f}"


def sprint_num(label: str) -> int:
    match = re.search(r"(\d+)", label or "")
    return int(match.group(1)) if match else -1


def pretty_space_key(label: str) -> Optional[str]:
    match = PAT["space_key"].search(label or "")
    if not match:
        return None
    return SPACE_NAME.get(match.group(1).upper())


def space_pt_label(label: str) -> Optional[str]:
    match = PAT["space_key"].search(label or "")
    if not match:
        return None
    return SPACE_PT.get(match.group(1).upper())


def clean_artifact(label: str) -> str:
    label = re.sub(r"\s*\(respostas\)\s*$", "", label or "", flags=re.I)
    label = re.sub(r"\s*-\s*T\d+\s*$", "", label, flags=re.I)
    return label.strip() or "Survey Alunos"


def canon_text(label: str) -> str:
    text = fix_mojibake(label or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_question_label(label: str) -> str:
    label = fix_mojibake(label or "")
    label = re.sub(r"\s*\(item inverso\)\s*$", "", label, flags=re.I).strip()
    label = re.sub(r"^\d+(?:\.\d+)?\.\s*", "", label).strip()
    label = re.sub(r"\s*Marque apenas uma opção\.?", "", label, flags=re.I).strip()
    label = re.sub(r"\s*Escolha uma alternativa:?\s*", "", label, flags=re.I).strip()
    label = label.replace(" ?", "?")
    return label


def is_inverse_item(label: str) -> bool:
    normalized = canon_text(label)
    return "(item inverso)" in normalized or any(hint in normalized for hint in INVERSE_HINTS)


def infer_question_dimension(label: str) -> str:
    normalized = canon_text(label)
    for pattern, dimension in QUESTION_DIMENSION_RULES:
        if re.search(pattern, normalized):
            return dimension
    return "Dimensão não identificada"


def question_items_frame(items: List[Tuple[str, float]], kind: str) -> pd.DataFrame:
    rows = []
    for label, score in items:
        inverse = is_inverse_item(label)
        if inverse and kind == "strength":
            reading = "Item inverso já invertido: nota alta sugere menor presença do problema."
        elif inverse:
            reading = "Item inverso já invertido: nota baixa sugere maior presença do problema."
        elif kind == "strength":
            reading = "Nota maior indica percepção mais positiva."
        else:
            reading = "Nota menor indica ponto de atenção para conversa."
        rows.append(
            {
                "Item": clean_question_label(label),
                "Dimensão": infer_question_dimension(label),
                "Nota": score,
                "Leitura": reading,
            }
        )
    return pd.DataFrame(rows)


def mood_emoji(value: float) -> str:
    if value is None or pd.isna(value):
        return ""
    if value >= 7.5:
        return "😄"
    if value >= 6.0:
        return "😐"
    return "🙁"


def parse_relato_md(text: str, source_file: str, fallback_team: Optional[str]) -> Report:
    text = fix_mojibake(text)
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]

    artifact = "Survey Alunos"
    sprint = "Sprint ?"
    team = fallback_team
    participation = None
    overall = None

    for line in lines[:12]:
        title = PAT["title"].search(line)
        if title:
            artifact = clean_artifact(title.group("artifact"))
            sprint = f"Sprint {title.group('sprint')}"
        team_match = PAT["team"].search(line)
        if team_match:
            team = team_match.group("team").upper()
        part_match = PAT["participation"].search(line)
        if part_match:
            participation = part_match.group("value").strip()
        overall_match = PAT["overall"].search(line)
        if overall_match:
            overall = to_float(overall_match.group("score"))

    mode = None
    space: Dict[str, float] = {}
    themes: Dict[str, float] = {}
    top5: List[Tuple[str, float]] = []
    bottom5: List[Tuple[str, float]] = []
    suggestions: List[str] = []

    for raw in lines:
        line = raw.strip()
        if PAT["h2_temas"].match(line):
            mode = "themes"
            continue
        if PAT["h2_space"].match(line):
            mode = "space"
            continue
        if PAT["h2_top"].match(line):
            mode = "top"
            continue
        if PAT["h2_bottom"].match(line):
            mode = "bottom"
            continue
        if PAT["h2_suggestions"].match(line):
            mode = "suggestions"
            continue

        qv = PAT["line_qv"].match(line)
        if mode == "space" and qv:
            key = pretty_space_key(qv.group("label"))
            score = to_float(qv.group("score"))
            if key and score is not None:
                space[key] = score
        elif mode == "themes" and qv:
            score = to_float(qv.group("score"))
            if score is not None:
                themes[qv.group("label").strip("* ")] = score
        elif mode == "top" and qv:
            label = qv.group("label").strip()
            score = to_float(qv.group("score"))
            if score is not None and label.lower() != "sprint":
                top5.append((label, score))
        elif mode == "bottom" and qv:
            label = qv.group("label").strip()
            score = to_float(qv.group("score"))
            if score is not None and label.lower() != "sprint":
                bottom5.append((label, score))
        elif mode == "suggestions" and line.startswith("- "):
            suggestions.append(line[2:].strip())

    return Report(
        artifact=artifact,
        sprint=sprint,
        team=team,
        overall=overall,
        participation=participation,
        space=space,
        themes=themes,
        top5=top5[:5],
        bottom5=bottom5[:5],
        suggestions=suggestions,
        source_file=source_file,
    )


def load_reports(relatos_dir: Path, fallback_team: Optional[str]) -> List[Report]:
    reports: List[Report] = []
    for path in sorted(relatos_dir.glob("*.md"), key=lambda p: (sprint_num(p.name), p.name)):
        try:
            reports.append(parse_relato_md(path.read_text(encoding="utf-8"), path.name, fallback_team))
        except Exception as exc:
            st.warning(f"Falha ao ler {path.name}: {exc}")
    return reports


def build_space_frame(reports: List[Report]) -> pd.DataFrame:
    rows = []
    for report in reports:
        for dimension, score in report.space.items():
            if score is None:
                continue
            rows.append(
                {
                    "Equipe": report.team,
                    "Dimensão": dimension,
                    "Sprint": report.sprint,
                    "Sprint Nº": sprint_num(report.sprint),
                    "Nota": float(score),
                    "Artefato": report.artifact,
                }
            )
    return pd.DataFrame(rows, columns=["Equipe", "Dimensão", "Sprint", "Sprint Nº", "Nota", "Artefato"])


def build_history_table(reports: List[Report]) -> pd.DataFrame:
    rows = []
    for report in sorted(reports, key=lambda item: sprint_num(item.sprint)):
        row = {
            "Sprint": report.sprint,
            "Participação": report.participation or "n/d",
            "Nota do Survey": score_text(report.overall),
        }
        for dimension in SPACE_ORDER:
            row[SPACE_HISTORY_LABELS[dimension]] = score_text(report.space.get(dimension))
        rows.append(row)
    return pd.DataFrame(rows)


def load_all_team_reports(team_dir: Path) -> List[Report]:
    teams_root = team_dir.parent
    reports: List[Report] = []
    for candidate in sorted(teams_root.glob("t*"), key=lambda p: sprint_num(p.name)):
        if not candidate.is_dir():
            continue
        relatos_dir = candidate / "data" / "relatos"
        if relatos_dir.exists():
            reports.extend(load_reports(relatos_dir, candidate.name.upper()))
    return reports


def render_space_explanation() -> None:
    with st.expander("Como ler as dimensões SPACE", expanded=False):
        st.markdown(
            """
            O modelo SPACE ajuda a olhar produtividade por cinco dimensões:

            - **Satisfaction & Well-Being:** satisfação, motivação, bem-estar e tensões percebidas.
            - **Performance:** percepção de entrega, qualidade e resultado do trabalho.
            - **Activity:** atividade registrada no processo, como commits, issues, PRs ou outras evidências de trabalho.
            - **Communication & Collaboration:** comunicação, colaboração, transparência e troca de informações.
            - **Efficiency & Flow:** foco, bloqueios, interrupções e fluidez do trabalho.
            """
        )


def render_team_comparison(all_agg: pd.DataFrame, team_label: str, sprint_sel: List[str], dim_sel: List[str]) -> None:
    if all_agg.empty or "Equipe" not in all_agg.columns:
        return

    comparison_df = all_agg.dropna(subset=["Equipe"]).copy()
    if sprint_sel:
        comparison_df = comparison_df[comparison_df["Sprint"].isin(sprint_sel)]
    if dim_sel:
        comparison_df = comparison_df[comparison_df["Dimensão"].isin(dim_sel)]
    if comparison_df.empty:
        return

    current_team = team_label.upper()

    st.divider()
    st.subheader("Comparação contextual entre equipes")
    st.caption(
        "Esta comparação serve apenas como referência contextual. Diferenças podem refletir participação, "
        "composição da equipe, momento da sprint e percepção dos respondentes."
    )
    st.write(
        "O gráfico abaixo compara a equipe atual com a média das equipes na sprint selecionada, "
        "separando por dimensão SPACE. Ele ajuda a identificar dimensões que podem merecer mais conversa, "
        "sem representar ranking entre times."
    )

    available_sprints = sorted(comparison_df["Sprint"].dropna().unique().tolist(), key=sprint_num)
    selected_sprint = st.selectbox(
        "Sprint para comparação:",
        available_sprints,
        index=len(available_sprints) - 1,
    )
    sprint_df = comparison_df[comparison_df["Sprint"] == selected_sprint].copy()

    current_dim = (
        sprint_df[sprint_df["Equipe"] == current_team]
        .groupby("Dimensão", as_index=False)["Nota"]
        .mean()
        .rename(columns={"Nota": "Equipe atual"})
    )
    mean_dim = (
        sprint_df.groupby("Dimensão", as_index=False)["Nota"]
        .mean()
        .rename(columns={"Nota": "Média das equipes"})
    )
    dim_comparison = current_dim.merge(mean_dim, on="Dimensão", how="outer").sort_values("Dimensão")
    if not dim_comparison.empty:
        dim_long = dim_comparison.melt(
            id_vars="Dimensão",
            value_vars=["Equipe atual", "Média das equipes"],
            var_name="Referência",
            value_name="Nota",
        ).dropna(subset=["Nota"])
        fig_dim = px.bar(
            dim_long,
            x="Dimensão",
            y="Nota",
            color="Referência",
            barmode="group",
            color_discrete_map={"Equipe atual": "#ff4b4b", "Média das equipes": "#7cc7ff"},
            height=420,
            title=f"Referência contextual por dimensão — {selected_sprint}",
        )
        fig_dim.update_yaxes(range=[0, 10], title="Nota")
        fig_dim.update_xaxes(title="Dimensão")
        st.plotly_chart(fig_dim, use_container_width=True)
        st.caption(
            "Barras vermelhas mostram a equipe aberta neste dashboard. Barras azuis mostram a média das equipes "
            "na mesma sprint e dimensão."
        )


def run_app(team_dir: Path, team_label: str) -> None:
    st.set_page_config(page_title=f"{team_label} · NES SPACE Dashboard", layout="wide")

    relatos_dir = team_dir / "data" / "relatos"
    reports = load_reports(relatos_dir, team_label.upper())
    if not reports:
        st.error(f"Nenhum relato encontrado em `{relatos_dir}`.")
        st.stop()

    agg = build_space_frame(reports)
    all_reports = load_all_team_reports(team_dir)
    all_agg = build_space_frame(all_reports)

    st.sidebar.title("Filtros")
    sprints = sorted({report.sprint for report in reports}, key=sprint_num)
    dimensions = SPACE_ORDER
    sprint_sel = st.sidebar.multiselect("Sprint", sprints, default=sprints)
    dim_sel = st.sidebar.multiselect("Dimensões SPACE", dimensions, default=dimensions)

    df = agg.copy()
    if sprint_sel:
        df = df[df["Sprint"].isin(sprint_sel)]
    if dim_sel:
        df = df[df["Dimensão"].isin(dim_sel)]

    st.title(f"NES · SPACE Dashboard · {team_label.upper()}")
    render_space_explanation()

    st.subheader("Histórico completo de notas")
    st.caption(
        "Todas as sprints carregadas aparecem abaixo. `n/d` indica que não houve "
        "respostas ou dados suficientes para calcular a nota."
    )
    st.dataframe(build_history_table(reports), use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns(3)
    if df.empty:
        col1.metric("Média SPACE filtrada", "n/d")
        col2.metric("Dimensão destaque", "n/d")
        col3.metric("Sprint destaque", "n/d")
    else:
        col1.metric("Média SPACE filtrada", f"{df['Nota'].mean():.2f}")
        col2.metric("Dimensão destaque", df.groupby("Dimensão")["Nota"].mean().idxmax())
        col3.metric("Sprint destaque", df.groupby("Sprint")["Nota"].mean().idxmax())

    st.subheader("Evolução por Sprint")
    if not df.empty:
        df_line = (
            df.groupby(["Dimensão", "Sprint", "Sprint Nº"], as_index=False)["Nota"]
            .mean()
            .sort_values(["Sprint Nº", "Dimensão"])
        )
        fig_line = px.line(df_line, x="Sprint", y="Nota", color="Dimensão", markers=True, height=420)
        fig_line.add_trace(
            go.Scatter(
                x=df_line["Sprint"],
                y=df_line["Nota"],
                mode="text",
                text=df_line["Nota"].map(mood_emoji),
                textposition="top center",
                showlegend=False,
            )
        )
        fig_line.update_yaxes(range=[0, 10], title="Nota (0-10)")
        fig_line.update_xaxes(title="Sprint", categoryorder="array", categoryarray=sprints)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Não há notas SPACE calculadas para o filtro selecionado.")

    st.divider()
    st.subheader("Última Sprint - Notas por Artefato")
    last_sprint = sorted(df["Sprint"].unique().tolist(), key=sprint_num)[-1] if not df.empty else None
    if last_sprint:
        st.caption(f"Última sprint detectada: **{last_sprint}**")
        df_last = df[df["Sprint"] == last_sprint].copy()
        df_last["Dimensão PT"] = df_last["Dimensão"].map(space_pt_label)
        fig_pts = px.strip(
            df_last,
            x="Nota",
            y="Artefato",
            color="Dimensão PT",
            orientation="h",
            stripmode="overlay",
            height=360,
        )
        fig_pts.update_traces(jitter=0.12, marker_size=11, opacity=0.9)
        fig_pts.update_xaxes(range=[0, 10], title="Nota (0-10)")
        fig_pts.update_yaxes(title="")
        st.plotly_chart(fig_pts, use_container_width=True)

    st.divider()
    st.subheader("SPACE por dimensão")
    if not df.empty:
        df_bar = df.groupby(["Dimensão", "Sprint"], as_index=False)["Nota"].mean()
        fig_bar = px.bar(df_bar, x="Dimensão", y="Nota", color="Sprint", barmode="group", height=420)
        fig_bar.update_yaxes(range=[0, 10], title="Nota")
        fig_bar.update_xaxes(title="Dimensão")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("As dimensões selecionadas não possuem notas calculadas.")

    render_team_comparison(all_agg, team_label, sprint_sel, dim_sel)

    st.subheader("Relatos carregados")
    summary = pd.DataFrame(
        [
            {
                "Sprint": report.sprint,
                "Artefato": report.artifact,
                "Equipe": report.team or team_label.upper(),
                "Participação": report.participation or "n/d",
                "Nota do Survey": score_text(report.overall),
            }
            for report in reports
        ]
    ).sort_values("Sprint", key=lambda s: s.map(sprint_num))
    st.dataframe(summary, use_container_width=True, hide_index=True)

    report_labels = [f"{report.sprint} · {report.artifact}" for report in reports]
    selected_label = st.selectbox("Abrir relato:", report_labels, index=len(report_labels) - 1)
    selected = reports[report_labels.index(selected_label)]

    st.markdown(f"### {selected.artifact} — {selected.sprint}")
    left, right = st.columns([2, 1])
    with left:
        st.metric("Nota do Survey", score_text(selected.overall))
        if selected.participation:
            st.caption(f"Participação estimada: {selected.participation}")
        st.write("**SPACE (do relato)**")
        selected_space = pd.DataFrame(
            [
                {
                    "Dimensão": SPACE_HISTORY_LABELS[dimension],
                    "Nota": score_text(selected.space.get(dimension)),
                }
                for dimension in SPACE_ORDER
            ]
        )
        st.table(selected_space)
        if selected.themes:
            st.write("**Temas / Subdimensões**")
            st.table(pd.Series(selected.themes, name="Nota"))
    with right:
        if selected.top5:
            st.write("**Pontos Fortes percebidos**")
            st.caption("Itens com maiores notas normalizadas. Em itens inversos, a pontuação já foi invertida antes da exibição.")
            st.dataframe(question_items_frame(selected.top5, "strength"), use_container_width=True, hide_index=True)
        if selected.bottom5:
            st.write("**Pontos de Atenção para conversa**")
            st.caption("Itens com menores notas normalizadas. Se um item inverso aparece aqui, ele já foi invertido e indica maior presença do problema descrito.")
            st.dataframe(question_items_frame(selected.bottom5, "attention"), use_container_width=True, hide_index=True)
    if selected.suggestions:
        st.write("**Sugestões**")
        for suggestion in selected.suggestions:
            st.write(f"- {suggestion}")
