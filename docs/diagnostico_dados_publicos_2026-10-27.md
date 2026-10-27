# Diagnóstico: NF-e pública ligada a compras

**Data:** 2026-10-27
**Fase:** investigação de fonte, sem mudança no código
**Pergunta:** dados públicos permitem conferir uma NF-e real contra a compra correspondente de forma reproduzível?

## Fontes verificadas

- [Portal da Transparência — download de NF-e](https://portaldatransparencia.gov.br/download-de-dados/notas-fiscais): publica dados de notas de compras federais.
- [Dicionário das NF-e](https://portaldatransparencia.gov.br/dicionario-de-dados/notas-fiscais): a tabela de itens inclui descrição, quantidade, valor unitário e total; o dicionário não apresenta identificador de contrato, empenho ou pedido nessa tabela.
- [Manual do PNCP — instrumentos de cobrança](https://pncp.gov.br/manual/pt-br/2.5/contrato_empenho/consultar_instrumentos_de_cobranca_de_um_contrato_ou_empenho.html): prevê vínculo ao contrato/empenho, chave da NF-e e itens da nota. A existência do campo não prova preenchimento em contratos concretos.
- [Manual do PNCP — itens da contratação](https://pncp.gov.br/manual/pt-br/2.5/contratacao/consultar_itens_de_uma_contratacao.html): distingue valor unitário **estimado** da contratação. Não se deve tratá-lo automaticamente como preço aprovado para pagamento.
- [Manual do PNCP — resultados de item](https://pncp.gov.br/manual/pt-br/latest/contratacao/consultar_um_resultado_especifico_de_item_de_uma_contratacao.html): publica fornecedor, quantidade e valor unitário **homologado**.

## Verificação de registros reais

Predição do Luiz, registrada antes da consulta: **6 a 10 de 10** contratos/empenhos de compras com NF-e vinculada.

Protocolo: consultar a [API pública de contratos do PNCP](https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=20260401&dataFinal=20260402&pagina=1&tamanhoPagina=50), páginas 1 e 2, publicações de 01–02/04/2026; selecionar os dez primeiros registros com `categoriaProcesso.nome = Compras` e `receita = false`, mantendo a ordem retornada. Em 27/10/2026, consultar `GET /api/pncp/v1/orgaos/{cnpj}/contratos/{anoContrato}/{sequencialContrato}/instrumentocobranca` para cada um. O primeiro registro elegível veio da página 1; os nove seguintes, da página 2.

| Nº | Contrato PNCP | Resultado da rota de cobrança |
|---:|---|---|
| 1 | [95595120000195-2-000010/2026](https://pncp.gov.br/api/pncp/v1/orgaos/95595120000195/contratos/2026/10/instrumentocobranca) | 404: `Nenhum instrumento de Cobrança encontrado.` |
| 2 | [02585924000122-2-003144/2026](https://pncp.gov.br/api/pncp/v1/orgaos/02585924000122/contratos/2026/3144/instrumentocobranca) | 404: mesma mensagem |
| 3 | [02585924000122-2-003145/2026](https://pncp.gov.br/api/pncp/v1/orgaos/02585924000122/contratos/2026/3145/instrumentocobranca) | 404: mesma mensagem |
| 4 | [02585924000122-2-003146/2026](https://pncp.gov.br/api/pncp/v1/orgaos/02585924000122/contratos/2026/3146/instrumentocobranca) | 404: mesma mensagem |
| 5 | [02585924000122-2-003147/2026](https://pncp.gov.br/api/pncp/v1/orgaos/02585924000122/contratos/2026/3147/instrumentocobranca) | 404: mesma mensagem |
| 6 | [02585924000122-2-003148/2026](https://pncp.gov.br/api/pncp/v1/orgaos/02585924000122/contratos/2026/3148/instrumentocobranca) | 404: mesma mensagem |
| 7 | [02585924000122-2-003149/2026](https://pncp.gov.br/api/pncp/v1/orgaos/02585924000122/contratos/2026/3149/instrumentocobranca) | 404: mesma mensagem |
| 8 | [02585924000122-2-003150/2026](https://pncp.gov.br/api/pncp/v1/orgaos/02585924000122/contratos/2026/3150/instrumentocobranca) | 404: mesma mensagem |
| 9 | [02585924000122-2-003151/2026](https://pncp.gov.br/api/pncp/v1/orgaos/02585924000122/contratos/2026/3151/instrumentocobranca) | 404: mesma mensagem |
| 10 | [02585924000122-2-003152/2026](https://pncp.gov.br/api/pncp/v1/orgaos/02585924000122/contratos/2026/3152/instrumentocobranca) | 404: mesma mensagem |

**Resultado observado:** 0/10 com instrumento de cobrança nessa amostra. IC de Wilson 95% para a fração da amostra: 0–27,8%, **somente sob hipótese de observações independentes**. Nove registros pertencem ao mesmo órgão; essa hipótese é fraca. Portanto, o resultado não estima a cobertura geral do PNCP e não demonstra que os contratos nunca tiveram NF-e. Ele demonstra apenas que essa rota não fornecia o vínculo para esses registros na data da consulta.

Uma busca dirigida adicional encontrou o [contrato 35251090000178-2-000037/2026](https://pncp.gov.br/app/contratos/35251090000178/2026/37), publicado em maio. Sua [rota de cobrança](https://pncp.gov.br/api/pncp/v1/orgaos/35251090000178/contratos/2026/37/instrumentocobranca) também respondeu `404` com a mesma mensagem em 27/10/2026. Esse caso **não integra a amostra de dez** nem altera o resultado medido.

### Segunda amostra: órgãos distintos

Predição do Luiz, registrada antes da consulta: **6 a 10 em 10** com NF-e vinculada.

Protocolo: na [primeira página da consulta de contratos publicados em 01–02/07/2025](https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=20250701&dataFinal=20250702&pagina=1&tamanhoPagina=50), tomar os primeiros dez registros na ordem da API com `categoriaProcesso.nome = Compras`, `receita = false` e CNPJ de órgão ainda não selecionado. Consultar para cada um a rota de instrumentos de cobrança em 27/10/2026. Dois contratos têm ano contratual 2024, mas foram **publicados** em 2025, conforme o filtro estabelecido.

| Nº | Contrato PNCP | Resultado |
|---:|---|---|
| 1 | [01746697000107-2-000001/2024](https://pncp.gov.br/api/pncp/v1/orgaos/01746697000107/contratos/2024/1/instrumentocobranca) | 404: nenhum instrumento encontrado |
| 2 | [07954480000179-2-014043/2025](https://pncp.gov.br/api/pncp/v1/orgaos/07954480000179/contratos/2025/14043/instrumentocobranca) | 404: idem |
| 3 | [88577416000118-2-000125/2024](https://pncp.gov.br/api/pncp/v1/orgaos/88577416000118/contratos/2024/125/instrumentocobranca) | 404: idem |
| 4 | [92005545000109-2-000070/2025](https://pncp.gov.br/api/pncp/v1/orgaos/92005545000109/contratos/2025/70/instrumentocobranca) | 404: idem |
| 5 | [83102368000198-2-000498/2025](https://pncp.gov.br/api/pncp/v1/orgaos/83102368000198/contratos/2025/498/instrumentocobranca) | 404: idem |
| 6 | [00569168000112-2-000012/2025](https://pncp.gov.br/api/pncp/v1/orgaos/00569168000112/contratos/2025/12/instrumentocobranca) | 404: idem |
| 7 | [15442776000139-2-000042/2025](https://pncp.gov.br/api/pncp/v1/orgaos/15442776000139/contratos/2025/42/instrumentocobranca) | 404: idem |
| 8 | [84591890000143-2-000152/2025](https://pncp.gov.br/api/pncp/v1/orgaos/84591890000143/contratos/2025/152/instrumentocobranca) | 404: idem |
| 9 | [82926551000145-2-001356/2025](https://pncp.gov.br/api/pncp/v1/orgaos/82926551000145/contratos/2025/1356/instrumentocobranca) | 404: idem |
| 10 | [82926569000147-2-000673/2025](https://pncp.gov.br/api/pncp/v1/orgaos/82926569000147/contratos/2025/673/instrumentocobranca) | 404: idem |

**Resultado:** 0/10 com instrumento; intervalo de Wilson 95%: 0–27,8% sob hipótese de amostragem independente. A escolha da primeira página e de um intervalo de publicação curto não é aleatória nem representativa do universo. Ainda pode haver dependência operacional entre órgãos que usam o mesmo integrador. A mensagem de 404 indica ausência de instrumento na rota consultada, não uma falha genérica de acesso e tampouco prova ausência de nota fora do PNCP. A busca dirigida que encontrou o caso IFAL não integra essa amostra.

## Caso positivo encontrado por busca dirigida

A [consulta oficial por data de inclusão de instrumentos de cobrança](https://pncp.gov.br/api/consulta/v1/instrumentoscobranca/inclusao?dataInicial=20261001&dataFinal=20261002&pagina=1&tamanhoPagina=10) retornou o instrumento 4 do [contrato IFAL 10825373000155-2-000420/2025](https://pncp.gov.br/api/pncp/v1/orgaos/10825373000155/contratos/2025/420/instrumentocobranca/4). A consulta individual confirmou o vínculo e os campos abaixo em 27/10/2026:

| Campo | Valor observado |
|---|---|
| Fornecedor do contrato e emitente da nota | CNPJ 18.008.915/0001-09 |
| Chave da NF-e | `27260918008915000109550010001141701508230755` |
| Data de emissão da NF-e | 11/09/2026 |
| Item da NF-e | Água mineral 20 L; 423 unidades × R$ 7,90 = R$ 3.341,70 |
| Compra vinculada pelo contrato | [10825373000155-1-000199/2024](https://pncp.gov.br/api/pncp/v1/orgaos/10825373000155/compras/2024/199/itens) |
| Item 2 da compra | Garrafão 20 L, 14.400 unidades; estimativa R$ 11,00/un. |
| [Resultado homologado do item 2](https://pncp.gov.br/api/pncp/v1/orgaos/10825373000155/compras/2024/199/itens/2/resultados) | Mesmo CNPJ do fornecedor; R$ 7,90/un. |

Há também [item 1 homologado](https://pncp.gov.br/api/pncp/v1/orgaos/10825373000155/compras/2024/199/itens/1/resultados) ao mesmo fornecedor para garrafão 20 L, mas por R$ 6,49/un. O valor global do contrato (R$ 114.660) coincide com o total homologado dos itens 2 e 3 desse fornecedor (14.400 × R$ 7,90 + 600 × R$ 1,50), o que **sugere** que a NF-e de R$ 7,90 pertence ao item 2. Essa identificação é inferência; falta confirmar a alocação dos itens no instrumento contratual ou documento anexo. O dado sustenta um alerta com trilha de evidências, não uma aprovação automática de pagamento.

A [lista de arquivos do contrato](https://pncp.gov.br/api/pncp/v1/orgaos/10825373000155/contratos/2025/420/arquivos) inclui um termo de referência e extratos. A tentativa de abrir o termo retornou bloqueio do navegador neste ambiente; não foi usado como evidência de alocação. O [extrato publicado no DOU](https://portal.ifba.edu.br/barreiras/anexos-2025/setembro/PublicaoDOU.pdf/%40%40download/file/PublicaoDOU.pdf) confirma o processo 23041.032956/2025-56, o fornecedor, o objeto e o valor global de R$ 114.660, mas não discrimina itens.

Essa busca é **dirigida a registros que já têm instrumento de cobrança**; não mede a frequência de vínculos entre todos os contratos.

## Diagnóstico para o projeto

O PNCP fornece **um caso positivo reproduzível** com contrato, NF-e e preço homologado comparável. A base da CGU traz notas reais, porém seu dicionário não fornece diretamente o pedido/contrato correspondente. Ainda não há base para afirmar cobertura ampla ou conferência automática de compras públicas de ponta a ponta: a correspondência exata do item e a disponibilidade dos vínculos exigem validação adicional.

**Próximo gate:** confirmar no contrato/anexos a alocação do item 2 e desenhar uma amostra estratificada por período, órgão e integrador para estimar disponibilidade com menos viés. Depois, especificar um adaptador somente para os campos comprovados, com decisão inconclusiva quando não houver vínculo ou correspondência de item suficiente. Para um produto de conferência operacional, a fonte principal provavelmente terá de ser a nota e o pedido/contrato fornecidos pelo próprio cliente; os dados públicos servem para prova de conceito e avaliação externa.
