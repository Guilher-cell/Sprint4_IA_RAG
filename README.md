# EV Challenge — GoodWe · Sprint 04 — RAG medido, confiável e utilizável

Chatbot com IA para mobilidade elétrica em condomínios (GoodWe **EV ChargeOps / ChargeGrid**).
Continuação das Sprints 1, 2 e 3: esta sprint adiciona **embeddings + ChromaDB persistente, pipeline RAG com
grounding e citação de fonte, segurança contra prompt injection via documentos, avaliação por iteração e interface web**.

FIAP · Prompt and Artificial Intelligence · 2026.2 · Prof. Jorge Luiz Gomes · Parceiro: GoodWe Brasil · Entrega: 23/10/2026

> **Estado da entrega.** A avaliação **live foi executada em 21/10/2026** (`nomic-embed-text` via Ollama local + `gpt-oss-120b` e `gpt-oss-20b` via Groq; 30 casos; 0 erros de chamada).
> O **RAGAS não foi executado** (`import ragas` falha no ambiente): usamos a **rubrica manual equivalente** (`evals/RUBRICA.md`), que é lexical e subestima a faithfulness.
> A ablação e o varrimento de `k` foram medidos **offline**. A matriz de prompts (v2/v3) ficou incompleta por limite de taxa da Groq. Limitações completas em `docs/relatorio_rag.md` §7.

## 1. Escopo exigido × onde está

| # | Item (enunciado §3) | Onde está | Status |
|---|---|---|---|
| 1 | Vetorização: base expandida em ChromaDB persistente + nomic-embed-text | `data/knowledge_base/` (8 docs), `src/rag/embeddings.py`, `src/rag/vector_store.py` | ✅ Chroma persistente + `nomic-embed-text` (Ollama) executados no live |
| 2 | Pipeline end-to-end: PyMuPDFLoader → RecursiveCharacterTextSplitter → retriever → prompt RAG versionado | `src/rag/{loader,chunking,retriever,prompt_rag,pipeline}.py`, `prompts/rag/` | ✅ |
| 3 | Grounding + citação (documento/seção) | `src/rag/pipeline.py` (pós-validação), UI mostra *arquivo · seção · página* | ✅ taxa de citação 1,00, nativa em 20/20 (live, iter3, nos dois modelos) |
| 4 | Avaliação RAGAS ou fallback manual documentado | `evals/` (`RUBRICA.md`, `metricas.py`, `run_eval_rag.py`, `ragas_eval.py`) | ✅ fallback manual documentado, aplicado em 4 iterações × 2 modelos · RAGAS **não executado** (não importa neste ambiente) |
| 5 | Interface web consumindo o RAG com citação visível | `app/app.py` (Gradio) | ✅ |
| 6 | Segurança: recusa fora do contexto; injection via documentos | `src/rag/seguranca.py`, `src/guardrails/` (S03), `evals/fixtures/doc_envenenado.md` | ✅ |
| 7 | Relatório de evolução (≤ 5 pág., antes/depois) | `docs/relatorio_evolucao_sprint4.pdf` (3 pág.) | ✅ |
| — | `relatorio_rag.md` e `relatorio_modelos.md` | `docs/` | ✅ |
| — | Prompt RAG versionado com ganho por iteração | `prompts/VERSOES_RAG.md` | ✅ |
| — | Bônus +1: multi-provider (modelos × prompts) | `run_eval_rag.py --matriz` | ✅ 2 modelos × 3 versões de prompt (matriz v2/v3 isolada ficou incompleta) |

## 2. Resultados (live, 30 casos, `gpt-oss-120b`; detalhes e `gpt-oss-20b` em `docs/relatorio_rag.md` §6.1)

| Métrica | Sprints 1/2 | iter1 | iter2 | **iter3** |
|---|---|---|---|---|
| answer_relevancy | 0,400 | 0,846 | **0,975** | 0,971 |
| context_recall | 0,000 | 0,829 | 0,871 | **0,908** |
| context_precision | 0,000 | 0,600 | 0,575 | **0,637** |
| taxa de citação | 0,00 | 0,00 | 1,00 (nativa 8/20) | **1,00 (nativa 20/20)** |
| recusa correta (8 casos) | 0,25 | 0,25 | **1,00** | **1,00** |
| resistência a injeção em documento | n/a | 1,00 | 1,00 | 1,00 |
| faithfulness (lexical)† | 0,067‡ | 0,670 | 0,510 | 0,514 |

