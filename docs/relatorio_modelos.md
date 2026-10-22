# Relatório de Uso de Modelos e Parâmetros — Sprint 04 (RAG)

Modelos e parâmetros do pipeline RAG (`src/rag/`, `src/chain/llm_factory.py`) e como compará-los.
Versão da Sprint 03 (chatbot conversacional): `docs/sprint3/relatorio_modelos_sprint3.md`.

> **Status da execução.** Comparação **live executada em 21/10/2026** (Groq, `nomic-embed-text` via Ollama local), com o mesmo eval set de 30 casos,
> mesmos parâmetros e mesmo pipeline para os dois modelos, 0 erros de chamada nas 8 execuções principais. O varrimento de `k` (§3) foi medido **offline**.
> A matriz modelos × prompts em `iter3` ficou **incompleta** por limite de taxa da Groq; o bônus é sustentado pelas 3 versões de prompt × 2 modelos da §4.

## 1. Modelos

| | Modelo A (principal) | Modelo B (segundo modelo / bônus) | Embeddings |
|---|---|---|---|
| Nome | `openai/gpt-oss-120b` | `openai/gpt-oss-20b` | `nomic-embed-text` |
| Provedor | Groq (GroqCloud) | Groq (GroqCloud) | Ollama Cloud (`OLLAMA_API_KEY`) ou Ollama local |
| Provider no código | `groq_oss` | `groq_secundario` | `EMBEDDINGS_BACKEND=nomic` |
| Tipo | open-weight, MoE (~5,1B ativos/token), **raciocínio** | open-weight, MoE (~3,6B ativos/token), **raciocínio** | modelo de embeddings (768 dim.) |
| Contexto | 131.072 tokens | 131.072 tokens | 8.192 tokens |

Escolha (herdada da Sprint 03): Groq em vez de Ollama local por falta de hardware para 120B; `llama-3.3-70b-versatile` foi
descontinuado em 16/08/2026 e `qwen/qwen3.6-27b` retornou 404 na conta da equipe. Limitação reconhecida: A e B são da
mesma família, então o comparativo isola **tamanho**, não arquitetura. `GROQ_MODEL_SECUNDARIO` no `.env` permite trocar o
Modelo B por outra família sem editar código.

## 2. Parâmetros adotados

| Parâmetro | Sprint 03 | **Sprint 04 (RAG)** | Justificativa |
|---|---|---|---|
| `temperature` | 0,4 | **0,0** | Resposta fundamentada no contexto deve ser a mais determinística possível (recomendação do enunciado); reduz variação entre execuções do eval |
| `top_p` | 0,9 | **1,0** | Com `temperature=0` a amostragem é gulosa e `top_p` é praticamente irrelevante; mantido em 1,0 para não adicionar um segundo corte |
| `max_tokens` | 600 | **1024** | Os gpt-oss são modelos de raciocínio: os tokens de *reasoning* contam no limite de saída; com 600 a resposta pode sair truncada ou **vazia**. O pipeline trata resposta vazia como erro explícito (`llm_resposta_vazia`) em vez de anexar `Fontes:` a um texto vazio |
| `k` (top-k) | — | **4** (iter2/iter3); 3 (iter1) | ver seção 3 |
| `fetch_k` | — | **3 × k** | candidatos buscados no Chroma antes de rerank/desempate |
| chunk | — | **600 / overlap 100** | ver `relatorio_rag.md` §3 |
| limiar de relevância | — | **0,22** (offline-hash) · **0,55** (nomic, *a recalibrar*) | recusa se o melhor trecho for pouco relevante |
| `max_retries` | 2 | 2 | rate limit do tier gratuito da Groq (~30 req/min por modelo) |

`max_tokens=1024` foi uma decisão por precaução; nas execuções live **não houve resposta vazia nem truncada** (0 erros), mas não variamos o parâmetro para medir o efeito.

## 3. Efeito de `k` (medido, offline, iter3, 30 casos — `evals/run_sweep_k.py`)

| k | relevância | recall | precisão | MRR | citação | recusa | injeção |
|---|---|---|---|---|---|---|---|
| 1 | 0,500 | 0,475 | **0,750** | 0,750 | 0,80 | 1,00 | 1,00 |
| 2 | 0,683 | 0,758 | 0,700 | 0,825 | 1,00 | 1,00 | 1,00 |
| 3 | **0,783** | 0,846 | 0,650 | 0,858 | 1,00 | 1,00 | 1,00 |
| **4** | 0,775 | 0,875 | 0,600 | 0,858 | 1,00 | 1,00 | 1,00 |
| 6 | 0,750 | 0,917 | 0,525 | 0,858 | 1,00 | 1,00 | 1,00 |
| 8 | 0,750 | **0,942** | 0,450 | 0,858 | 1,00 | 1,00 | 1,00 |

Trade-off clássico: **k maior sobe o recall e derruba a precisão** (mais ruído no prompt, mais tokens). k=1 é pobre
(recall 0,475). **k=3 e k=4 empatam em relevância** (0,783 vs 0,775: diferença dentro do ruído de n=20). Escolhi **k=4** por
priorizar recall — perguntas como "o que o zelador pode e não pode fazer" exigem trechos de mais de um documento —, ao custo de
precisão 0,60. Ressalva: o gerador offline é extrativo e favorece k pequeno; com um LLM o ótimo pode mudar (rode o sweep live).

## 4. Comparação de modelos no RAG (live, 21/10/2026)

Iteração final **iter3** (prompt RAG v3), 30 casos, `temperature=0`, `top_p=1`, `max_tokens=1024`, k=4:

