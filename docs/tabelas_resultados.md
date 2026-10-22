# Tabelas de resultados (geradas por scripts/gerar_tabelas.py)

### Iterações — `offline:offline`

| Métrica | baseline_s12 | iter1 | iter2 | iter3 |
|---|---|---|---|---|
| answer_relevancy | 0.108 | 0.608 | 0.667 | 0.775 |
| faithfulness | 1 | 1 | 1 | 1 |
| fidelidade_base | 0.472 | 1 | 1 | 1 |
| context_recall | 0 | 0.758 | 0.838 | 0.875 |
| context_precision | 0 | 0.517 | 0.525 | 0.6 |
| MRR | 0 | 0.808 | 0.867 | 0.858 |
| taxa_citacao | 0 | 0 | 0.95 | 1 |
| recusa_correta | 0.25 | 0.375 | 0.75 | 1 |
| resist._injeção | — | 0 | 0 | 1 |
| latência_média_s | 0.005 | 0.005 | 0.005 | 0.007 |
| nº de chunks | 10 | 26 | 66 | 66 |
| embeddings / geração | offline-hash / extrativo-offline | offline-hash / extrativo-offline | offline-hash / extrativo-offline | offline-hash / extrativo-offline |

### Iterações — `live:groq_oss`

| Métrica | baseline_s12 | iter1 | iter2 | iter3 |
|---|---|---|---|---|
| answer_relevancy | 0.4 | 0.846 | 0.975 | 0.971 |
| faithfulness | 0.067 | 0.67 | 0.51 | 0.514 |
| fidelidade_base | 0.202 | 0.692 | 0.642 | 0.576 |
| context_recall | 0 | 0.829 | 0.871 | 0.908 |
| context_precision | 0 | 0.6 | 0.575 | 0.637 |
| MRR | 0 | 0.875 | 0.892 | 0.917 |
| taxa_citacao | 0 | 0 | 1 | 1 |
| recusa_correta | 0.25 | 0.25 | 1 | 1 |
| resist._injeção | — | 1 | 1 | 1 |
| latência_média_s | 1.824 | 5.208 | 4.007 | 3.286 |
| nº de chunks | 10 | 26 | 66 | 66 |
| embeddings / geração | nomic-embed-text / openai/gpt-oss-120b | nomic-embed-text / openai/gpt-oss-120b | nomic-embed-text / openai/gpt-oss-120b | nomic-embed-text / openai/gpt-oss-120b |

### Iterações — `live:groq_secundario`

| Métrica | baseline_s12 | iter1 | iter2 | iter3 |
|---|---|---|---|---|
| answer_relevancy | 0.308 | 0.721 | 0.958 | 0.975 |
| faithfulness | 0.047 | 0.71 | 0.559 | 0.744 |
| fidelidade_base | 0.211 | 0.746 | 0.624 | 0.748 |
| context_recall | 0 | 0.829 | 0.871 | 0.908 |
| context_precision | 0 | 0.6 | 0.575 | 0.637 |
| MRR | 0 | 0.875 | 0.892 | 0.917 |
| taxa_citacao | 0 | 0 | 1 | 1 |
| recusa_correta | 0.25 | 0.25 | 1 | 1 |
| resist._injeção | — | 0.5 | 0.5 | 1 |
| latência_média_s | 8.762 | 5.934 | 4.216 | 5.157 |
| nº de chunks | 10 | 26 | 66 | 66 |
| embeddings / geração | nomic-embed-text / openai/gpt-oss-20b | nomic-embed-text / openai/gpt-oss-20b | nomic-embed-text / openai/gpt-oss-20b | nomic-embed-text / openai/gpt-oss-20b |

### Matriz modelo × prompt — `live:groq_oss` (iter3 com prompt v1/v2/v3)

| Métrica | v1 |
|---|---|
| answer_relevancy | 0.946 |
| faithfulness | 0.833 |
| fidelidade_base | 0.754 |
| context_recall | 0.908 |
| context_precision | 0.637 |
| MRR | 0.917 |
| taxa_citacao | 1 |
| recusa_correta | 0.875 |
| resist._injeção | 1 |
| latência_média_s | 0.813 |
| nº de chunks | 66 |
| embeddings / geração | nomic-embed-text / openai/gpt-oss-120b |

### Ablação da iter3 (`offline:offline`)

| Variante | answer_relevancy | context_recall | context_precision | mrr | taxa_citacao | taxa_recusa_correta | resistencia_injecao |
|---|---|---|---|---|---|---|---|
| iter3 (completa) | 0.775 | 0.875 | 0.6 | 0.858 | 1 | 1 | 1 |
| - rerank lexical | 0.529 | 0.838 | 0.525 | 0.867 | 0.65 | 1 | 1 |
| - limiar de relevância | 0.775 | 0.875 | 0.6 | 0.858 | 1 | 0.75 | 1 |
| - checagem de entidades | 0.775 | 0.875 | 0.6 | 0.858 | 1 | 1 | 1 |
| - sanitização de contexto | 0.775 | 0.875 | 0.6 | 0.858 | 1 | 1 | 0 |
| - guardrails regex (S03) | 0.775 | 0.875 | 0.6 | 0.858 | 1 | 0.75 | 1 |
| - chunking por seção/prefixo | 0.783 | 0.858 | 0.575 | 0.883 | 1 | 1 | 1 |
| - overlap (100 -> 0) | 0.775 | 0.875 | 0.6 | 0.858 | 1 | 1 | 1 |
