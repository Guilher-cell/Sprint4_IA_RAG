"""
evals/run_ablacao.py
--------------------
ABLAÇÃO da iteração iter3 (Sprint 04): desliga UM componente por vez e mede o efeito no mesmo
eval set, para atribuir o ganho a decisões concretas em vez de ao "pacote" inteiro.

    python evals/run_ablacao.py            # modo offline (reproduzível, sem rede)
    python evals/run_ablacao.py --modo live --provider groq_oss

Saída: evals/ablacao_results.json  (+ tabela Markdown no stdout)
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

from evals.run_eval_rag import EVAL_SET, rodar_iteracao, textos_por_documento  # noqa: E402
from src.rag.config import ITERACOES, com_parametros  # noqa: E402

# nome -> mudanças aplicadas sobre iter3 (cada uma desliga/reverte UM componente)
ABLACOES = {
    "iter3 (completa)": {},
    "- rerank lexical": {"rerank": False},
    "- limiar de relevância": {"usar_limiar": False},
    "- checagem de entidades": {"checar_entidades": False},
    "- sanitização de contexto": {"sanitizar_contexto": False},
    "- guardrails regex (S03)": {"guardrails_regex": False},
    "- chunking por seção/prefixo": {"chunk_por_secao": False, "prefixar_secao": False},
    "- overlap (100 -> 0)": {"chunk_overlap": 0},
}
COLUNAS = ["answer_relevancy", "context_recall", "context_precision", "mrr", "taxa_citacao",
           "taxa_recusa_correta", "resistencia_injecao"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["offline", "live"], default="offline")
    ap.add_argument("--provider", default=None)
    args = ap.parse_args()
    load_dotenv()

    provider = "offline" if args.modo == "offline" else (args.provider or "groq_oss")
    embeddings = "offline" if args.modo == "offline" else "nomic"
    casos = json.loads(EVAL_SET.read_text(encoding="utf-8"))["casos"]
    base_aut = textos_por_documento()

    saida, linhas = {}, []
    for nome, mud in ABLACOES.items():
        cfg = com_parametros(ITERACOES["iter3"], nome=nome, **mud)
        r = rodar_iteracao(cfg, args.modo, provider, embeddings, casos, base_aut)
        saida[nome] = r["agregados"]
        linhas.append((nome, r["agregados"]))
        print(f"{nome:32s}", *[f"{r['agregados'][c]}" for c in COLUNAS], flush=True)

    destino = RAIZ / "evals" / "ablacao_results.json"
    destino.write_text(json.dumps({"modo": f"{args.modo}:{provider}", "resultados": saida},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n| Variante | " + " | ".join(COLUNAS) + " |\n|---|" + "---|" * len(COLUNAS))
    for nome, ag in linhas:
        print(f"| {nome} | " + " | ".join(str(ag[c]) for c in COLUNAS) + " |")
    print("\nresultados gravados em", destino)


if __name__ == "__main__":
    main()
