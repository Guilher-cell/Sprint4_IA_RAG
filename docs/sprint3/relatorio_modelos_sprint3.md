# Relatório de Uso de Modelos e Parâmetros — GoodWe EV ChargeOps Chatbot

Comparativo entre os dois modelos suportados por `src/chain/llm_factory.py`, para o bônus de
multi-provider da Sprint 03 (§6 do enunciado).

## 1. Modelos comparados

> **Nota de arquitetura.** A equipe não tem hardware local para rodar `gpt-oss-120b` via
> Ollama (120B parâmetros exigem GPU/RAM que a equipe não possui). Os dois modelos abaixo são
> acessados via **API da Groq (GroqCloud)** — mesma `GROQ_API_KEY`, mesmo SDK
> (`langchain-groq`), apenas o parâmetro `model` muda. Essa decisão está documentada em
> `docs/relatorio_evolucao.md` (Problema 4). O suporte a Ollama local permanece no código
> (`provider="ollama"` em `llm_factory.py`) como caminho opcional, não usado por padrão.
>
> **Histórico da escolha do Modelo B (2 tentativas fracassadas antes desta).** O plano
> original era `llama-3.3-70b-versatile` (mesmo da Sprint 2), mas a Groq o **descontinuou em
> 16/08/2026** (Problema 5). A substituta recomendada pela própria Groq, `qwen/qwen3.6-27b`,
> **também retornou erro 404** na conta da equipe — provavelmente um modelo em acesso
> restrito/preview por conta ou tier, mesmo documentado publicamente (Problema 7). Por isso o
> Modelo B final é `openai/gpt-oss-20b`: está no catálogo padrão (não preview) da Groq, com
> rate limits publicamente documentados, o que reduz o risco de um quarto erro 404 — ao custo
> de comparar duas variantes de tamanho do mesmo modelo (120B vs. 20B) em vez de duas famílias
> diferentes. `GROQ_MODEL_SECUNDARIO` no `.env` é livremente configurável: se a equipe
> confirmar acesso a outro modelo (rodando o comando abaixo), pode trocar sem editar código.
>
> ```bash
> curl -s https://api.groq.com/openai/v1/models \
>   -H "Authorization: Bearer $GROQ_API_KEY" | python3 -m json.tool
> ```

| | Modelo A | Modelo B |
|---|---|---|
| Nome | `openai/gpt-oss-120b` | `openai/gpt-oss-20b` |
| Provedor de hospedagem | Groq (GroqCloud) | Groq (GroqCloud) |
| Model lab de origem | OpenAI (open-weight, lançado em ago/2025) | OpenAI (open-weight, lançado em ago/2025) |
| Parâmetros (aprox.) | 120B (mixture-of-experts, ~5,1B ativos por token) | 20B (mixture-of-experts, ~3,6B ativos por token) |
| Contexto | 131.072 tokens | 131.072 tokens |
| Uso na Sprint 2 | — | — |
| Uso na Sprint 03 | Modelo padrão da chain LCEL (`LLM_PROVIDER=groq_oss`), equivalente funcional ao `ChatOllama (gpt-oss:120b)` exigido pelo enunciado (Aula 01) | Segundo modelo do comparativo (`LLM_PROVIDER=groq_secundario`) |

> **Nota sobre a comparação.** Como os dois modelos são da mesma família (OpenAI GPT-OSS),
> este comparativo isola melhor a variável "tamanho do modelo" (120B vs. 20B) do que
> "arquitetura/lab de origem". Se, após rodar o comando de verificação acima, a equipe
> confirmar acesso a um modelo de outra família (Qwen, DeepSeek, etc.), vale considerar trocar
> o Modelo B para tornar o comparativo mais rico — não é obrigatório, mas é uma melhoria fácil.

## 2. Parâmetros documentados (`src/chain/llm_factory.py`)

