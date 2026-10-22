# EV Challenge — GoodWe · Sprint 03

**Continuação do projeto entregue nas Sprints 1 e 2** (ver `README.md`, que documenta o
projeto original: contexto do desafio, personas, arquitetura legada e resultados de teste).
Este arquivo documenta **apenas o que a Sprint 03 pediu**: o refactory conversacional em
LangChain (Módulo 1, Aulas 01–04).

O código e os relatórios legados da Sprint 2 (`chatbot.py`, `tools.py`, `system_prompt.py`,
`modelo_de_testes.py`, `resultados_testes.md`) foram **mantidos intactos**, de propósito, para
servir de baseline real do comparativo antes/depois exigido nesta sprint.

---

## 1. Conceito atendido

> "Reconstruir o núcleo conversacional do chatbot em LangChain LCEL: chain
> `prompt | llm | parser`, memória por sessão com limite de tokens, saída estruturada
> Pydantic v2 validada e context engineering leve (XML tagging)."

Feito em `src/chain/builder.py`, `src/chain/memoria.py` e `src/schemas/`. O ganho é
demonstrado no comparativo antes/depois em `docs/relatorio_evolucao.md` (seção 3), com dados
reais das duas execuções (Sprint 2 e Sprint 03).

## 2. Escopo exigido × o que foi entregue

| # | Item exigido (Aula) | Onde está | Status |
|---|---|---|---|
| 1 | Chain LCEL end-to-end (`ChatPromptTemplate \| ChatOllama \| parser`) — Aula 01 | `src/chain/builder.py` | ✅ Entregue via `ChatGroq` com `openai/gpt-oss-120b` (equivalente funcional ao `ChatOllama` do enunciado — ver nota de arquitetura abaixo) |
| 2 | Memória por sessão, `RunnableWithMessageHistory` + limite de tokens, 3+ turnos — Aula 02 | `src/chain/memoria.py` (`TokenBufferChatMessageHistory`) | ✅ Entregue e testada |
| 3 | Structured output, schema Pydantic v2 com `field_validator` — Aula 03 | `src/schemas/consulta_recarga.py`, `src/schemas/resposta_chat.py` | ✅ Entregue, com `field_validator` e `model_validator` |
| 4 | Context engineering: prompt versionado (XML) + medição de tokens (tiktoken) — Aula 04 | `prompts/system_prompt_v2.md`, `prompts/VERSOES.md`, `evals/measure_tokens.py` | ✅ Entregue (-14,2% de caracteres do v1 para o v2, medição exata) |
| 5 | Segurança e guardrails: jailbreak/injection, escopo GoodWe | `src/guardrails/scope_validator.py`, `src/guardrails/moderation.py` | ✅ Entregue e testado (ver seção 4 abaixo) |
| 6 | Relatório de evolução do projeto (PDF, até 5 pág., comparativo antes/depois) | `docs/relatorio_evolucao.md` / `.pdf` / `.docx` | ✅ Entregue, com dados reais das duas execuções |
| — | Bônus: chamada multi-provider (2+ modelos, 2+ prompts) | `src/chain/llm_factory.py`, `docs/relatorio_modelos.md` | ✅ Entregue: `openai/gpt-oss-120b` e `openai/gpt-oss-20b`, ambos via Groq |

### Nota de arquitetura: por que Groq em vez de Ollama local

O enunciado especifica `ChatOllama (gpt-oss:120b)`. A equipe não tem hardware local capaz de
rodar um modelo de 120B parâmetros, então os dois modelos comparados são acessados via **API
da Groq**, que hospeda nativamente `openai/gpt-oss-120b` — mesmo modelo, execução remota em
vez de local. O suporte a `ChatOllama` continua implementado no código
(`provider="ollama"` em `llm_factory.py`) para quem tiver hardware disponível. Essa decisão,
e as tentativas de modelo que não funcionaram no caminho até aqui (`llama-3.3-70b-versatile`
descontinuado pela Groq; `qwen/qwen3.6-27b` sem acesso liberado na conta), estão documentadas
em detalhe em `docs/relatorio_evolucao.md`, Problemas 4, 5 e 7.

