# PROSE NES 2026/1 - Leva Sprint 3

Repositorio dos dashboards SPACE do NES preparados para a coleta da Sprint 3.

Cada equipe fica isolada em `teams/tX`, compartilhando o mesmo motor em
`common/dashboard_app.py`. As planilhas brutas e auditorias nominais nao sao
versionadas.

## Estado desta leva

- T4, equipe da Sophya: Sprints 0, 1, 2 e 3 carregadas.
- Demais equipes: estrutura preservada para processamento posterior.
- PDF da devolutiva do T4 gerado a partir da Sprint 3, com historico S0-S3.

## Deploy no Streamlit Cloud

Use este repositorio e a branch `main`.

Para o T4:

```text
teams/t4/app.py
```

Os demais times seguem o mesmo formato:

```text
teams/t1/app.py
teams/t2/app.py
...
teams/t9/app.py
```

## Execucao local

```bash
python -m pip install -r requirements.txt
python -m streamlit run teams/t4/app.py
```

## Dados publicados

Somente artefatos agregados necessarios ao dashboard sao versionados, como
relatos Markdown e imagens. Respostas individuais, planilhas de Forms e
auditorias de classificacao devem permanecer fora do repositorio.

## Relatorio PDF

- [T4 - Sprint 3, com historico S0-S3](pdfs/relatorio_T4_sprint_3.pdf)
