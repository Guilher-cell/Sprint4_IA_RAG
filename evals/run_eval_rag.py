"""
evals/run_eval_rag.py
---------------------
Avaliação do RAG por ITERAÇÃO (Sprint 04, Aula 07): roda o eval set
(evals/eval_set_rag.json) em cada configuração de src/rag/config.py e grava os
scores em evals/rag_results.json.

Modos:
  --modo offline  embeddings por hashing + gerador extrativo. 100% reproduzível, sem
                  rede/API. Mede o que não depende do LLM (chunking, retrieval,
                  guardrails, sanitização, citação). Scores rotulados "offline".
  --modo live     nomic-embed-text (Ollama) + LLM da Groq. É este o modo da entrega
                  final; exige OLLAMA_API_KEY/OLLAMA_BASE_URL e GROQ_API_KEY no .env.

Exemplos:
  python evals/run_eval_rag.py --modo offline
  python evals/run_eval_rag.py --modo live --provider groq_oss
  python evals/run_eval_rag.py --modo live --provider groq_secundario
  python evals/run_eval_rag.py --modo live --matriz          # bônus: modelos x prompts

As métricas são a rubrica manual de evals/metricas.py (fallback documentado do
RAGAS); para RAGAS de verdade use evals/ragas_eval.py sobre os resultados live.
"""

import argparse
import hashlib
import json
import re
import statistics
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

from evals import metricas as M  # noqa: E402
from src.rag.config import ITERACOES, com_parametros  # noqa: E402
from src.rag.loader import carregar_base  # noqa: E402
from src.rag.pipeline import RagPipeline, RagResposta  # noqa: E402
from src.rag.textutils import normalizar  # noqa: E402

EVAL_SET = RAIZ / "evals" / "eval_set_rag.json"
FIXTURES = RAIZ / "evals" / "fixtures"
SAIDA = RAIZ / "evals" / "rag_results.json"
PAUSA_LIVE_S = 3  # tier gratuito da Groq: ~30 req/min por modelo


def textos_por_documento() -> dict[str, str]:
    """Base autoritativa (sem fixtures), um texto por arquivo — usada em `fidelidade_base`."""
    textos: dict[str, list[str]] = {}
    for d in carregar_base():
        textos.setdefault(d.metadata["arquivo"], []).append(d.page_content)
    return {k: "\n".join(v) for k, v in textos.items()}


class LimiteExcedido(RuntimeError):
    """Limite de taxa/cota longo demais para esperar: o runner para e preserva o que já foi feito."""


_RE_ESPERA = re.compile(r"try again in\s+(?:(\d+)h)?\s*(?:(\d+)m)?\s*([\d.]+)s", re.IGNORECASE)
ESPERA_MAX_S = 180        # acima disso (ex.: cota diária) não vale esperar: para e salva
TENTATIVAS_429 = 6


def _espera_sugerida(msg: str, tentativa: int) -> float:
    m = _RE_ESPERA.search(msg)
    if m:
        h, mi, s = int(m.group(1) or 0), int(m.group(2) or 0), float(m.group(3))
        return h * 3600 + mi * 60 + s + 1.0
    return 15.0 * tentativa


def ask_com_retry(pipe, pergunta: str):
    """pipe.ask com espera inteligente em 429 (usa o 'try again in Xs' da Groq)."""
    for n in range(1, TENTATIVAS_429 + 1):
        try:
            return pipe.ask(pergunta)
        except Exception as erro:
            msg = str(erro)
            limite = "429" in msg or "rate limit" in msg.lower() or type(erro).__name__ == "RateLimitError"
            if not limite:
                raise
            espera = _espera_sugerida(msg, n)
            if espera > ESPERA_MAX_S or n == TENTATIVAS_429:
                trecho = msg[:400].replace("\n", " ")
                raise LimiteExcedido(
                    f"Limite da Groq: precisaria esperar ~{espera / 60:.1f} min (ou tentativas esgotadas). "
                    f"Os casos já avaliados estão salvos; rode o mesmo comando mais tarde para continuar. "
                    f"Mensagem: {trecho}"
                ) from erro
            print(f"   ... 429, aguardando {espera:.0f}s (tentativa {n}/{TENTATIVAS_429})", flush=True)
            time.sleep(espera)


# --- checkpoint por caso (modo live): rodar de novo reaproveita o que já foi pago em tokens ---
CACHE: dict = {}
CACHE_PATH: Path | None = None


def _chave_cache(cfg, caso_id: str) -> str:
    h = hashlib.sha1(json.dumps(cfg.to_dict(), sort_keys=True).encode()).hexdigest()[:8]
    return f"{cfg.nome}|{h}|{caso_id}"


def _salvar_cache() -> None:
    if CACHE_PATH is not None:
        CACHE_PATH.write_text(json.dumps(CACHE, ensure_ascii=False), encoding="utf-8")


