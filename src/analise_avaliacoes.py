"""
Analisa as avaliacoes dos clientes: distribuicao das notas, efeito do atraso
e temas dos comentarios negativos (nota 1 ou 2).

Os temas sao identificados por palavras-chave em portugues. E uma aproximacao:
um comentario pode cair em mais de um tema ou em nenhum.

Uso: python src/analise_avaliacoes.py   (depois de rodar preparar_dados.py)
Saida: data/processed/temas_avaliacoes_negativas.csv
"""
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW, PROC = RAIZ / "data" / "raw", RAIZ / "data" / "processed"

TEMAS = {
    "Entrega / atraso / nao recebi": r"n[aã]o receb|atras|prazo|entreg|chegou|aguardando",
    "Produto errado / incompleto": r"errad|diferente|faltando|incomplet|s[oó] (?:veio|recebi|chegou)|apenas (?:um|1)",
    "Defeito / qualidade": r"defeit|quebrad|danific|qualidade|n[aã]o funciona|ruim|p[eé]ssim",
    "Atendimento / reembolso": r"resposta|contato|atendimento|n[aã]o respond|reembols|devolu|estorno",
}

pedidos = pd.read_csv(PROC / "f_pedidos.csv", parse_dates=["order_purchase_timestamp"])
pedidos = pedidos[(pedidos.order_purchase_timestamp >= "2017-01-01")
                  & (pedidos.order_purchase_timestamp < "2018-09-01")]
aval = (pd.read_csv(RAW / "olist_order_reviews_dataset.csv")
        .sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last"))
entregues = pedidos[pedidos.status_pt == "Entregue"].merge(
    aval[["order_id", "review_score", "review_comment_message"]], on="order_id")

print("== Distribuicao das notas (pedidos entregues)")
print(entregues.review_score.value_counts(normalize=True).sort_index().map("{:.1%}".format).to_string())
print(f"\nAvaliacoes negativas (1-2): {(entregues.review_score <= 2).mean():.1%}")

print("\n== % de avaliacoes negativas: no prazo x atrasado")
neg = entregues.groupby("entregue_atrasado").review_score.apply(lambda s: (s <= 2).mean())
print(f"No prazo : {neg.get(0.0, float('nan')):.1%}")
print(f"Atrasado : {neg.get(1.0, float('nan')):.1%}")

comentarios = (aval[(aval.review_score <= 2) & aval.review_comment_message.notna()]
               .review_comment_message.str.lower())
linhas = [{"tema": t, "comentarios": int(comentarios.str.contains(rx).sum()),
           "percentual": comentarios.str.contains(rx).mean()} for t, rx in TEMAS.items()]
temas = pd.DataFrame(linhas).sort_values("comentarios", ascending=False)
temas.to_csv(PROC / "temas_avaliacoes_negativas.csv", index=False)

print(f"\n== Temas dos {len(comentarios):,} comentarios negativos")
for _, r in temas.iterrows():
    print(f"{r.tema:32s} {r.comentarios:>6,}  {r.percentual:.0%}")
