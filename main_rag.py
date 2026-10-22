"""
main_rag.py
-----------
CLI do RAG da Sprint 04 (a interface principal é app/app.py).

    python main_rag.py                       # iter3, provider automático (Groq se houver chave; senão offline)
    python main_rag.py --iteracao iter2 --provider offline
    python main_rag.py --pergunta "Qual o limite de potência do condomínio?"
"""

import argparse
import warnings

from dotenv import load_dotenv

warnings.filterwarnings("ignore")


def formatar(r) -> str:
    saida = [f"\nGoodWe Assistant: {r.resposta}"]
    if r.fontes:
        saida.append("\nFontes citadas:")
        saida += [f"  [{f.id}] {f.arquivo} · {f.secao} · p. {f.pagina}" for f in r.fontes]
    saida.append(f"\n(camada: {r.camada} | modelo: {r.modelo} | embeddings: {r.backend_embeddings} | {r.latencia_s}s)")
    return "\n".join(saida)


def main() -> None:
    from src.rag.config import ITERACOES
    from src.rag.pipeline import RagPipeline

    ap = argparse.ArgumentParser()
    ap.add_argument("--iteracao", default="iter3", choices=list(ITERACOES))
    ap.add_argument("--provider", default="auto")
    ap.add_argument("--embeddings", default=None, help="nomic | offline | auto")
    ap.add_argument("--pergunta", default=None)
    args = ap.parse_args()
    load_dotenv()

    pipe = RagPipeline(ITERACOES[args.iteracao], provider=args.provider, embeddings_backend=args.embeddings)
    print("=" * 64)
    print(f"GoodWe EV ChargeOps — RAG Sprint 04 | {args.iteracao} | {pipe.modelo} | embeddings: {pipe.backend}")
    print(f"Base: {len(pipe.chunks)} trechos em ChromaDB persistente. 'sair' encerra.")
    print("=" * 64)

    if args.pergunta:
        print(formatar(pipe.ask(args.pergunta)))
        return
    while True:
        try:
            entrada = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if entrada.lower() in {"sair", "exit", "quit"}:
            break
        if entrada:
            try:
                print(formatar(pipe.ask(entrada)))
            except Exception as erro:
                print(f"[ERRO ao consultar o modelo] {erro}")


if __name__ == "__main__":
    main()
