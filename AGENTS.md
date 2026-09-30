# AGENTS.md — conferencia-nf-agente

Piloto de portfólio: conferência de nota fiscal × pedido de compra. Responda em pt-BR.
Dono: Luiz Maibashi. Objetivo do projeto: reproduzir, com dado sintético, o padrão de
conferência de documento que uso no trabalho (leitura de carta comercial em PDF com revisão humana).

## Regra de ouro

**O LLM lê, o código decide.** Nenhuma decisão de pagamento sai de LLM. XML vai por
parser; LLM só em PDF/imagem; toda leitura passa por `checar_leitura` antes da regra.

## Linguagem do projeto

| Termo | Significado aqui |
|---|---|
| NF-e | nota fiscal eletrônica, um XML estruturado |
| DANFE | a versão impressa (PDF) da NF-e |
| xPed | campo da NF-e com o nº do pedido de compra |
| checagem de leitura | aritmética (qtd × preço, soma = total) + dígito do CNPJ, sem gabarito |
| fila | quem age: `automatico`, `comprador` (divergência real), `revisor` (leitura duvidosa) |
| decisão perigosa | aprovar o que devia barrar; a métrica que mais importa |
| régua | o gabarito e a comparação da avaliação; já errou 2× (zeros à esquerda, descrição truncada) |

## Estado (2026-09-30)

- **F1** (`b322563`): roteador, parser XML, leitura Gemini com schema, regra com tolerância,
  avaliação. `gemini-3.5-flash-lite`, 10 notas/condição: limpo 155/155 campos; escaneado
  134/155 (86%, IC95% 80–91%); 0 decisões perigosas; 5/10 escaneados em revisão sem precisar.
- **F2** (`e4eacf1`): n8n 2.41.3 em Docker. Lote 7 XML + 3 escaneados: 5 automático,
  3 comprador, 2 revisor (1 por leitura "PC 20260003").
- **F3** (2026-09-30): agente LangChain 1.4 (`conferencia_nf/agente.py`) explica nota
  divergente; 3 ferramentas só de leitura, recebe cópia do resultado. Injection, 10 ataques
  casados por cenário: frase no DANFE chegou à nota 0/10; status mudou 0/10; texto obedeceu
  0/10 (rótulo do Luiz; IC95% 0–28% cada). Predição era b, ~8/10.
- Predições do Luiz ficam registradas no README antes de cada medição.

## Próximo passo

- Degrau barato pendente: normalizar o nº do pedido (espaço × hífen) na regra, e remedir.
- F3: conferir se `output_tokens` do langchain-google-genai inclui raciocínio; causa das
  4 execuções de 56–99 s. Ataque adaptativo (várias tentativas) não testado.
- F4: custo por nota em R$ e conta de retorno.

## Como rodar

```bash
pip install -r requirements.txt
python -m conferencia_nf.gerar_dados --n 30 --saida data   # data/ fica fora do git; semente fixa
python -m pytest -q                                        # não chama API
# PC do trabalho: %TEMP% nega acesso ao pytest → acrescente --basetemp=.pytest_tmp
python scripts/avaliar_injecao.py --modelo gemini-3.5-flash-lite   # 1 caso; --lote = 10
docker compose up -d --build                               # api:8000 + n8n:5678
# Git Bash no Windows: prefixe os exec com MSYS_NO_PATHCONV=1
docker compose exec n8n n8n import:workflow --input=/workflows/conferencia.json
docker compose exec n8n n8n publish:workflow --id=ConfNFxPedido0001
docker compose restart n8n
python scripts/enviar_lote.py
```

Precisa de `GEMINI_API_KEY` no ambiente. Cota grátis do `gemini-2.5-flash`: 20 chamadas/dia;
use `gemini-3.5-flash-lite` (padrão no compose).

## Regras de trabalho

- **Teste 1 documento antes de qualquer lote** que chame a API (erro registrado em 2026-09-29).
- Toda proporção com `n` e IC95% (Wilson, `scripts/avaliar_extracao.py`).
- Pedir a predição do Luiz antes de medir; registrar no README.
- Zona de julgamento: o agente escreve o código; o Luiz prevê, diagnostica e explica em voz alta.
- Commits em Conventional Commits, sem `Co-Authored-By`.
