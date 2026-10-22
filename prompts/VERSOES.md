# Versionamento do System Prompt — GoodWe EV ChargeOps

Este arquivo documenta a evolução do system prompt entre a Sprint 2 (`system_prompt_v1.md`,
migrado sem alterações de conteúdo do `system_prompt.py` original) e a Sprint 3
(`system_prompt_v2.md`, com **context engineering** via XML tagging, Aula 04 do Módulo 1).

## Tabela de versões

| Versão | Arquivo | O que mudou | Por quê | Ganho medido |
|---|---|---|---|---|
| v1 | `system_prompt_v1.md` | Baseline da Sprint 2. Prompt em texto corrido com seções em `# TITULO` (Markdown simples). | Era o formato original, herdado sem alterações do `system_prompt.py`. | 6.854 caracteres · 982 palavras · ≈1.714 tokens (estimativa char/4 — ver nota de metodologia abaixo). |
| v2 | `system_prompt_v2.md` | Reestruturado com **tags XML** (`<role>`, `<contexto_condominio>`, `<escopo_por_persona>` com sub-tags por persona, `<contexto_tecnico>`, `<regras_de_comportamento>`, `<formato_de_saida>`, `<escalada_humana>`, `<limites_e_seguranca>`). Frases redundantes entre seções foram condensadas (ex.: a comparação com eletroposto comercial, que aparecia repetida no v1, foi consolidada em um único bloco). Regra 7 (recusa de aconselhamento jurídico/financeiro/elétrico) foi adicionada explicitamente — exigência da Sprint 03 (§6) que não existia no v1. | 1) Tags XML dão ao modelo (e ao parser de extração) limites de seção inequívocos, reduzindo ambiguidade — prática recomendada de context engineering (Aula 04). 2) Consolidar redundâncias reduz tokens gastos por turno sem perder conteúdo. 3) A regra de guardrail de domínio sensível é um requisito novo da Sprint 03. | 5.884 caracteres (**-14,2%**) · 796 palavras (**-18,9%**) · ≈1.471 tokens estimados (**-14,2%**). |


## Para testar a contagem de tokens execute:
```bash
python evals/measure_tokens.py
```

