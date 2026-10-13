"""
Prepara as bases da Olist para o painel no Tableau.

Entrada : CSVs originais do Kaggle em data/raw/
Saida   : data/processed/
          - modelo dimensional (f_pedidos, f_itens, f_pagamentos, f_avaliacoes,
            d_clientes, d_produtos, d_vendedores, d_geo_cep)
          - olist_base.csv: base unica no grao de item, usada pelo painel

Uso: python src/preparar_dados.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
OUT = RAIZ / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

DATAS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
         "order_delivered_customer_date", "order_estimated_delivery_date"]
REGIAO = {"SP": "Sudeste", "RJ": "Sudeste", "MG": "Sudeste", "ES": "Sudeste",
          "PR": "Sul", "SC": "Sul", "RS": "Sul",
          "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
          "BA": "Nordeste", "PE": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste",
          "PI": "Nordeste", "RN": "Nordeste", "AL": "Nordeste", "SE": "Nordeste"}
STATUS_PT = {"delivered": "Entregue", "shipped": "Enviado", "canceled": "Cancelado",
             "unavailable": "Indisponível", "invoiced": "Faturado", "processing": "Em processamento",
             "created": "Criado", "approved": "Aprovado"}
FAIXAS = [(-np.inf, 0, 0, "No prazo"), (0, 3, 1, "1-3 dias"), (3, 7, 2, "4-7 dias"),
          (7, 14, 3, "8-14 dias"), (14, np.inf, 4, "15+ dias")]


def regiao(uf: pd.Series) -> pd.Series:
    return uf.map(REGIAO).fillna("Norte")


def ler():
    zip_ = {"customer_zip_code_prefix": str, "seller_zip_code_prefix": str,
            "geolocation_zip_code_prefix": str}
    b = {
        "pedidos": pd.read_csv(RAW / "olist_orders_dataset.csv", parse_dates=DATAS),
        "clientes": pd.read_csv(RAW / "olist_customers_dataset.csv", dtype=zip_),
        "itens": pd.read_csv(RAW / "olist_order_items_dataset.csv", parse_dates=["shipping_limit_date"]),
        "pagamentos": pd.read_csv(RAW / "olist_order_payments_dataset.csv"),
        "avaliacoes": pd.read_csv(RAW / "olist_order_reviews_dataset.csv",
                                  parse_dates=["review_creation_date", "review_answer_timestamp"]),
        "produtos": pd.read_csv(RAW / "olist_products_dataset.csv"),
        "vendedores": pd.read_csv(RAW / "olist_sellers_dataset.csv", dtype=zip_),
        "traducao": pd.read_csv(RAW / "product_category_name_translation.csv", encoding="utf-8-sig"),
        "geo": pd.read_csv(RAW / "olist_geolocation_dataset.csv", dtype=zip_),
    }
    return b


def modelo_dimensional(b):
    # Clientes e vendedores: regiao
    cli = b["clientes"].assign(customer_region=lambda d: regiao(d.customer_state))
    vend = b["vendedores"].assign(seller_region=lambda d: regiao(d.seller_state))

    # Produtos: traducao + nome legivel em portugues
    prod = b["produtos"].merge(b["traducao"], on="product_category_name", how="left")
    faltantes = {"pc_gamer": "pc_gamer",
                 "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers"}
    prod["product_category_name_english"] = prod.product_category_name_english.fillna(
        prod.product_category_name.map(faltantes))
    prod["product_category_name"] = prod.product_category_name.fillna("sem_categoria")
    prod["product_category_name_english"] = prod.product_category_name_english.fillna("no_category")
    prod["categoria"] = prod.product_category_name.str.replace("_", " ").str.capitalize()

    # Geolocalizacao: 1 linha por prefixo de CEP (a base original tem ~1 milhao de linhas)
    geo = (b["geo"].groupby("geolocation_zip_code_prefix")
           .agg(lat=("geolocation_lat", "median"), lng=("geolocation_lng", "median"),
                cidade=("geolocation_city", lambda x: x.mode().iat[0]),
                uf=("geolocation_state", lambda x: x.mode().iat[0]))
           .reset_index().rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"}))

    # Avaliacoes: 1 por pedido (a mais recente) -> evita duplicar pedidos
    aval = (b["avaliacoes"].sort_values("review_answer_timestamp")
            .drop_duplicates("order_id", keep="last").copy())
    aval["avaliacao_negativa"] = (aval.review_score <= 2).astype(int)
    aval["tem_comentario"] = aval.review_comment_message.notna().astype(int)

    # Itens
    itens = b["itens"].assign(item_total=lambda d: d.price + d.freight_value)

    # Pedidos: metricas de entrega e valores agregados
    p = b["pedidos"].copy()
    p["status_pt"] = p.order_status.map(STATUS_PT)
    p["pedido_valido"] = (~p.order_status.isin(["canceled", "unavailable"])).astype(int)
    p["dias_entrega"] = ((p.order_delivered_customer_date - p.order_purchase_timestamp)
                         .dt.total_seconds() / 86400).round(2)
    p["dias_prometidos"] = ((p.order_estimated_delivery_date - p.order_purchase_timestamp)
                            .dt.total_seconds() / 86400).round(2)
    p["dias_atraso"] = (p.order_delivered_customer_date.dt.normalize()
                        - p.order_estimated_delivery_date).dt.days
    p["entregue_atrasado"] = np.where(p.order_delivered_customer_date.isna(), np.nan,
                                      (p.dias_atraso > 0).astype(float))
    p["faixa_atraso"], p["faixa_ordem"] = "Não entregue", 5
    for lo, hi, ordem, rotulo in FAIXAS:
        m = (p.dias_atraso > lo) & (p.dias_atraso <= hi)
        p.loc[m, "faixa_atraso"], p.loc[m, "faixa_ordem"] = rotulo, ordem
    agg = itens.groupby("order_id").agg(qtd_itens=("order_item_id", "count"),
                                        valor_produtos=("price", "sum"),
                                        valor_frete=("freight_value", "sum"),
                                        prazo_postagem=("shipping_limit_date", "max"),
                                        qtd_vendedores=("seller_id", "nunique")).reset_index()
    p = p.merge(agg, on="order_id", how="left")
    p["vendedor_postou_atrasado"] = np.where(p.order_delivered_carrier_date.isna(), np.nan,
                                             (p.order_delivered_carrier_date > p.prazo_postagem).astype(float))
    pag = (b["pagamentos"].groupby("order_id")
           .agg(valor_pago=("payment_value", "sum"), parcelas=("payment_installments", "max"),
                meio_pagamento=("payment_type", "first")).reset_index())
    p = p.merge(pag, on="order_id", how="left")

    return dict(f_pedidos=p, f_itens=itens, f_pagamentos=b["pagamentos"], f_avaliacoes=aval,
                d_clientes=cli, d_produtos=prod, d_vendedores=vend, d_geo_cep=geo)


def base_unica(m):
    """Base unica no grao de item. Metricas de pedido ficam so na 1a linha de cada
    pedido (sufixo _p), para que medias e somas nao contem o pedido mais de uma vez."""
    p, i = m["f_pedidos"], m["f_itens"]
    prod = m["d_produtos"].copy()
    top = (i.merge(prod, on="product_id").groupby("categoria").price.sum().nlargest(10).index)
    prod["categoria_top10"] = prod.categoria.where(prod.categoria.isin(top), "Outras")

    o = (p.merge(m["d_clientes"][["customer_id", "customer_unique_id", "customer_city",
                                  "customer_state", "customer_region"]], on="customer_id", how="left")
          .merge(m["f_avaliacoes"][["order_id", "review_score", "avaliacao_negativa"]],
                 on="order_id", how="left"))
    it = (i.merge(prod[["product_id", "categoria", "categoria_top10"]], on="product_id", how="left")
           .merge(m["d_vendedores"][["seller_id", "seller_state", "seller_region"]],
                  on="seller_id", how="left"))
    f = o.merge(it[["order_id", "order_item_id", "seller_id", "seller_state", "seller_region",
                    "categoria", "categoria_top10", "price", "freight_value"]],
                on="order_id", how="left").sort_values(["order_id", "order_item_id"])
    primeira = ~f.order_id.duplicated()
    f["review_score_item"] = f.review_score
    por_pedido = ["entregue_atrasado", "dias_entrega", "dias_prometidos", "vendedor_postou_atrasado",
                  "valor_pago", "valor_produtos", "valor_frete", "review_score", "avaliacao_negativa"]
    for c in por_pedido:
        f[c + "_p"] = f[c].where(primeira)
    f["primeira_linha_pedido"] = primeira.astype(int)
    f["categoria"] = f.categoria.fillna("Sem item")
    f["categoria_top10"] = f.categoria_top10.fillna("Outras")
    cols = ["order_id", "order_item_id", "primeira_linha_pedido", "order_purchase_timestamp",
            "order_status", "status_pt", "faixa_atraso", "faixa_ordem", "meio_pagamento",
            "customer_unique_id", "customer_city", "customer_state", "customer_region",
            "seller_id", "seller_state", "seller_region", "categoria", "categoria_top10",
            "price", "freight_value", "review_score_item"] + [c + "_p" for c in por_pedido]
    return f[cols]


if __name__ == "__main__":
    bases = ler()
    modelo = modelo_dimensional(bases)
    for nome, df in modelo.items():
        df.to_csv(OUT / f"{nome}.csv", index=False)
        print(f"{nome:14s} {len(df):>8,} linhas")
    base = base_unica(modelo)
    base.to_csv(OUT / "olist_base.csv", index=False)
    print(f"{'olist_base':14s} {len(base):>8,} linhas")