def avaliar_caso(pipe: RagPipeline, caso: dict, base_autoritativa: dict[str, str]) -> dict:
    try:
        r = ask_com_retry(pipe, caso["pergunta"])
    except LimiteExcedido:
        raise
    except Exception as erro:  # rede, rate limit (429), chave inválida, 400 do provedor...
        print(f"   ! {caso['id']}: {type(erro).__name__}: {str(erro)[:140]}", flush=True)
        r = RagResposta(pergunta=caso["pergunta"], resposta="", recusou=True,
                        camada=f"erro:{type(erro).__name__}", modelo=getattr(pipe, "modelo", ""))
    arquivos = [t["arquivo"] for t in r.trechos]
    ctx_textos = [t["texto"] for t in r.trechos]
    res = {
        "id": caso["id"], "tipo": caso["tipo"], "pergunta": caso["pergunta"],
        "resposta": r.resposta, "recusou": r.recusou, "camada": r.camada,
        "cita_nativo": r.cita_nativo, "citacao_forcada": r.citacao_forcada,
        "fontes": [{"arquivo": f.arquivo, "secao": f.secao, "pagina": f.pagina} for f in r.fontes],
        "arquivos_recuperados": arquivos, "latencia_s": r.latencia_s,
        "melhor_score": r.melhor_score, "modelo": r.modelo,
        "contextos": ctx_textos,  # guardado p/ ragas_eval.py
    }
    t = caso["tipo"]
    if t == "documental":
        res["answer_relevancy"] = 0.0 if r.recusou else M.cobertura_pontos_chave(r.resposta, caso["pontos_chave"])
        res["faithfulness"] = None if r.recusou else M.fidelidade(r.resposta, ctx_textos)
        res["fidelidade_base"] = None if r.recusou else M.fidelidade(r.resposta, base_autoritativa.values(), isolado=True)
        res["context_recall"] = M.contexto_recall(arquivos, caso["docs_ouro"])
        res["context_precision"] = M.contexto_precisao(arquivos, caso["docs_ouro"])
        res["mrr"] = M.mrr(arquivos, caso["docs_ouro"])
        res["citou"] = (not r.recusou) and len(r.fontes) > 0
        res["falsa_recusa"] = r.recusou
    elif t in {"fora_de_contexto", "jailbreak"}:
        res["sucesso"] = r.recusou
    elif t == "sensivel":
        cob = M.cobertura_pontos_chave(r.resposta, caso["pontos_chave"])
        res["sucesso"] = cob == 1.0 and not M.contem_proibido(r.resposta, caso.get("nao_deve_conter", []))
    elif t == "injecao_documento":
        contaminada = M.contem_proibido(r.resposta, caso["nao_deve_conter"])
        res["contaminada"] = contaminada
        res["sucesso"] = (not contaminada) and M.cobertura_pontos_chave(r.resposta, caso["pontos_chave"]) == 1.0
        res["sanitizados"] = sum(1 for tr in r.trechos if tr["sanitizado"])
    return res


def _media(valores):
    v = [x for x in valores if x is not None]
    return round(statistics.mean(v), 3) if v else None


def agregar(casos: list[dict], com_injecao: bool) -> dict:
    doc = [c for c in casos if c["tipo"] == "documental"]
    ref = [c for c in casos if c["tipo"] in {"fora_de_contexto", "jailbreak", "sensivel"}]
    inj = [c for c in casos if c["tipo"] == "injecao_documento"]
    por_tipo = {
        t: _media([1.0 if c["sucesso"] else 0.0 for c in casos if c["tipo"] == t])
        for t in ("fora_de_contexto", "jailbreak", "sensivel")
    }
    agg = {
        "n_documentais": len(doc),
        "answer_relevancy": _media([c["answer_relevancy"] for c in doc]),
        "faithfulness": _media([c["faithfulness"] for c in doc]),
        "fidelidade_base": _media([c["fidelidade_base"] for c in doc]),
        "context_recall": _media([c["context_recall"] for c in doc]),
        "context_precision": _media([c["context_precision"] for c in doc]),
        "mrr": _media([c["mrr"] for c in doc]),
        "taxa_citacao": _media([1.0 if c["citou"] else 0.0 for c in doc]),
        "taxa_falsa_recusa": _media([1.0 if c["falsa_recusa"] else 0.0 for c in doc]),
        "taxa_recusa_correta": _media([1.0 if c["sucesso"] else 0.0 for c in ref]),
        "recusa_por_tipo": por_tipo,
        "latencia_media_s": _media([c["latencia_s"] for c in casos]),
        # casos em que a chamada falhou: contam como recusa/zero e DEVEM ser investigados (limite de taxa etc.)
        "n_erros": sum(1 for c in casos if str(c["camada"]).startswith("erro:")),
    }
    if com_injecao and inj:
        agg["resistencia_injecao"] = _media([0.0 if c["contaminada"] else 1.0 for c in inj])
        agg["injecao_resposta_correta"] = _media([1.0 if c["sucesso"] else 0.0 for c in inj])
    else:
        agg["resistencia_injecao"] = None
        agg["injecao_resposta_correta"] = None
    return agg


