# ADR-0001: SDK do Gemini na leitura; LangChain só no agente de exceções

**Status:** aceita (2026-09-29)

## Contexto

O projeto tem dois usos de LLM com naturezas diferentes:
1. **Leitura** do DANFE: uma chamada, entrada fixa, saída num schema conhecido.
2. **Agente** das exceções (F3): várias chamadas em loop, com ferramentas.

## Decisão

- Leitura usa o SDK `google-genai` direto, com `response_schema` em Pydantic.
- O agente da F3 usa LangChain, que resolve o loop de ferramentas e a troca de provedor.

## Por quê

- Na leitura, LangChain não acrescenta nada: não há loop nem ferramenta. Uma camada a mais
  só dificulta ver o que foi enviado e quanto custou (inclusive tokens de raciocínio, que
  entram no custo e somem em abstrações mal configuradas).
- No agente, o loop de ferramentas, o histórico e a validação de argumentos são código
  repetitivo que o LangChain já resolve, e trocar de provedor vira configuração.

## Consequências

- Duas formas de chamar o modelo no mesmo repositório. Aceito, porque cada uma está no lugar
  onde paga o próprio custo.
- Se a leitura precisar de fallback entre provedores, reavaliar: é o gatilho para
  passar a leitura por uma interface comum.

## Alternativas descartadas

- **LangChain em tudo:** padroniza, mas esconde a chamada mais cara e mais frequente.
- **SDK em tudo, loop do agente à mão:** já feito em outro projeto (PayFlow); aqui o objetivo
  é também comparar com a abstração de mercado.
