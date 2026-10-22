"""
evals/ragas_eval.py
-------------------
Avaliação RAGAS (faithfulness + answer_relevancy) sobre os resultados do modo LIVE
de evals/run_eval_rag.py (item 4 do escopo da Sprint 04).

Juiz: LLM da Groq (o mesmo `get_llm`); embeddings do answer_relevancy: nomic-embed-text.

STATUS (transparência): este script foi escrito contra a API do ragas 0.4.x, mas NÃO
foi executado no ambiente de montagem do pacote — lá não havia GROQ_API_KEY/Ollama e o
`import ragas` falhou por incompatibilidade com o langchain-community instalado
(`No module named 'langchain_community.chat_models.vertexai'`). É exatamente o cenário
em que o enunciado aceita o FALLBACK MANUAL (evals/metricas.py + evals/RUBRICA.md), que é
o que gera os scores de evals/rag_results.json. Se o ragas funcionar no seu ambiente,
rode este script e compare os dois conjuntos de scores no relatório.

Uso:
    python evals/run_eval_rag.py --modo live --provider groq_oss      # gera as respostas
    python evals/ragas_eval.py --provider groq_oss --iteracoes iter1,iter2,iter3
"""

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

RESULTADOS = RAIZ / "evals" / "rag_results.json"
SAIDA = RAIZ / "evals" / "ragas_scores.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="groq_oss")
    ap.add_argument("--iteracoes", default="iter1,iter2,iter3")
    args = ap.parse_args()
    load_dotenv()

    try:
        from ragas import EvaluationDataset, evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import Faithfulness, ResponseRelevancy
    except Exception as erro:  # ambiente sem ragas funcional
        sys.exit(
            f"RAGAS indisponível neste ambiente ({type(erro).__name__}: {erro}).\n"
            "Use o fallback manual: os scores de evals/rag_results.json já usam a rubrica de "
            "evals/RUBRICA.md (equivalente documentado)."
        )

    from src.chain.llm_factory import get_llm
    from src.rag.embeddings import get_embeddings

    chave = f"live:{args.provider}"
    dados = json.loads(RESULTADOS.read_text(encoding="utf-8"))
    if chave not in dados.get("iteracoes", {}):
        sys.exit(f"Sem resultados '{chave}' em rag_results.json. Rode antes: run_eval_rag.py --modo live.")

    juiz = LangchainLLMWrapper(get_llm(args.provider, temperature=0.0, max_tokens=1024))
    emb, _ = get_embeddings("nomic")
    metricas = [Faithfulness(), ResponseRelevancy()]

    saida = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    for nome in args.iteracoes.split(","):
        casos = [c for c in dados["iteracoes"][chave][nome]["casos"] if c["tipo"] == "documental" and not c["recusou"]]
        ds = EvaluationDataset.from_list(
            [{"user_input": c["pergunta"], "response": c["resposta"], "retrieved_contexts": c["contextos"]} for c in casos]
        )
        res = evaluate(ds, metrics=metricas, llm=juiz, embeddings=LangchainEmbeddingsWrapper(emb))
        df = res.to_pandas()
        saida.setdefault(chave, {})[nome] = {
            "faithfulness": round(float(df["faithfulness"].mean()), 3),
            "answer_relevancy": round(float(df["answer_relevancy"].mean()), 3),
            "n": len(casos),
        }
        print(nome, saida[chave][nome])
        time.sleep(2)
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