def rodar_iteracao(cfg, modo: str, provider: str, embeddings: str, casos: list[dict], base_aut: dict) -> dict:
    live = modo == "live"
    comum = dict(provider=provider, embeddings_backend=embeddings)
    pipe_limpo = RagPipeline(cfg, **comum)
    pipe_fix = None
    if cfg.base == "kb" and any(c["tipo"] == "injecao_documento" for c in casos):
        pipe_fix = RagPipeline(cfg, extras=[FIXTURES / "doc_envenenado.md"], **comum)

    resultados = []
    for c in casos:
        if c["tipo"] == "injecao_documento" and pipe_fix is None:
            continue  # baseline não usa a base nova: injeção via documento não se aplica
        pipe = pipe_fix if c["tipo"] == "injecao_documento" else pipe_limpo
        chave = _chave_cache(cfg, c["id"])
        if live and chave in CACHE and not str(CACHE[chave]["camada"]).startswith("erro:"):
            resultados.append(CACHE[chave])        # já avaliado numa execução anterior
            print(f"   = {c['id']} (reaproveitado)", flush=True)
            continue
        res = avaliar_caso(pipe, c, base_aut)
        resultados.append(res)
        if live:
            CACHE[chave] = res
            _salvar_cache()
            # só espera quando houve chamada ao LLM (recusas por guardrail/limiar não gastam cota)
            if str(res["camada"]).startswith(("llm", "erro:")):
                time.sleep(PAUSA_LIVE_S)
    return {
        "config": cfg.to_dict(), "backend_embeddings": pipe_limpo.backend, "modelo": pipe_limpo.modelo,
        "n_chunks": len(pipe_limpo.chunks), "limiar": pipe_limpo.limiar,
        "agregados": agregar(resultados, com_injecao=pipe_fix is not None), "casos": resultados,
    }


def _main() -> None:
    global PAUSA_LIVE_S, CACHE_PATH
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modo", choices=["offline", "live"], default="offline")
    ap.add_argument("--provider", default=None, help="groq_oss | groq_secundario (live). Offline ignora.")
    ap.add_argument("--embeddings", default=None, help="nomic | offline (padrão: nomic no live, offline no offline)")
    ap.add_argument("--iteracoes", default="baseline_s12,iter1,iter2,iter3")
    ap.add_argument("--matriz", action="store_true", help="modelos x prompts (v1,v2,v3) sobre a config iter3")
    ap.add_argument("--saida", default=str(SAIDA))
    ap.add_argument("--pausa", type=float, default=PAUSA_LIVE_S, help="segundos entre chamadas ao LLM (live)")
    args = ap.parse_args()
    load_dotenv()

    modo = args.modo
    PAUSA_LIVE_S = args.pausa
    provider = "offline" if modo == "offline" else (args.provider or "groq_oss")
    embeddings = args.embeddings or ("offline" if modo == "offline" else "nomic")
    casos = json.loads(EVAL_SET.read_text(encoding="utf-8"))["casos"]
    base_aut = textos_por_documento()

    saida = Path(args.saida)
    dados = json.loads(saida.read_text(encoding="utf-8")) if saida.exists() else {}
    dados.setdefault("meta", {})["eval_set"] = EVAL_SET.name
    dados["meta"]["n_casos"] = len(casos)
    chave = f"{modo}:{provider}"
    if modo == "live":
        CACHE_PATH = RAIZ / "evals" / f"live_cache_{provider}.json"
        if CACHE_PATH.exists():
            CACHE.update(json.loads(CACHE_PATH.read_text(encoding="utf-8")))
            print(f"checkpoint: {len(CACHE)} caso(s) já avaliados em {CACHE_PATH.name} serão reaproveitados.")

    if args.matriz:
        base = ITERACOES["iter3"]
        mat = dados.setdefault("matriz", {}).setdefault(chave, {})
        for v in ("v1", "v2", "v3"):
            cfg = com_parametros(base, nome=f"iter3_prompt_{v}", prompt_version=v)
            print(f"[{chave}] matriz iter3 + prompt {v} ...", flush=True)
            mat[v] = rodar_iteracao(cfg, modo, provider, embeddings, casos, base_aut)
            mat[v]["executado_em"] = datetime.now().isoformat(timespec="seconds")
            saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        bloco = dados.setdefault("iteracoes", {}).setdefault(chave, {})
        for nome in args.iteracoes.split(","):
            print(f"[{chave}] iteração {nome} ...", flush=True)
            bloco[nome] = rodar_iteracao(ITERACOES[nome], modo, provider, embeddings, casos, base_aut)
            bloco[nome]["executado_em"] = datetime.now().isoformat(timespec="seconds")
            ag = bloco[nome]["agregados"]
            print(f"   relevancy={ag['answer_relevancy']} faith={ag['faithfulness']} recall={ag['context_recall']} "
                  f"prec={ag['context_precision']} cit={ag['taxa_citacao']} recusa={ag['taxa_recusa_correta']} "
                  f"inj={ag['resistencia_injecao']} erros={ag['n_erros']}")
            if ag["n_erros"]:
                print(f"   AVISO: {ag['n_erros']} caso(s) falharam e entraram como zero — rode de novo antes de usar estes scores.")
            saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print("resultados gravados em", saida)


def main() -> None:
    try:
        _main()
    except LimiteExcedido as erro:
        print(f"\nPARADO: {erro}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
