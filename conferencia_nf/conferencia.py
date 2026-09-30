"""Regra de negócio: nota × pedido. Nenhum LLM aqui, de propósito.

Três camadas, nesta ordem:
1. A leitura é confiável? (aritmética e CNPJ). Se não, vai para revisão humana.
2. Achamos o pedido e o fornecedor bate? Se não, revisão humana.
3. Item a item: preço e quantidade dentro da tolerância.
"""
from . import cnpj
from .modelos import Divergencia, NotaFiscal, Pedido, Resultado

# Tolerância de preço sobre o valor do item (não por unidade: R$ 0,50 numa tampa de
# R$ 0,07 seria aceitar 700% de aumento). Vale o maior entre 0,5% e R$ 0,50.
# Valor ilustrativo; num cliente real, combinado com o financeiro antes do piloto.
TOL_PRECO_PCT = 0.005
TOL_PRECO_ABS = 0.50


def checar_leitura(nota: NotaFiscal) -> list[str]:
    """Checagens que não precisam de gabarito: se falham, a leitura não é confiável."""
    motivos = []
    if not cnpj.valido(nota.cnpj_emitente):
        motivos.append(f"CNPJ {nota.cnpj_emitente} com dígito verificador inválido")
    for item in nota.itens:
        esperado = item.quantidade * item.valor_unitario
        if abs(esperado - item.valor_total) > max(0.02, 0.001 * item.valor_total):
            motivos.append(
                f"item {item.codigo}: {item.quantidade} × {item.valor_unitario} "
                f"≠ {item.valor_total}"
            )
    soma = sum(i.valor_total for i in nota.itens)
    if abs(soma - nota.valor_total) > 0.05:
        motivos.append(f"soma dos itens {soma:.2f} ≠ total da nota {nota.valor_total:.2f}")
    return motivos


def conferir(nota: NotaFiscal, pedidos: dict[str, Pedido], origem: str) -> Resultado:
    motivos = checar_leitura(nota)
    pedido = pedidos.get(nota.pedido) if nota.pedido else None
    if pedido is None:
        motivos.append(f"pedido {nota.pedido!r} não encontrado")
    elif pedido.cnpj_fornecedor != nota.cnpj_emitente:
        motivos.append("CNPJ do emitente diferente do fornecedor do pedido")
    if motivos:
        return Resultado(status="revisao_humana", origem=origem, motivos_revisao=motivos, nota=nota)

    do_pedido = {i.codigo: i for i in pedido.itens}
    divergencias = []
    for item in nota.itens:
        ped = do_pedido.get(item.codigo)
        if ped is None:
            divergencias.append(Divergencia(
                tipo="item_fora_do_pedido", codigo=item.codigo,
                detalhe=f"{item.descricao} não consta no pedido {pedido.numero}",
                diferenca_rs=round(item.valor_total, 2)))
            continue
        excesso = (item.valor_unitario - ped.valor_unitario) * item.quantidade
        tolerancia = max(TOL_PRECO_ABS, TOL_PRECO_PCT * ped.valor_unitario * item.quantidade)
        if excesso > tolerancia:
            divergencias.append(Divergencia(
                tipo="preco_acima", codigo=item.codigo,
                detalhe=f"R$ {item.valor_unitario:.4f} na nota contra R$ {ped.valor_unitario:.4f} no pedido",
                diferenca_rs=round(excesso, 2)))
        # Entregar menos que o pedido é entrega parcial, não divergência.
        if item.quantidade > ped.quantidade:
            divergencias.append(Divergencia(
                tipo="quantidade_acima", codigo=item.codigo,
                detalhe=f"{item.quantidade:g} na nota contra {ped.quantidade:g} no pedido",
                diferenca_rs=round((item.quantidade - ped.quantidade) * item.valor_unitario, 2)))

    status = "divergente" if divergencias else "aprovada"
    return Resultado(status=status, origem=origem, divergencias=divergencias, nota=nota)
