"""
evals/calibrar_limiar.py
------------------------
Ajuda a escolher o limiar de relevância (RAG_LIMIAR) para o backend de embeddings em
uso. Imprime a distribuição do melhor score recuperado para perguntas respondíveis
(Q*) e para perguntas fora do contexto (F*), na configuração iter3.

Por que existe: cosseno do nomic-embed-text e cosseno do embedding offline têm escalas
diferentes. O limiar padrão do backend offline (0.22) foi fixado ANTES de olhar os
scores do eval set; o do nomic (0.55) é só um ponto de partida e DEVE ser recalibrado
aqui ao rodar com EMBEDDINGS_BACKEND=nomic.

Cuidado metodológico: calibrar e avaliar no mesmo eval set superestima a qualidade.
Escolha o limiar com margem (ponto médio entre o menor score respondível e o maior
fora de contexto) e registre isso no relatório.

Uso:  python evals/calibrar_limiar.py [--embeddings nomic|offline]
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

from src.rag.config import ITERACOES, com_parametros  # noqa: E402
from src.rag.pipeline import RagPipeline  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embeddings", default=None)
    args = ap.parse_args()
    load_dotenv()

    cfg = com_parametros(ITERACOES["iter3"], usar_limiar=False, checar_entidades=False, guardrails_regex=False)
    pipe = RagPipeline(cfg, provider="offline", embeddings_backend=args.embeddings)
    casos = json.loads((RAIZ / "evals" / "eval_set_rag.json").read_text(encoding="utf-8"))["casos"]

    resp, fora = [], []
    for c in casos:
        if c["tipo"] == "documental":
            resp.append((pipe.recuperar(c["pergunta"])[0].score, c["id"]))
        elif c["tipo"] == "fora_de_contexto":
            fora.append((pipe.recuperar(c["pergunta"])[0].score, c["id"]))
    resp.sort(); fora.sort(reverse=True)
    print(f"backend: {pipe.backend} | limiar atual: {pipe.limiar}")
    print("respondíveis (menores):", [(i, round(s, 3)) for s, i in resp[:5]])
    print("fora do contexto (maiores):", [(i, round(s, 3)) for s, i in fora[:5]])
    margem = resp[0][0] - fora[0][0]
    print(f"menor respondível - maior fora = {margem:+.3f}  (ponto médio sugerido: {(resp[0][0] + fora[0][0]) / 2:.3f})")
    if margem <= 0:
        print("AVISO: as distribuições se sobrepõem; nenhum limiar separa os dois grupos sem custo.")


if __name__ == "__main__":
    main()
