# Interface web — RAG GoodWe EV ChargeOps (Sprint 04 · Aula 08)

Interface **Gradio** que consome o mesmo `RagPipeline` do CLI (`main_rag.py`), com **citação de fonte visível**.

## Executar

Na **raiz do projeto**:

```bash
pip install -r requirements.txt
python app/app.py          # http://127.0.0.1:7860
```

Funciona sem chaves (modo offline: gerador extrativo + embeddings por hashing). Para usar o LLM e o nomic-embed-text,
preencha o `.env` (veja `.env.example`): `GROQ_API_KEY`, `OLLAMA_API_KEY`/`OLLAMA_BASE_URL`, `EMBEDDINGS_BACKEND=nomic`.

## O que a tela mostra

| Área | Conteúdo |
|---|---|
| Chat | a resposta, com marcadores `[n]` no texto, e logo abaixo **“Fontes citadas”**: `arquivo · seção · página` |
| Linha de status | iteração, gerador (LLM ou extrativo offline), backend de embeddings, k e a **camada que decidiu** (ex.: `guardrail_jailbreak`, `retrieval_sem_contexto`, `llm`) |
| Painel “Trechos recuperados” | cada trecho enviado ao prompt, com score e marca 🧹 quando o sanitizador removeu uma instrução embutida |
| Configuração (recolhida) | iteração (`baseline_s12`, `iter1`, `iter2`, `iter3`), geração (`auto`, `offline`, `groq_oss`, `groq_secundario`) e `k` |

## Perguntas para demonstrar

- *Como faço para agendar o carregamento para a madrugada?* → resposta com fonte do manual do morador.
- *O carregador do box 7 está com a luz vermelha piscando…* → fonte: manual de diagnóstico, seção de LEDs.
- *Posso abrir o quadro elétrico e mexer no disjuntor sozinho?* → recusa e orientação ao profissional habilitado.
- *Qual é a capital da Austrália?* → recusa (fora do escopo).
- Troque a iteração para `iter1` e repita: **nenhuma resposta traz fonte** e a pergunta do quadro elétrico é respondida em vez de recusada (não há guardrails) — é o “antes” do comparativo.

## Observações

- Se a chamada ao LLM falhar (rede, chave, rate limit), o erro aparece no chat em vez de derrubar a interface.
- A interface roda só em `127.0.0.1`; não há deploy público nesta entrega (o deploy é tema do Módulo 3).
