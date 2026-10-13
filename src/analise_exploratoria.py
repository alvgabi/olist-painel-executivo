"""
Calcula os indicadores e achados apresentados no painel e no README.
Periodo analisado: jan/2017 a ago/2018 (meses completos da base).

Uso: python src/analise_exploratoria.py   (depois de rodar preparar_dados.py)
"""
from pathlib import Path
import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
b = pd.read_csv(PROC / "olist_base.csv", parse_dates=["order_purchase_timestamp"])
b = b[(b.order_purchase_timestamp >= "2017-01-01") & (b.order_purchase_timestamp < "2018-09-01")]
v = b[~b.status_pt.isin(["Cancelado", "Indisponível"])]
pp = v[v.primeira_linha_pedido == 1]

print("== Indicadores (pedidos validos)")
print(f"Receita de produtos : R$ {v.price.sum():,.0f}")
print(f"Pedidos             : {v.order_id.nunique():,}")
print(f"Ticket medio        : R$ {(pp.valor_produtos_p.sum() + pp.valor_frete_p.sum()) / v.order_id.nunique():,.2f}")
print(f"Nota media          : {pp.review_score_p.mean():.2f}")
print(f"Entregas atrasadas  : {pp.entregue_atrasado_p.mean():.1%}")
rec = v.groupby("customer_unique_id").order_id.nunique()
print(f"Taxa de recompra    : {(rec > 1).mean():.1%}")

print("\n== Nota media por faixa de atraso (pedidos entregues)")
print(pp[pp.faixa_ordem < 5].groupby(["faixa_ordem", "faixa_atraso"]).review_score_p.mean().round(2))

print("\n== % atraso e nota por mes")
m = pp.groupby(pp.order_purchase_timestamp.dt.to_period("M")).agg(
    atraso=("entregue_atrasado_p", "mean"), nota=("review_score_p", "mean"))
print(m.round(3).to_string())

print("\n== Por regiao")
r = pp.groupby("customer_region").agg(pedidos=("order_id", "count"), dias=("dias_entrega_p", "mean"),
                                       atraso=("entregue_atrasado_p", "mean"), nota=("review_score_p", "mean"))
print(r.sort_values("dias").round(3).to_string())

print("\n== Vendedor postou fora do prazo x atraso final")
print(pp.groupby("vendedor_postou_atrasado_p").entregue_atrasado_p.mean().round(3))

print(f"\nPrazo prometido medio: {pp.dias_prometidos_p.mean():.1f} dias | real: {pp.dias_entrega_p.mean():.1f} dias")
