# VigiPA — Monitoramento de notificações de violência (2016–2025)

Protótipo de dashboard analítico para a região do Baixo Amazonas, com dados agregados do SINAN. **Não é uma ferramenta oficial da SESPA** e não deve orientar decisões clínicas ou ações operacionais sem validação epidemiológica.

## Como abrir

1. Extraia `VigiPA_Dashboard_2016_2025.zip`.
2. Abra `index.html` no navegador com acesso à internet (Chart.js é carregado de CDN).
3. `data.js` deve permanecer junto do HTML. O arquivo `data.json` é a mesma base agregada em formato aberto.
4. Para publicar em servidor estático, envie somente `index.html` e `data.js`. Não publique CSVs brutos.

## O que o painel calcula

- Notificações por ano, mês de notificação, município de ocorrência e `LES_AUTOP`.
- Distribuição por sexo (`CS_SEXO`), raça/cor (`CS_RACA`) e idade codificada (`NU_IDADE_N`).
- Repetição (`OUT_VEZES=1`) entre registros conhecidos (`1` ou `2`).
- Frequência de campos de múltipla marcação para tipos, meios e vínculos do provável autor.
- Respostas conversacionais determinísticas para rankings, somas e variações percentuais entre anos.

As contagens de tipos, meios e vínculos **não são mutuamente exclusivas**. A classificação `LES_AUTOP=2` indica *não autoprovocada*, e não estabelece diretamente se houve agressor interpessoal. `LES_AUTOP` vazio/ignorado aparece como *Não classificada*. Não se usa imputação de sexo, raça, idade, agravo ou município.

O campo `NU_ANO` define o ano do recorte. Mês vem de `DT_NOTIFIC` se data válida. Os municípios correspondem ao local de ocorrência (`ID_MN_OCOR`), não ao local de residência (`ID_MN_RESI`), e os códigos de seis e sete dígitos são confrontados com a lista dos 13 municípios especificados. A idade SINAN usa primeiro dígito como unidade (1 hora, 2 dias, 3 meses, 4 anos); valores inválidos ficam em *Ignorada*.

## Limites dos dados

- O arquivo é um **agregado**, não tem registros individuais nem identificadores de pessoas.
- Não foram fornecidos denominadores anuais de população por município. Portanto, **taxas de notificação por 100 mil habitantes não são calculadas**. Sem eles, comparar risco entre municípios com base em volume absoluto pode ser enganoso.
- O campo `EVOLUCAO` está presente no CSV, mas o dicionário PDF disponibilizado (revisão junho/2015) não documenta suficientemente seu significado para uma estimativa auditável de letalidade. O painel não apresenta esse indicador como validado.
- Não existe campo explícito confiável de tentativa de suicídio ou automutilação para subtipagem de todas as notificações; o painel usa lesão autoprovocada como categoria ampla.
- Notificações são eventos de registro, não pessoas únicas. As séries podem ser afetadas por subnotificação, atraso, qualidade de preenchimento e mudanças de vigilância, especialmente em 2025.
- **2020 tem zero registros selecionados na base fornecida.** Isso deve ser investigado como possível lacuna de origem, extração ou classificação antes de comparar períodos pandêmicos ou calcular crescimento a partir de 2020.
- As perguntas livres são interpretadas apenas por regras explícitas no navegador. Não há LLM, integração externa, endpoint ou geração de SQL, e perguntas não reconhecidas recebem uma orientação.

## Pipeline

O script `vigilancia_etl.py` lê em streaming três CSVs originais e dois contidos em `csv.zip`. Ajuste os caminhos definidos nele se reorganizar os arquivos. Execute:

```bash
python vigilancia_etl.py
python empacotar_vigilancia.py
```

O script de empacotamento (`empacotar_vigilancia.py`) pertence à entrega original e converte `data.json` em `data.js`. Para reutilizá-lo, conserve-o junto do projeto ou gere a linha `window.VIGILANCIA_DADOS = <JSON>;` a partir do JSON.

## Para evolução

1. Validar com a equipe de vigilância a interpretação de `EVOLUCAO` e os códigos atualizados para 2016–2025.
2. Integrar série de população municipal por ano, com fontes IBGE e notas de compatibilidade temporal, para estimar **taxas de notificação** por 100 mil habitantes.
3. Auditoria adicional de completude, duplicidades, mudanças de formulário e supressão de pequenas células antes de qualquer publicação pública.
4. Para chat com LLM, colocar somente consultas parametrizadas a agregados por trás de uma API segura, com autenticação e testes contra divulgação de microdados.

## Referências

- Dicionário fornecido: `VIOLEN_DIC_DADOS.pdf`, revisão junho/2015.
- Código municipal: IBGE, tabela de códigos dos municípios, https://www.ibge.gov.br/explica/codigos-dos-municipios.php
- SINAN: a interpretação epidemiológica e eventual divulgação pública devem seguir protocolos institucionais.