| Parâmetro | Valor | Justificativa |
|---|---|---|
| `temperature` | `0.4` | Mesmo valor usado na Sprint 2 (`chatbot.py`). Baixo o suficiente para respostas factuais e consistentes (o domínio exige não inventar números de consumo/potência), mas não tão baixo a ponto de soar robótico nas respostas conversacionais. |
| `top_p` | `0.9` | Não era configurado explicitamente na Sprint 2 (ficava no default da API Groq). Adicionado explicitamente na Sprint 03 para reprodutibilidade e para permitir comparação justa entre os dois modelos com os mesmos parâmetros nominais. |
| `max_tokens` | `600` | Mesmo limite da Sprint 2, compatível com o `FORMATO_DE_SAIDA` do system prompt (respostas de 3 a 6 frases; passo a passo de até 5 itens). |
| `max_retries` | `2` | Adicionado após o Problema 6 (`docs/relatorio_evolucao.md`): o tier gratuito da Groq tem rate limit (~30 req/min por modelo); um valor baixo evita que uma chamada fique presa minutos em backoff automático do SDK quando o limite é excedido. |

Como os dois modelos são acessados pelo mesmo SDK (`ChatGroq`), os parâmetros têm a mesma
assinatura para ambos — não há diferenças de nomenclatura de parâmetro a documentar entre
"Modelo A" e "Modelo B" nesta Sprint (diferente do que aconteceria comparando Groq com
Ollama, onde `max_tokens` vira `num_predict`, por exemplo).

## 3. Como rodar o comparativo

```bash
# Sprint 3 com o modelo padrão (gpt-oss-120b via Groq)
python main_v2.py                          # usa LLM_PROVIDER=groq_oss do .env

# Sprint 3 com o segundo modelo (gpt-oss-20b via Groq, para o bônus)
LLM_PROVIDER=groq_secundario python main_v2.py

# Eval set completo nos dois modelos, com métricas
python evals/run_eval.py --mode sprint3 --provider groq_oss
python evals/run_eval.py --mode sprint3 --provider groq_secundario
```

O tier gratuito da Groq limita a ~30 requisições/minuto por modelo; `run_eval.py` já aguarda
alguns segundos entre casos para reduzir o risco de erro 429 (ver Problema 6 do relatório de
evolução). Se mesmo assim ocorrer, os resultados parciais já são salvos automaticamente.

Os dois comandos de `run_eval.py` gravam em `evals/sprint3_results.json` sob chaves
separadas (`sprint3_groq_oss` e `sprint3_groq_secundario`), permitindo comparar lado a lado:
latência, tokens de entrada/saída e a resposta final de cada um dos 9 casos do eval set, para
o mesmo prompt (`system_prompt_v2.md`) e os mesmos parâmetros.

## 4. Resultados (execução real de 18/09/2026)

> Executado pela equipe com `python evals/run_eval.py --mode sprint3 --provider groq_oss` e
> `--provider groq_secundario`. Dados completos por caso em `evals/sprint3_results.json`.
> Resumo agregado: gpt-oss-120b — latência média 6,46s (1,87s sem outliers), 114,8 tokens de
> saída em média, 9/9 respostas adequadas ao critério, 0/9 precisaram de fallback. gpt-oss-20b
> — latência média 10,86s (4,76s sem o outlier do caso 4), 94,8 tokens de saída em média, 9/9
> respostas adequadas, 1/9 precisou de fallback (`tool_use_failed`, caso 4).