| Métrica | `gpt-oss-120b` (A) | `gpt-oss-20b` (B) | Diferença (B − A) |
|---|---|---|---|
| answer_relevancy | 0,971 | 0,975 | +0,004 |
| faithfulness (lexical)† | 0,514 | 0,744 | +0,230 |
| fidelidade à base (documento único)† | 0,576 | 0,748 | +0,172 |
| context_recall / precision / MRR | 0,908 / 0,637 / 0,917 | idem (a recuperação não depende do gerador) | 0 |
| taxa de citação (nativa) | 1,00 (20/20) | 1,00 (20/20) | 0 |
| recusa correta (8 casos) | 1,00 | 1,00 | 0 |
| resistência a injeção (2 casos) | 1,00 | 1,00 | 0 |
| falsa recusa | 0,00 | 0,00 | 0 |
| latência mediana por chamada ao LLM | **3,1 s** | 7,8 s | +4,7 s |
| latência média (todos os casos, inclui os sem LLM) | 3,29 s | 5,16 s | |
| erros de chamada | 0 | 0 | |

Evolução por iteração (relevância / faithfulness† / resistência a injeção / latência mediana):

| Iteração (prompt) | 120b | 20b |
|---|---|---|
| baseline S1/2 (`system_prompt_v1`) | 0,400 / 0,067‡ / n/a / 1,4 s | 0,308 / 0,047‡ / n/a / 11,6 s |
| iter1 (RAG v1) | 0,846 / 0,670 / 1,00 / 5,3 s | 0,721 / 0,710 / 0,50 / 6,6 s |
| iter2 (RAG v2) | 0,975 / 0,510 / 1,00 / 5,1 s | 0,958 / 0,559 / 0,50 / 4,7 s |
| iter3 (RAG v3) | 0,971 / 0,514 / 1,00 / 3,1 s | 0,975 / 0,744 / 1,00 / 7,8 s |

† Rubrica lexical (subestima fidelidade; auditoria manual de 6 frases do 120b: 5 sustentadas, 1 não verificada) — ver `docs/relatorio_rag.md` §6.1.
‡ Não comparável (o LLM viu o prompt inteiro; a métrica compara com 3 trechos).

**Leitura:**
- **Qualidade de resposta equivalente** (relevância 0,971 × 0,975; mesmas recusas e citações). Com n = 20 não há diferença que o eval set sustente.
- **O 20b teve faithfulness lexical maior** (0,744 × 0,514). Hipótese **não testada**: o 20b responde de forma mais literal e o 120b parafraseia/elabora mais; a rubrica lexical premia a literalidade.
- **Latência:** o 120b foi mais rápido na mediana (3,1 s × 7,8 s), mas a Groq varia entre execuções: no baseline o 20b chegou a 11,6 s de mediana. Com poucas chamadas e rate limit, trate latência como indicativa.
- **Robustez a injeção sem sanitização:** o 120b resistiu (1,00 em iter1/iter2) e o 20b não (0,50; resposta correta 0,00) — com 2 casos, é indício, não conclusão.
- **Custo:** a Groq não informou preços na montagem e não medimos tokens por chamada; não há comparação de custo.
- **Limite do desenho:** A e B são da mesma família (só muda o tamanho), então não se pode concluir nada sobre outras famílias de modelo.

**Bônus multi-provider (+1 pt):** consultamos **dois modelos** (`groq_oss`, `groq_secundario`) com **três versões de prompt** (`prompt_rag_v1/v2/v3`, usadas nas iterações iter1/iter2/iter3). Ressalva: nas iterações, a versão do prompt
varia **junto** com mudanças de pipeline; o isolamento do prompt só foi concluído para o v1 na config iter3 (120b: relevância 0,946, faithfulness 0,833, recusa 0,875, 0 erros) —
a matriz v2/v3 falhou por 429 e não é usada.

## 5. Evidência anterior dos mesmos modelos (Sprint 03, execução real de 18/09/2026)

Outra tarefa (chatbot com *tool calling*, 9 casos) — **não substitui** a comparação RAG, mas é o único dado real
de A × B que a equipe tem:

| | gpt-oss-120b | gpt-oss-20b |
|---|---|---|
| Latência média (bruta / sem outliers) | 6,46 s / 1,87 s | 10,86 s / 4,76 s |
| Tokens de saída médios | 114,8 | 94,8 |
| Respostas adequadas | 9/9 | 9/9 |
| Fallback por `tool_use_failed` | 0/9 | 1/9 |

Fonte: `docs/sprint3/relatorio_modelos_sprint3.md` §4–5. Lição aplicável ao RAG: comparar médias brutas de latência é
enganoso com outliers (rate limit, backoff) — reporte também a mediana.

## 6. Como reproduzir / completar

```bash
cp .env.example .env     # GROQ_API_KEY (+ Ollama local com `ollama pull nomic-embed-text`); nunca commitar o .env
python evals/run_eval_rag.py --modo live --provider groq_oss
python evals/run_eval_rag.py --modo live --provider groq_secundario
python evals/run_eval_rag.py --modo live --provider groq_oss --matriz     # completa v2/v3 (reaproveita casos já avaliados)
python evals/run_sweep_k.py --modo live --provider groq_oss                # k com LLM real (ainda não feito)
python scripts/gerar_tabelas.py                                            # -> docs/tabelas_resultados.md
```

Tier gratuito da Groq: ~30 req/min por modelo e cotas de tokens; o runner espera o tempo sugerido em 429, para se a espera for longa e grava cada caso em `evals/live_cache_<provider>.json`.
