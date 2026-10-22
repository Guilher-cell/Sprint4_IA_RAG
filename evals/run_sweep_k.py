"""
evals/run_sweep_k.py
--------------------
Varre o parâmetro k (top-k) na configuração iter3 e mede o efeito no mesmo eval set
(documentado em docs/relatorio_modelos.md, exigência da Sprint 04 §6).

    python evals/run_sweep_k.py                 # offline, reproduzível
    python evals/run_sweep_k.py --modo live --provider groq_oss
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

KS = (1, 2, 3, 4, 6, 8)
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

    saida = {}
    for k in KS:
        r = rodar_iteracao(com_parametros(ITERACOES["iter3"], nome=f"iter3_k{k}", k=k),
                           args.modo, provider, embeddings, casos, base_aut)
        saida[f"k={k}"] = r["agregados"]
        print(f"k={k}", *[r["agregados"][c] for c in COLUNAS], flush=True)

    destino = RAIZ / "evals" / "sweep_k_results.json"
    destino.write_text(json.dumps({"modo": f"{args.modo}:{provider}", "resultados": saida},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n| k | " + " | ".join(COLUNAS) + " |\n|---|" + "---|" * len(COLUNAS))
    for k, ag in saida.items():
        print(f"| {k} | " + " | ".join(str(ag[c]) for c in COLUNAS) + " |")


if __name__ == "__main__":
    main()