## 3. Estrutura de pastas criada 

```
prompts/                      # system prompt versionado + tabela de versões
  system_prompt_v1.md
  system_prompt_v2.md
  VERSOES.md
src/chain/                    # builder.py (LCEL) e memoria.py
  builder.py
  memoria.py
  llm_factory.py
src/schemas/                  # schema Pydantic v2 do domínio EV
  consulta_recarga.py
  resposta_chat.py
src/guardrails/                # scope_validator.py e moderation.py
  scope_validator.py
  moderation.py
src/data/                     # dados mockados (migrados de tools.py)
  mock_data.py
evals/                        # eval set reexecutado + resultados
  eval_set.json
  run_eval.py
  measure_tokens.py
  sprint3_results.json
docs/                         # relatório de evolução (PDF, até 5 pág.) + relatorio_modelos.md
  relatorio_evolucao.md / .pdf / .docx
  relatorio_modelos.md / .pdf / .docx
main_v2.py                    # entry point da Sprint 03 (CLI)
```

## 4. Segurança e guardrails 

| Exigência | Implementação | Evidência real |
|---|---|---|
| Recusa de jailbreak/prompt injection | `scope_validator.eh_tentativa_de_jailbreak` (regex, bloqueia antes de chamar o LLM) | Testado no eval set (caso 7): bloqueado em 0,004s, sem custo de API |
| Validação de escopo GoodWe | `scope_validator.eh_fora_de_escopo` + classificação `TipoConsulta.FORA_DE_ESCOPO` | Testado (caso 6): recusa educada, correta |
| Recusa de aconselhamento jurídico/financeiro sem orientar profissional habilitado | `moderation.verificar_dominio_sensivel` | Testado (caso 9): corrigido após um bug real de regex (ver Problema 8 no relatório) — hoje bloqueia corretamente |
| Recusa de aconselhamento de segurança elétrica sem orientar profissional habilitado | `moderation.verificar_dominio_sensivel` | Testado (caso 8): bloqueia e orienta eletricista/suporte GoodWe |
| Não inventar especificações de produto fora da base | Lookup determinístico em `src/data/mock_data.py`, nunca inventado pelo LLM | Ver Problema 9 no relatório: mesmo com lookup determinístico, a *extração* da unidade pode falhar — limitação documentada, não escondida |

## 5. Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env      # preencher GROQ_API_KEY
python main_v2.py         # usa LLM_PROVIDER=groq_oss (padrão) do .env
```

Para reexecutar o eval set e regenerar os relatórios com números atualizados:

```bash
python evals/measure_tokens.py
python evals/run_eval.py --mode sprint3 --provider groq_oss
python evals/run_eval.py --mode sprint3 --provider groq_secundario
python docs/_gerar_pdf.py   # regenera os PDFs a partir dos .md
```

Detalhes completos de configuração (variáveis de ambiente, troca de modelo, Ollama opcional)
estão no `README.md` original, seção 12, e em `docs/relatorio_modelos.md`.

## 6. Relatório de evolução do projeto

Ver `docs/relatorio_evolucao.md` (ou `.pdf`/`.docx`), com:
- Resumo da evolução (Sprint 1/2 → Sprint 03)
- Decisões técnicas e trade-offs do refactory
- Tabela de comparativo antes/depois, com dados reais das duas execuções (18/09/2026)
- **9 problemas reais** encontrados e resolvidos durante o desenvolvimento (não hipotéticos)
- Equipe e divisão de trabalho

## 7. Equipe e divisão de trabalho

| Integrante | RM | Tarefa principal |
|---|---|---|
| André Fujinaga | 569158 | Chain LCEL + Multi-provider |
| Arthur Machado | 569919 | Memória conversacional |
| Conrado Gracie | 569157 | Structured Output (Pydantic v2) |
| Guilherme Belo | 570079 | Context Engineering + Prompt Versionado |
| Renato Sandreschi | 569156 | Guardrails + Eval/Relatório |

---

*Para o contexto completo do projeto (Sprints 1 e 2), personas do sistema, arquitetura
legada e resultados de teste originais, ver `README.md`.*
