"""
src/chain/llm_factory.py
---------------------------
Factory de LLM para o comparativo multi-provider exigido pelo bônus da
Sprint 03 (§6): openai/gpt-oss-120b vs. openai/gpt-oss-20b.

DECISÃO DE ARQUITETURA (ver docs/relatorio_evolucao.md, Problema 4): a
equipe não tem hardware local para rodar gpt-oss-120b via Ollama (120B
parâmetros exigem GPU/RAM que a equipe não possui). Em vez disso, os DOIS
modelos são acessados via API da Groq (GroqCloud) — mesma GROQ_API_KEY,
mesmo SDK (`langchain-groq`), apenas o parâmetro `model` muda.

HISTÓRICO DE MODELOS QUE NÃO FUNCIONARAM (ver docs/relatorio_evolucao.md,
Problemas 5 e 7) — documentado aqui para quem for mexer neste arquivo:
  1. `llama-3.3-70b-versatile` (plano original, mesmo da Sprint 2):
     descontinuado pela Groq em 16/08/2026 -> 404 model_not_found.
  2. `qwen/qwen3.6-27b` (1ª tentativa de substituto, recomendado pela
     própria documentação de deprecação da Groq): existe na documentação
     pública, mas retornou "does not exist or you do not have access to
     it" na conta da equipe — provável modelo em preview/acesso restrito
     por conta/tier, não necessariamente removido do catálogo.
  3. Modelo atual (`openai/gpt-oss-20b`): parte do catálogo padrão (não
     preview) da Groq, com rate limits publicamente documentados
     (30 RPM / 1.000 RPD no tier gratuito) — mesma família do modelo A,
     o que reduz a "informatividade" do comparativo (duas variantes de
     tamanho do mesmo modelo, não duas famílias diferentes), mas prioriza
     a chain funcionar de fato sobre um modelo tentar-e-falhar outro nome.

Antes de rodar, confirme quais modelos a SUA chave de API realmente acessa:
    curl -s https://api.groq.com/openai/v1/models \
      -H "Authorization: Bearer $GROQ_API_KEY" | python3 -m json.tool
Se `qwen/qwen3.6-27b` (ou outro modelo) aparecer na lista, basta apontar
GROQ_MODEL_SECUNDARIO para ele no .env — não é necessário mexer no código.

O suporte a Ollama local é mantido no código (função `_get_ollama`, provider
"ollama") como caminho OPCIONAL, caso algum integrante tenha hardware
disponível no futuro — mas não é o caminho usado por padrão.

Os parâmetros (temperature, top_p, max_tokens) são os mesmos entre os dois
modelos por padrão, para que o comparativo em docs/relatorio_modelos.md
isole a variável "modelo", não "parâmetros". Ver esse arquivo para a tabela
de parâmetros e discussão dos resultados.
"""

import os
from typing import Optional

DEFAULT_TEMPERATURE = 0.4
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 600

# Free tier da Groq costuma limitar a ~30 RPM por modelo (ver
# docs/relatorio_evolucao.md, Problema 6). max_retries baixo evita que uma
# chamada fique presa minutos em backoff automático do SDK quando o limite
# é excedido — preferimos falhar rápido e deixar o chamador (run_eval.py)
# decidir o que fazer, com uma mensagem clara em vez de uma espera silenciosa.
GROQ_MAX_RETRIES = 2

# Os dois modelos exigidos/comparados, ambos hospedados na Groq (GroqCloud).
# GROQ_MODEL_SECUNDARIO é configurável via .env de propósito (ver histórico
# na docstring acima) — troque livremente se sua conta tiver acesso a um
# modelo diferente, sem precisar editar este arquivo.
GROQ_MODEL_OSS = "openai/gpt-oss-120b"
GROQ_MODEL_SECUNDARIO_PADRAO = "openai/gpt-oss-20b"

# Suporte opcional a Ollama local (não usado por padrão - ver docstring acima).
OLLAMA_DEFAULT_MODEL = "gpt-oss:120b"
OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"

PROVIDERS_VALIDOS = {"groq_oss", "groq_secundario", "ollama"}


def _get_groq(
    modelo: str, temperature: float, top_p: float, max_tokens: int
):
    from langchain_groq import ChatGroq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY não encontrada. Defina no .env (usada para "
            "'groq_oss' e 'groq_secundario', já que ambos os modelos são "
            "hospedados na Groq)."
        )
    return ChatGroq(
        model=modelo,
        api_key=api_key,
        temperature=temperature,
        model_kwargs={"top_p": top_p},
        max_tokens=max_tokens,
        max_retries=GROQ_MAX_RETRIES,
    )


def _get_ollama(
    modelo: Optional[str], temperature: float, top_p: float, max_tokens: int
):
    """Caminho OPCIONAL, só usado se alguém tiver Ollama local disponível."""
    from langchain_ollama import ChatOllama

    modelo = modelo or os.environ.get("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL)
    base_url = os.environ.get("OLLAMA_BASE_URL", OLLAMA_DEFAULT_BASE_URL)
    return ChatOllama(
        model=modelo,
        base_url=base_url,
        temperature=temperature,
        top_p=top_p,
        num_predict=max_tokens,
    )


def get_llm(
    provider: Optional[str] = None,
    *,
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_tokens: int = DEFAULT_MAX_TOKENS,
):
    """
    Retorna uma instância de chat model do LangChain, conforme `provider`
    (ou a variável de ambiente LLM_PROVIDER, default "groq_oss"):

      - "groq_oss"        -> ChatGroq com openai/gpt-oss-120b (padrão da
                             chain, equivalente funcional ao ChatOllama
                             exigido pelo enunciado)
      - "groq_secundario" -> ChatGroq com o modelo em GROQ_MODEL_SECUNDARIO
                             (.env), default openai/gpt-oss-20b — segundo
                             modelo do comparativo/bônus; TROQUE no .env se
                             sua conta tiver acesso a outro modelo (ver
                             comando de verificação na docstring do módulo)
      - "ollama"          -> ChatOllama local (opcional, requer servidor
                             Ollama rodando; não é o caminho padrão da equipe)

    Parâmetros documentados no relatorio_modelos.md:
      - temperature=0.4: mesma usada na Sprint 2, para manter respostas
        consistentes/factuais sem ficar robótico.
      - top_p=0.9: valor comumente recomendado como complemento à temperature
        moderada; não era configurado explicitamente na Sprint 2 (ficava no
        default da API Groq).
      - max_tokens=600: mesmo limite da Sprint 2, compatível com o
        FORMATO_DE_SAIDA (respostas curtas, 3 a 6 frases).
    """
    provider = (provider or os.environ.get("LLM_PROVIDER", "groq_oss")).lower()

    if provider not in PROVIDERS_VALIDOS:
        raise ValueError(
            f"Provider desconhecido: '{provider}'. Use um de: "
            f"{sorted(PROVIDERS_VALIDOS)}."
        )

    if provider == "groq_oss":
        modelo = model or os.environ.get("GROQ_MODEL_OSS", GROQ_MODEL_OSS)
        return _get_groq(modelo, temperature, top_p, max_tokens)

    if provider == "groq_secundario":
        modelo = model or os.environ.get(
            "GROQ_MODEL_SECUNDARIO", GROQ_MODEL_SECUNDARIO_PADRAO
        )
        return _get_groq(modelo, temperature, top_p, max_tokens)

    return _get_ollama(model, temperature, top_p, max_tokens)
