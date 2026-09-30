# Conferência de nota fiscal × pedido de compra

Um time financeiro confere à mão cada nota de fornecedor contra o pedido de compra.
Este projeto automatiza a conferência e usa LLM **só onde a regra não alcança**: nota
que chega em PDF ou escaneada. Toda decisão é tomada por código; o modelo só lê.

> Dados 100% sintéticos: fornecedores, CNPJs e produtos fictícios. O XML segue a estrutura
> da NF-e 4.00 de forma simplificada e sem assinatura.

## Como funciona

```mermaid
flowchart LR
    A[Documento do fornecedor] --> B{Tipo?}
    B -- XML da NF-e --> C[Parser determinístico<br/>custo zero]
    B -- PDF / imagem --> D[Gemini<br/>saída estruturada]
    C --> E[Checagem da leitura<br/>aritmética + dígito do CNPJ]
    D --> E
    E -- falhou --> H[Revisão humana]
    E -- ok --> F[Regra: nota × pedido<br/>preço, quantidade, item]
    F -- dentro da tolerância --> G[Aprovada]
    F -- fora --> I[Divergente<br/>com diferença em R$]
```

- **XML vai por regra.** A NF-e já é estruturada; ler XML com LLM seria pagar para errar.
- **O LLM só lê, nunca decide.** Formato válido (JSON no schema) não garante conteúdo certo,
  por isso toda leitura passa por checagens que não precisam de gabarito: quantidade ×
  preço = total do item, soma dos itens = total da nota e dígito verificador do CNPJ.
- **Erro falha fechado.** Leitura duvidosa, pedido não encontrado ou fornecedor diferente
  do pedido vão para revisão humana, nunca para aprovação.

## Resultado da leitura com LLM (F1)

`gemini-3.5-flash-lite`, 10 notas por condição, acerto campo a campo contra o gabarito
(IC95% de Wilson). Rodar: `python scripts/avaliar_extracao.py --n 10 --modelo gemini-3.5-flash-lite`.

| | DANFE limpo | DANFE escaneado |
|---|---|---|
| Campos corretos | 155/155 (100%, IC95% 97,6–100%) | 134/155 (86%, IC95% 80–91%) |
| Quantidade, preço e total | sem erro | sem erro |
| Campo que mais errou | — | descrição (11/21) e nº do pedido (5/10) |
| **Decisão igual à da nota verdadeira** | 10/10 | 5/10 |
| **Decisão errada para o lado perigoso** (aprovar o que devia barrar) | 0/10 | 0/10 (IC95% 0–28%) |
| Tokens por nota (entrada/saída) | ≈ 710 / 300 | ≈ 1.270 / 300 |

**Leitura de negócio.** Acerto por campo não é a métrica que importa. No escaneado, 86% dos
campos certos ainda deram 0 decisões perigosas, porque a regra depende dos números (que
vieram certos) e o erro de texto cai em revisão. O custo aparece em outro lugar: metade dos
escaneados foi para revisão humana sem precisar. Os próximos degraus, do mais barato ao
mais caro:
1. pedir o XML ao fornecedor (zera o problema);
2. casar pedido e item por similaridade quando o código vem ilegível (regra, sem LLM);
3. só então testar modelo maior.

**Limites.** n = 10 por condição, dados sintéticos e um único layout de DANFE. O ruído do
"escaneado" é simulado. O número serve para comparar degraus, não para prometer acerto em
produção.

### Predição registrada antes de medir

| | Predição | Medido |
|---|---|---|
| Acerto no DANFE limpo | ~90% | 100% (IC95% 97,6–100%) |
| Acerto no escaneado | ~90% | 86% (IC95% 80–91%) |
| Campo que mais erra | descrição e CNPJ | descrição e nº do pedido; CNPJ errou 1/10 e foi barrado pelo dígito verificador |

## Fluxo no n8n (F2)

O fornecedor (ou o e-mail de entrada) manda o arquivo para um webhook do n8n. O n8n chama
a API, separa por quem precisa agir e registra na "planilha" (CSV via API; trocar por
Google Sheets é trocar só o nó de saída).

```
Nota recebida (webhook) → Conferir na API → Quem precisa agir?
    ├─ Automático ──────────────┐
    ├─ Comprador contesta ──────┼→ Registrar na planilha → Responder ao remetente
    └─ Revisor confere a leitura┘
```

Lote de teste com mistura fixada antes de medir (7 XML + 3 escaneados):

| Fila | Notas | Por quê |
|---|---|---|
| Automático | 5 | tudo dentro do pedido e da tolerância |
| Comprador contesta | 3 | divergência real: preço, quantidade e item fora do pedido |
| Revisor confere a leitura | 2 | 1 nota sem pedido (esperado) e 1 escaneado em que o LLM leu `PC 20260003` em vez de `PC-20260003` |

5 de 10 chegaram a uma pessoa, e só 1 por causa do LLM. O que dominou foi a taxa de
problema real das notas, que aqui é alta por construção (4 de 10). Num cliente, essa taxa
é o primeiro número a levantar no diagnóstico: ela define o tamanho do time que sobra,
mais do que a qualidade do modelo.

## Como rodar

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...       # opcional: GEMINI_MODEL (padrão gemini-2.5-flash)
python -m conferencia_nf.gerar_dados --n 30 --saida data
python -m pytest -q             # não chama API
uvicorn api:app --port 8000     # POST /conferir com o arquivo
```

Com n8n (Docker):

```bash
docker compose up -d --build
docker compose exec n8n n8n import:workflow --input=/workflows/conferencia.json
docker compose exec n8n n8n publish:workflow --id=ConfNFxPedido0001
docker compose restart n8n
python scripts/enviar_lote.py   # manda 10 notas ao webhook
```

No Git Bash do Windows, use `MSYS_NO_PATHCONV=1` antes dos comandos `exec`.

## Estrutura

| Arquivo | Papel |
|---|---|
| `conferencia_nf/roteador.py` | Decide o caminho pelo conteúdo do arquivo, não pela extensão |
| `conferencia_nf/extrator_xml.py` | Parser da NF-e, protegido contra XXE |
| `conferencia_nf/extrator_llm.py` | Gemini com schema; conta tokens de raciocínio no custo |
| `conferencia_nf/conferencia.py` | Regra de negócio e tolerâncias |
| `conferencia_nf/gerar_dados.py` | Pedidos, XML, DANFE e DANFE escaneado sintéticos |
| `scripts/avaliar_extracao.py` | Acerto por campo, decisão vs gabarito, tokens |
| `api.py` | Endpoint que o n8n chama (F2) |
| `docs/adr/` | Decisões de arquitetura |

## Próximas fases

- **F3**: agente com ferramentas só de leitura para explicar as divergências, com teste de
  prompt injection escrito dentro do PDF.
- **F4**: custo por nota em R$ e conta de retorno para um time de conferência.
