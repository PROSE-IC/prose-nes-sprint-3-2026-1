# Metodologia do Dashboard

Este documento registra como o dashboard interpreta os relatos do Survey e como algumas informações devem ser lidas durante as reuniões de feedback.

## Dimensões SPACE

O modelo SPACE ajuda a olhar produtividade por cinco dimensões:

- **Satisfaction & Well-Being:** satisfação, motivação, bem-estar e tensões percebidas.
- **Performance:** percepção de entrega, qualidade e resultado do trabalho.
- **Activity:** atividade registrada no processo, como commits, issues, PRs ou outras evidências de trabalho.
- **Communication & Collaboration:** comunicação, colaboração, transparência e troca de informações.
- **Efficiency & Flow:** foco, bloqueios, interrupções e fluidez do trabalho.

Neste dashboard, a análise atual vem principalmente do survey. Por isso, a dimensão **Activity** aparece como explicação do modelo, mas ainda não é exibida como série própria nos gráficos.

## Nota do Survey e Média SPACE

A **Nota do Survey** é a nota geral calculada pelo script de análise a partir das respostas do questionário. Ela considera os temas definidos no processamento do survey e seus pesos.

A **Média SPACE filtrada** exibida no topo do dashboard é uma média simples das dimensões SPACE visíveis nos filtros selecionados. Por isso, ela pode ser ligeiramente diferente da Nota do Survey.

## Comparação contextual entre equipes

O dashboard pode mostrar uma comparação leve entre a equipe atual e a média das equipes para contextualizar a leitura dos resultados. Essa comparação não deve ser usada como ranking, avaliação individual ou competição entre times.

Frase de leitura recomendada:

> Esta comparação serve apenas como referência contextual. Diferenças podem refletir participação, composição da equipe, momento da sprint e percepção dos respondentes.

A comparação aparece por dimensão SPACE. Ela ajuda a perceber se uma dimensão da equipe está próxima, acima ou abaixo da média observada nas demais equipes, mas a interpretação final deve considerar a participação no survey, o momento da sprint e os comentários levantados durante o feedback.

## Top 5 Perguntas

O **Top 5 perguntas** mostra as perguntas com maiores notas normalizadas no survey. Em geral, esses itens representam os pontos mais fortes percebidos pela equipe naquela sprint.

## Bottom 5 Perguntas

O **Bottom 5 perguntas** mostra as perguntas com menores notas normalizadas no survey. Em geral, esses itens representam pontos que merecem mais atenção ou investigação durante a conversa com a equipe.

## Itens Inversos

Algumas perguntas são inversas, como tensão, conflito, dificuldade de comunicação e bloqueios. Nesses casos, uma resposta alta no formulário pode indicar maior presença de um problema.

Para evitar interpretação errada, o script novo inverte a pontuação desses itens antes de montar os rankings. Assim, se um item inverso aparece no Bottom 5, isso significa que ele é um possível sinal de problema, e não uma resposta positiva baixa.

Também foram ajustados alguns rótulos para deixar isso mais explícito. Por exemplo:

```text
Tensões da equipe na Sprint (item inverso)
```

Essa marcação ajuda a lembrar que a pontuação já foi tratada antes de aparecer no dashboard.
