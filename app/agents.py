import os
from functools import lru_cache

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.flavor_schemas import ExecutableRecipeDraft
from app.schemas import FernandoReview, TechnicalReview

_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")


TECHNICAL_WRITER_PROMPT = """
Você é o Chef Técnico do sistema de composição nordestina.

Você NÃO inventa a arquitetura do prato. Ela já foi definida por blocos de sabor
da Biblioteca Fernando Nordeste v0.1.

Sua função é transformar a arquitetura em receita executável.

Regras:
- Respeite os blocos, funções e formas escolhidas.
- Use apenas ingredientes nordestinos da arquitetura (e os do pedido).
- Informe gramas, temperaturas, tempos, ordem e pontos críticos.
- Adapte a Thermomix TM7, churrasqueira e demais equipamentos do pedido.
- Não adicione componentes decorativos fora da arquitetura.
- Se houver correções de equilíbrio/conflito, aplique-as na execução.
- Responda no schema solicitado.
""".strip()


TECHNICAL_REVIEW_PROMPT = """
Você é o revisor de execução técnica.

Avalie viabilidade da receita (quantidades, temperaturas, tempos, equipamentos,
segurança, cronograma). Não julgue estilo pessoal.

Quando reprovar, peça mudanças concretas e executáveis.
""".strip()


FERNANDO_CRITIC_PROMPT = """
Você é o Crítico Fernando.

A receita veio do motor de blocos da Biblioteca Nordeste v0.1. Avalie se a
composição parece uma decisão sua:

- protagonismo do ingrediente;
- poucos componentes com função clara;
- acidez e contraste de textura;
- brasa/redução/aproveitamento com benefício perceptível;
- tipicidade nordestina sem folclore turístico;
- ausência de complexidade só para impressionar.

Se a arquitetura de blocos for boa mas a execução for genérica, diga isso.
Se algo não parecer Fernando, reprove com alterações precisas.
""".strip()


@lru_cache(maxsize=1)
def get_model():
    return init_chat_model(
        f"openai:{_MODEL}",
        temperature=0.3,
    )


@lru_cache(maxsize=1)
def get_technical_writer_agent():
    return create_agent(
        model=get_model(),
        system_prompt=TECHNICAL_WRITER_PROMPT,
        response_format=ExecutableRecipeDraft,
    )


@lru_cache(maxsize=1)
def get_technical_agent():
    return create_agent(
        model=get_model(),
        system_prompt=TECHNICAL_REVIEW_PROMPT,
        response_format=TechnicalReview,
    )


@lru_cache(maxsize=1)
def get_fernando_critic_agent():
    return create_agent(
        model=get_model(),
        system_prompt=FERNANDO_CRITIC_PROMPT,
        response_format=FernandoReview,
    )


# Proxies preguiçosos para imports existentes
class _LazyAgent:
    def __init__(self, factory):
        self._factory = factory

    def invoke(self, *args, **kwargs):
        return self._factory().invoke(*args, **kwargs)


technical_writer_agent = _LazyAgent(get_technical_writer_agent)
technical_agent = _LazyAgent(get_technical_agent)
fernando_critic_agent = _LazyAgent(get_fernando_critic_agent)
creator_agent = technical_writer_agent
