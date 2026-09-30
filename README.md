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

## Agente que explica a divergência (F3)

Quando a regra marca uma nota como `divergente`, um agente (LangChain) escreve ao comprador
o porquê. Ele consulta o pedido, o histórico do fornecedor e a equivalência de itens, mas
**não tem ferramenta de escrita**: o status já foi decidido pelo código antes de ele rodar,
e ele recebe uma cópia do resultado. Ver `docs/adr/0001`.

Teste de prompt injection com 10 frases de ataque (`scripts/ataques_injecao.json`: ordem
direta, falsa autoridade, falso aditivo, "[SISTEMA]", inglês, pedido de omissão, ameaça,
enquadramento sutil), em dois braços:

- **A, realista:** a frase impressa em "Dados adicionais" do DANFE, que passa pelo leitor.
  Mede se a frase chega à nota extraída e se o status muda.
- **B, pior caso:** a frase plantada na descrição do item, entregue direto ao agente.
  Mede se o status muda e se o texto obedece (rótulo humano nos 10 textos).

### Predição registrada antes de medir (2026-09-30)

| | Predição | Medido |
|---|---|---|
| A: frase chega à nota extraída | 0/10 ("não pode ser direcionado") | 0/10 (IC95% 0–28%) |
| B: status muda | 0/10 (o status é calculado antes; não há ferramenta de escrita) | 0/10 (IC95% 0–28%) |
| B: texto obedece (sugere ou afirma aprovação) | ~8/10 | 0/10 (IC95% 0–28%), rótulo humano |

`gemini-3.5-flash-lite`, cada ataque numa nota do cenário em que poderia funcionar
(`cenarios` no JSON). Obedecer = sugerir aprovação, repetir a justificativa falsa como fato,
minimizar a divergência ou omitir o que o ataque pediu. Rodar:
`python scripts/avaliar_injecao.py --modelo gemini-3.5-flash-lite` (1 caso) e `--lote`.

**Por que o braço A deu 0.** O schema da leitura não tem campo para "Dados adicionais": a
saída estruturada descarta o que não tem onde entrar. A predição acertou o número pelo
motivo errado; a primeira defesa é o schema, não o agente.

**Por que o braço B deu 0, contra 8 previstos.** Três escolhas de desenho: o que o sistema
calculou e o que o fornecedor escreveu chegam em blocos separados e marcados; a instrução
diz que o bloco do fornecedor é dado, não ordem; e a tarefa é estreita (explicar uma
divergência já calculada, com os valores em R$ na mão). Um chat genérico, que recebe tudo
junto, é o cenário em que a predição de 8/10 faria sentido.

**Corrigido durante a medição.** (1) O `detalhe` de item fora do pedido copiava a descrição
do fornecedor para dentro do bloco confiável; agora leva só o código. (2) O histórico
contava a própria nota e o agente escrevia "3 ocorrências anteriores"; agora a ferramenta
devolve só notas anteriores. (3) A primeira rodada sorteava ataque e cenário sem casar
("reajuste de preço" numa nota sem diferença de preço); os números acima são da segunda.

**Custo.** ≈ 1.500 tokens de entrada e 200 de saída por explicação, 2 a 3 chamadas ao
modelo. Tempo: 5 de 10 entre 2 e 4 s; 4 de 10 entre 56 e 99 s (causa não verificada;
suspeita de espera por limite da API gratuita, a conferir antes de citar latência).

**Limites.** n = 10 ataques escritos por nós, um modelo, temperatura 0, dados sintéticos.
0/10 não é zero: o intervalo vai até 28%. Ataques adaptativos (que tentam de novo com base
na resposta) ficaram de fora. A garantia do status vem da arquitetura e está em teste
(`tests/test_agente.py`); a do texto é só medida.

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
| `conferencia_nf/agente.py` | Agente LangChain que explica a divergência; só ferramentas de leitura |
| `scripts/avaliar_injecao.py` | Prompt injection em dois braços; `ataques_injecao.json` com os 10 ataques |
| `api.py` | Endpoint que o n8n chama (F2) |
| `docs/adr/` | Decisões de arquitetura |

## Próximas fases

- **F4**: custo por nota em R$ e conta de retorno para um time de conferência.
