# Dicionário de dados – olist_base.csv

Base única do painel, no grão de **item de pedido**. Colunas com sufixo `_p` são métricas do pedido e só aparecem na primeira linha de cada pedido (`primeira_linha_pedido = 1`), para não contar o pedido mais de uma vez.

| Coluna | Tipo | Descrição |
|---|---|---|
| `order_id` | texto | ID do pedido |
| `order_item_id` | número | Número do item dentro do pedido (vazio para pedidos sem item) |
| `primeira_linha_pedido` | inteiro | 1 na primeira linha de cada pedido; usado para métricas de pedido |
| `order_purchase_timestamp` | data/hora | Data e hora da compra |
| `order_status` | texto | Status original (inglês) |
| `status_pt` | texto | Status em português |
| `faixa_atraso` | texto | No prazo, 1-3, 4-7, 8-14, 15+ dias ou Não entregue |
| `faixa_ordem` | inteiro | Ordem da faixa (0 a 5), usada para ordenar o gráfico |
| `meio_pagamento` | texto | Meio do primeiro pagamento do pedido |
| `customer_unique_id` | texto | ID único do cliente (agrupa pedidos do mesmo cliente) |
| `customer_city` | texto | Cidade do cliente |
| `customer_state` | texto | UF do cliente |
| `customer_region` | texto | Região do cliente |
| `seller_id` | texto | ID do vendedor do item |
| `seller_state` | texto | UF do vendedor |
| `seller_region` | texto | Região do vendedor |
| `categoria` | texto | Categoria do produto (nome legível) |
| `categoria_top10` | texto | Categoria se estiver entre as 10 de maior receita; senão "Outras" |
| `price` | número | Preço do item (R$) |
| `freight_value` | número | Frete do item (R$) |
| `review_score_item` | número | Nota do pedido repetida em cada item (para análises por categoria/vendedor) |
| `entregue_atrasado_p` | número | 1 se entregue depois da data prometida (só na 1ª linha do pedido) |
| `dias_entrega_p` | número | Dias entre compra e entrega |
| `dias_prometidos_p` | número | Dias entre compra e data prometida |
| `vendedor_postou_atrasado_p` | número | 1 se o vendedor postou após o prazo limite |
| `valor_pago_p` | número | Total pago no pedido (R$) |
| `valor_produtos_p` | número | Soma dos produtos do pedido (R$) |
| `valor_frete_p` | número | Soma do frete do pedido (R$) |
| `review_score_p` | número | Nota da avaliação (1 a 5) |
| `avaliacao_negativa_p` | número | 1 se nota 1 ou 2 |

## Campos calculados no Tableau

| Campo | Fórmula |
|---|---|
| Receita | `SUM([price])` |
| Pedidos | `COUNTD([order_id])` |
| Ticket médio | `(SUM([valor_produtos_p]) + SUM([valor_frete_p])) / COUNTD([order_id])` |
| Nota média | `AVG([review_score_p])` |
| % Entregas atrasadas | `AVG([entregue_atrasado_p])` |
| % Avaliações negativas | `AVG([avaliacao_negativa_p])` |
| Prazo médio de entrega | `AVG([dias_entrega_p])` |
| Frete / produto | `SUM([freight_value]) / SUM([price])` |
| % Postagem atrasada | `AVG([vendedor_postou_atrasado_p])` |
| Pedidos por cliente (LOD) | `{ FIXED [customer_unique_id] : COUNTD([order_id]) }` |
| Taxa de recompra | `COUNTD(IF [Pedidos por cliente] > 1 THEN [customer_unique_id] END) / COUNTD([customer_unique_id])` |