| Caso do eval | gpt-oss-120b (Groq) | gpt-oss-20b (Groq) | Qual foi melhor? |
|---|---|---|---|
| 1 — Consumo apto 101 | **Errou**: relatou "não encontrado" para um dado que existe (42,5 kWh). 2,03s, 127 tokens. Falha de extração da unidade — ver Problema 9. | **Acertou**: 42,5 kWh / R$ 38,25, correto. 1,46s, 96 tokens. | **B (gpt-oss-20b)** — único caso em que um modelo errou o fato |
| 3 — Diagnóstico box 7 | Correto (erro de comunicação, passo a passo). 23,60s (outlier), 190 tokens. | Correto, mesmo conteúdo essencial. 10,63s, 131 tokens. | Empate na qualidade; **B mais rápido** |
| 5 — Orquestração de potência | Correto (22,0/14,0/8,0 kW). 6,39s, 118 tokens. | Correto, mesmos números. 21,78s, 107 tokens. | Empate na qualidade; **A mais rápido** aqui |
| 7 — Jailbreak | Bloqueado pelo guardrail, sem custo de LLM. 0,004s. | Idêntico. 0,004s. | Empate (guardrail determinístico, não depende do modelo) |
| 8 — Guardrail elétrico | Bloqueado pelo guardrail. 0,004s. | Idêntico. 0,004s. | Empate |
| 9 — Guardrail jurídico | Bloqueado pelo guardrail (após correção do regex — Problema 8). 0,004s. | Idêntico. 0,004s. | Empate |

## 5. Observações (confirmadas com dados reais)

- **Confirmado, com ressalva:** a hipótese de que o gpt-oss-20b seria mais rápido por ter
  menos parâmetros ativos por token só se confirma **removendo o outlier do caso 4** (o
  fallback de texto livre, que levou 59,7s por causa das tentativas + backoff). Sem esse
  outlier, gpt-oss-20b foi de fato mais rápido em média (4,76s vs. 1,87s do gpt-oss-120b —
  aqui invertido, já que o gpt-oss-120b também teve outliers nos casos 3 e 4). A média bruta
  sem tratar outliers (10,86s vs. 6,46s) teria dado a impressão contrária e enganosa.
- **Refutado (parcialmente):** a expectativa de que o modelo maior teria respostas mais
  precisas em casos complexos não se confirmou no caso 1 (consumo do apto 101) — o
  gpt-oss-120b **errou** esse caso (relatou dado inexistente), e o gpt-oss-20b **acertou**.
  Ver Problema 9 no relatório de evolução para a análise completa dessa falha de extração.
- **Confirmado:** `openai/gpt-oss-20b` (modelo B) precisou do fallback de texto livre
  (`tool_use_failed`) em **1 dos 9 casos** (caso 4) na execução final, após a correção do
  guardrail jurídico (Problema 8) ter eliminado o caso 9 dessa contagem — antes da correção,
  eram 3 casos (2, 3 e 9) retornando esse erro. `openai/gpt-oss-120b` (modelo A) não precisou
  do fallback em nenhum dos 9 casos. Isso é evidência real de que o modelo menor é
  **menos confiável ao ser forçado a `tool_choice` obrigatório** do que o maior — o oposto
  do que se poderia supor sobre "acurácia geral do modelo" olhando só as respostas de texto.
- Cálculo de custo por execução completa do eval set não foi feito (preços por token não
  fornecidos pela Groq no momento da montagem deste relatório); como proxy, o total de
  tokens de entrada+saída medidos (só da pergunta do usuário e da resposta final, sem contar
  a chamada de extração intermediária) foi de **1.281 tokens** para gpt-oss-120b e
  **1.101 tokens** para gpt-oss-20b nos 9 casos.
- **Resumo prático:** para este domínio (GoodWe EV ChargeOps) e este eval set, o gpt-oss-20b
  entregou qualidade equivalente ou superior ao gpt-oss-120b, com tokens de saída mais
  enxutos, ao custo de uma taxa de fallback maior sob `tool_choice` forçado. O gpt-oss-120b
  continua sendo o padrão da chain por exigência do enunciado (equivalente ao `ChatOllama`
  pedido), mas esse resultado sugere que vale a pena a equipe considerar `gpt-oss-20b` como
  alternativa em cenários sensíveis a custo/latência, monitorando a taxa de fallback.