Com o `gpt-oss-20b`, a iter3 chega a relevância 0,975, faithfulness† 0,744 e injeção 1,00 (0,50 nas iter1/iter2).
† rubrica **lexical**: subestima a fidelidade (auditoria manual de 6 frases sinalizadas: 5 sustentadas pela base, 1 não verificada); trate como limite inferior. ‡ baseline não comparável.
**Honestidade:** para o 120b, iter3 melhora a recuperação e a citação nativa, mas **não** a qualidade da resposta sobre a iter2. Offline (sem LLM, reproduzível), relevância 0,108 → 0,608 → 0,667 → 0,775.
Ablação por componente e varrimento de `k` (offline): `docs/relatorio_rag.md` e `docs/relatorio_modelos.md`.

## 3. Estrutura

```
data/knowledge_base/   8 documentos: 5 PDFs (4 manuais + regimento), FAQ, tabela tarifária, política de escalonamento
data/chroma_db/        vector store persistente (gerado; no .gitignore)
src/rag/               loader · chunking · embeddings · vector_store · retriever · prompt_rag · seguranca · pipeline · config
prompts/rag/           prompt_rag_v1/v2/v3.md  (+ prompts/VERSOES_RAG.md = tabela de versões e ganhos)
app/                   interface Gradio (+ README de execução)
evals/                 eval_set_rag.json · RUBRICA.md · metricas.py · run_eval_rag.py · run_ablacao.py · run_sweep_k.py · ragas_eval.py · *_results.json
docs/                  relatorio_evolucao_sprint4.pdf/.md · relatorio_rag.md · relatorio_modelos.md · sprint3/ (documentos legados)
tests/                 test_rag.py (29 testes, 100% offline)
scripts/               gerar_kb_pdfs.py · gerar_tabelas.py · gerar_pdf.py
main_rag.py            CLI do RAG        |   main_v2.py = chatbot Sprint 03   |   chatbot.py = Sprint 1/2 (legado)
```

O código e os relatórios das Sprints 1–3 foram **mantidos** (o README original está em `docs/sprint3/README_sprint3.md`).

## 4. Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env          # opcional para rodar offline; obrigatório para o modo live (nunca commitar o .env)

python app/app.py             # interface -> http://127.0.0.1:7860
python main_rag.py            # CLI (--iteracao iter1|iter2|iter3, --provider offline|groq_oss|groq_secundario)
pytest -q                     # 29 testes, sem rede
```

Sem `GROQ_API_KEY` o provider `auto` usa o **gerador extrativo offline** (responde com sentenças do contexto, não é um LLM); sem
Ollama o backend de embeddings `auto` cai para `offline-hash` **com aviso**.

## 5. Reproduzir a avaliação offline

```bash
python evals/run_eval_rag.py --modo offline      # baseline_s12, iter1, iter2, iter3  -> evals/rag_results.json
python evals/run_ablacao.py                      # ablação da iter3                   -> evals/ablacao_results.json
python evals/run_sweep_k.py                      # varrimento de k                    -> evals/sweep_k_results.json
python scripts/gerar_tabelas.py                  # -> docs/tabelas_resultados.md
```

Duas execuções consecutivas dão resultados idênticos (busca do Chroma configurada para ser determinística).



## 6. Equipe

| Integrante | RM | Tarefa principal (Sprint 04) |
|---|---|---|
| André Fujinaga | 569158 | Pipeline RAG end-to-end + multi-provider |
| Arthur Machado | 569919 | Vetorização: ChromaDB persistente + nomic-embed-text |
| Conrado Gracie | 569157 | Interface web (Gradio) com citação visível |
| Guilherme Belo | 570079 | Prompt RAG versionado + base de conhecimento |
| Renato Sandreschi | 569156 | Guardrails/segurança + avaliação + relatório de evolução |

*(A divisão da Sprint 04 é uma proposta: ajuste para refletir quem realmente fez cada parte.)*
