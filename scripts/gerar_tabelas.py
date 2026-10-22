"""
scripts/gerar_tabelas.py
------------------------
Gera docs/tabelas_resultados.md (tabelas Markdown) a partir de:
  - evals/rag_results.json     (iterações offline e/ou live; matriz modelos x prompts)
  - evals/ragas_scores.json    (opcional: RAGAS real, se evals/ragas_eval.py foi executado)
  - evals/ablacao_results.json (opcional)

Use depois de rodar o modo live para copiar os números reais para os relatórios
(docs/relatorio_rag.md, docs/relatorio_modelos.md, docs/relatorio_evolucao_sprint4.md).

    python scripts/gerar_tabelas.py
"""

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
METRICAS = [
    ("answer_relevancy", "answer_relevancy"), ("faithfulness", "faithfulness"),
    ("fidelidade_base", "fidelidade_base"), ("context_recall", "context_recall"),
    ("context_precision", "context_precision"), ("mrr", "MRR"), ("taxa_citacao", "taxa_citacao"),
    ("taxa_recusa_correta", "recusa_correta"), ("resistencia_injecao", "resist._injeção"),
    ("latencia_media_s", "latência_média_s"),
]


def fmt(v):
    return "—" if v is None else (f"{v:.3f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v))


def tabela_iteracoes(titulo: str, bloco: dict) -> str:
    nomes = list(bloco)
    linhas = [f"### {titulo}", "", "| Métrica | " + " | ".join(nomes) + " |", "|---|" + "---|" * len(nomes)]
    for chave, rotulo in METRICAS:
        linhas.append(f"| {rotulo} | " + " | ".join(fmt(bloco[n]["agregados"].get(chave)) for n in nomes) + " |")
    linhas.append("| nº de chunks | " + " | ".join(str(bloco[n]["n_chunks"]) for n in nomes) + " |")
    linhas.append("| embeddings / geração | " + " | ".join(
        f"{bloco[n]['backend_embeddings']} / {bloco[n]['modelo']}" for n in nomes) + " |")
    return "\n".join(linhas) + "\n"


def main() -> None:
    saida = ["# Tabelas de resultados (geradas por scripts/gerar_tabelas.py)\n"]
    rr = RAIZ / "evals" / "rag_results.json"
    if rr.exists():
        dados = json.loads(rr.read_text(encoding="utf-8"))
        for chave, bloco in dados.get("iteracoes", {}).items():
            saida.append(tabela_iteracoes(f"Iterações — `{chave}`", bloco))
        for chave, mat in dados.get("matriz", {}).items():
            saida.append(tabela_iteracoes(f"Matriz modelo × prompt — `{chave}` (iter3 com prompt v1/v2/v3)", mat))
    rg = RAIZ / "evals" / "ragas_scores.json"
    if rg.exists():
        saida.append("### RAGAS (LLM-juiz) — faithfulness e answer_relevancy\n")
        saida.append("| Execução | Iteração | faithfulness | answer_relevancy | n |\n|---|---|---|---|---|")
        for chave, its in json.loads(rg.read_text(encoding="utf-8")).items():
            for it, v in its.items():
                saida.append(f"| {chave} | {it} | {v['faithfulness']} | {v['answer_relevancy']} | {v['n']} |")
        saida.append("")
    ab = RAIZ / "evals" / "ablacao_results.json"
    if ab.exists():
        d = json.loads(ab.read_text(encoding="utf-8"))
        cols = ["answer_relevancy", "context_recall", "context_precision", "mrr", "taxa_citacao",
                "taxa_recusa_correta", "resistencia_injecao"]
        saida.append(f"### Ablação da iter3 (`{d['modo']}`)\n")
        saida.append("| Variante | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols))
        for nome, ag in d["resultados"].items():
            saida.append(f"| {nome} | " + " | ".join(fmt(ag.get(c)) for c in cols) + " |")
        saida.append("")
    destino = RAIZ / "docs" / "tabelas_resultados.md"
    destino.write_text("\n".join(saida), encoding="utf-8")
    print("gerado:", destino.relative_to(RAIZ))


if __name__ == "__main__":
    main()
