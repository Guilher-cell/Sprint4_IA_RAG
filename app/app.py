"""
app/app.py
----------
Interface web (Gradio) do RAG da Sprint 04 — Aula 08. Consome o mesmo `RagPipeline`
do CLI e mostra, para cada resposta:
  - a resposta com as citações [n] no texto;
  - as FONTES CITADAS (documento · seção · página) logo abaixo da resposta, no chat;
  - no painel lateral, os trechos recuperados com score e o que o guardrail/sanitizador fez.

Executar (na raiz do projeto):   python app/app.py      →  http://127.0.0.1:7860
Detalhes e variáveis de ambiente: app/README.md
"""

import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import gradio as gr  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from src.rag.config import ITERACOES, com_parametros  # noqa: E402
from src.rag.pipeline import RagPipeline  # noqa: E402

load_dotenv()

EXEMPLOS = [
    "Como faço para agendar o carregamento para a madrugada?",
    "O carregador do box 7 está com a luz vermelha piscando. O que significa?",
    "Quanto custa carregar 30 kWh na faixa econômica?",
    "Quem pode alterar o limite de potência do condomínio e com base em quê?",
    "Posso abrir o quadro elétrico e mexer no disjuntor sozinho?",
    "Qual é a capital da Austrália?",
]

_cache: dict[tuple, RagPipeline] = {}


def obter_pipeline(iteracao: str, provider: str, k: int) -> RagPipeline:
    chave = (iteracao, provider, k)
    if chave not in _cache:
        cfg = com_parametros(ITERACOES[iteracao], k=int(k))
        _cache[chave] = RagPipeline(cfg, provider=provider)
    return _cache[chave]


def _status(p: RagPipeline, camada: str = "") -> str:
    modo = "offline (extrativo, sem LLM)" if p.provider == "offline" else f"LLM: {p.modelo}"
    extra = f" · decisão: `{camada}`" if camada else ""
    return f"**Iteração** `{p.cfg.nome}` · **geração** {modo} · **embeddings** `{p.backend}` · **k** {p.cfg.k}{extra}"


def formatar_fontes(r) -> str:
    if not r.fontes:
        return ""
    linhas = [f"- **[{f.id}]** `{f.arquivo}` · {f.secao} · p. {f.pagina}" for f in r.fontes]
    return "\n\n---\n**Fontes citadas**\n" + "\n".join(linhas)


def formatar_trechos(r) -> str:
    if not r.trechos:
        return "_Nenhum trecho recuperado para esta pergunta._"
    blocos = []
    for t in r.trechos:
        marca = " 🧹 *sanitizado (instrução embutida removida)*" if t["sanitizado"] else ""
        blocos.append(
            f"**[{t['id']}] {t['arquivo']}** · {t['secao']} · p. {t['pagina']} · score {t['score']:.3f}{marca}\n\n"
            f"> {t['texto'][:420].replace(chr(10), ' ')}{'…' if len(t['texto']) > 420 else ''}"
        )
    return "\n\n".join(blocos)


def responder(mensagem, historico, iteracao, provider, k):
    historico = list(historico or [])
    if not (mensagem or "").strip():
        return historico, "", "", "", ""
    try:
        pipe = obter_pipeline(iteracao, provider, k)
        r = pipe.ask(mensagem)
        corpo = re.sub(r"\n*Fontes:.*$", "", r.resposta, flags=re.DOTALL) if r.fontes else r.resposta
        texto = corpo + formatar_fontes(r)
        status, trechos = _status(pipe, r.camada), formatar_trechos(r)
    except Exception as erro:  # rede, chave inválida, rate limit...
        texto = f"⚠️ Não consegui consultar o modelo: `{type(erro).__name__}: {erro}`"
        status, trechos = "**Erro** — veja a mensagem no chat.", ""
    historico += [{"role": "user", "content": mensagem}, {"role": "assistant", "content": texto}]
    return historico, "", status, trechos, ""


def construir_interface() -> gr.Blocks:
    with gr.Blocks(title="GoodWe EV ChargeOps · RAG") as demo:
        gr.Markdown(
            "# GoodWe EV ChargeOps — Assistente com RAG\n"
            "Responde **apenas com a base de conhecimento** (manuais, regimento, FAQ e tarifas) e "
            "**cita a fonte** de cada resposta. Material didático do EV Challenge FIAP × GoodWe."
        )
        status = gr.Markdown("_Faça uma pergunta para ver a configuração em uso._")
        with gr.Row():
            with gr.Column(scale=3):
                chat = gr.Chatbot(label="Conversa", height=460)
                caixa = gr.Textbox(label="Sua pergunta", placeholder="Ex.: Como cancelo um agendamento?", lines=1)
                with gr.Row():
                    enviar = gr.Button("Enviar", variant="primary")
                    limpar = gr.Button("Limpar conversa")
                gr.Examples(EXEMPLOS, inputs=caixa, label="Exemplos")
            with gr.Column(scale=2):
                with gr.Accordion("Configuração", open=False):
                    iteracao = gr.Dropdown(list(ITERACOES), value="iter3", label="Iteração do RAG")
                    provider = gr.Dropdown(
                        ["auto", "offline", "groq_oss", "groq_secundario"], value="auto",
                        label="Geração (auto = Groq se houver GROQ_API_KEY; senão offline)",
                    )
                    k = gr.Slider(1, 8, value=4, step=1, label="k (trechos recuperados)")
                gr.Markdown("### Trechos recuperados")
                trechos = gr.Markdown("_Os trechos usados na resposta aparecem aqui._")
        oculto = gr.Markdown(visible=False)

        entradas = [caixa, chat, iteracao, provider, k]
        saidas = [chat, caixa, status, trechos, oculto]
        caixa.submit(responder, entradas, saidas)
        enviar.click(responder, entradas, saidas)
        limpar.click(lambda: ([], "", "_Conversa limpa._", "_Os trechos usados na resposta aparecem aqui._"),
                     None, [chat, caixa, status, trechos])
    return demo


if __name__ == "__main__":
    construir_interface().launch(server_name="127.0.0.1", server_port=7860)
