"""
measure_tokens.py
------------------
Mede o tamanho (em tokens) do system prompt v1 (Sprint 2) vs v2 (Sprint 3),
usando tiktoken como tokenizador de referência (Aula 04 - Context Engineering).

Nota: gpt-oss:120b (Ollama) não expõe publicamente um tokenizador equivalente
ao cl100k_base da OpenAI. Usamos cl100k_base apenas como referência comparativa
consistente entre as duas versões do prompt — não como contagem exata de tokens
do modelo real usado na chain. Ainda assim, é uma medição muito mais confiável
do que a estimativa por caracteres/4 usada no ambiente de montagem deste pacote
(sem acesso de rede ao download do vocabulário tiktoken).

Execução: python evals/measure_tokens.py
"""

from pathlib import Path

import tiktoken

RAIZ = Path(__file__).resolve().parents[1]
PROMPTS_DIR = RAIZ / "prompts"


def medir(caminho: Path, enc) -> dict:
    texto = caminho.read_text(encoding="utf-8")
    return {
        "arquivo": caminho.name,
        "caracteres": len(texto),
        "palavras": len(texto.split()),
        "tokens_cl100k_base": len(enc.encode(texto)),
    }


def main() -> None:
    enc = tiktoken.get_encoding("cl100k_base")

    v1 = medir(PROMPTS_DIR / "system_prompt_v1.md", enc)
    v2 = medir(PROMPTS_DIR / "system_prompt_v2.md", enc)

    print("=" * 60)
    print("Medição de tokens - system prompt v1 (Sprint 2) vs v2 (Sprint 3)")
    print("=" * 60)
    for r in (v1, v2):
        print(
            f"{r['arquivo']:<24} "
            f"{r['caracteres']:>6} chars  "
            f"{r['palavras']:>5} palavras  "
            f"{r['tokens_cl100k_base']:>5} tokens"
        )

    delta_tokens = v2["tokens_cl100k_base"] - v1["tokens_cl100k_base"]
    pct = 100 * delta_tokens / v1["tokens_cl100k_base"]
    print("-" * 60)
    print(f"Delta de tokens (v2 - v1): {delta_tokens} ({pct:+.1f}%)")
    print(
        "\nAtualize prompts/VERSOES.md e docs/relatorio_evolucao.md com estes "
        "números reais (substituindo a estimativa por caracteres/4)."
    )


if __name__ == "__main__":
    main()
