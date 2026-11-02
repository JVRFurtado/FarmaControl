# FarmaControl — API JSON (somente leitura)

API para integrar o FarmaControl com outros sistemas (painéis, planilhas, scripts). Entrega os mesmos dados das telas, com as mesmas regras de acesso, e **não altera nada** no banco.

- **Base:** `https://farmacontrol-mxr1.onrender.com/api/` (local: `http://127.0.0.1:8000/api/`)
- **Formato:** JSON UTF-8; datas em ISO 8601 (`AAAA-MM-DD`).
- **Métodos:** apenas `GET` (os demais retornam `405`).
- **Autenticação:** a mesma sessão do site. Qualquer usuário ativo (Atendente, Gestor ou Admin) pode consultar. Sem login → `401` em JSON.
- **Paginação:** `?page=` e `?por_pagina=` (padrão 50, máximo 100).
- **Erros:** `{"erro": "mensagem"}` com status `400`, `401`, `404` ou `405`.

## Endpoints

| Endpoint | Descrição | Parâmetros |
|---|---|---|
| `GET /api/` | Índice da API | — |
| `GET /api/produtos/` | Produtos e medicamentos (paginado) | `buscar`, `categoria` (id), `filtro` (`estoque_baixo`, `vencendo`, `vencidos`, `normal`) |
| `GET /api/produtos/{id}/` | Detalhe de um item | — |
| `GET /api/alertas/` | Totais e listas de vencidos, vencendo (≤ 30 dias) e estoque baixo | — |
| `GET /api/categorias/` | Categorias | — |
| `GET /api/entregas/` | Histórico de entregas (paginado) | `produto` (id), `buscar` (produto ou paciente) |
| `GET /api/movimentacoes/` | Entradas e saídas de estoque (paginado) | `produto` (id), `tipo` (`ENTRADA`/`SAIDA`) |

### Exemplo de item de produto
```json
{
  "id": 7,
  "tipo": "medicamento",
  "nome": "Dipirona",
  "dosagem": "500 mg",
  "categoria": "Analgésicos",
  "categoria_id": 1,
  "quantidade": 30,
  "estoque_minimo": 5,
  "estoque_baixo": false,
  "data_validade": "2027-01-30",
  "dias_para_vencer": 90,
  "status_validade": "normal",
  "ultima_compra": null,
  "altura_cm": null,
  "largura_cm": null,
  "comprimento_cm": null
}
```
`status_validade`: `normal` (> 30 dias), `aviso` (≤ 30 dias), `vencido`, ou `null` sem data de validade.

### Resposta paginada
```json
{ "count": 120, "page": 1, "pages": 3, "por_pagina": 50, "results": [ ... ] }
```

## Exemplos de uso

**curl** (login por sessão):
```bash
URL=https://farmacontrol-mxr1.onrender.com
curl -c cookies.txt -s $URL/usuarios/login/ -o /dev/null
TOKEN=$(grep csrftoken cookies.txt | awk '{print $7}')
curl -b cookies.txt -c cookies.txt -s -o /dev/null \
     -d "username=atendente&password=SUA_SENHA&csrfmiddlewaretoken=$TOKEN" \
     -H "Referer: $URL/usuarios/login/" $URL/usuarios/login/
curl -b cookies.txt "$URL/api/alertas/"
curl -b cookies.txt "$URL/api/produtos/?filtro=vencendo"
```

**Python** (`requests`):
```python
import re, requests

URL = "https://farmacontrol-mxr1.onrender.com"
s = requests.Session()
html = s.get(f"{URL}/usuarios/login/").text
token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
s.post(f"{URL}/usuarios/login/", data={"username": "atendente", "password": "SUA_SENHA",
       "csrfmiddlewaretoken": token}, headers={"Referer": f"{URL}/usuarios/login/"})

alertas = s.get(f"{URL}/api/alertas/").json()
print(alertas["totais"])
```

**JavaScript** (no navegador, já logado no site):
```js
const r = await fetch('/api/produtos/?filtro=estoque_baixo');
const dados = await r.json();
console.log(dados.count, dados.results);
```

## Notas de projeto
- Implementada em `estoque/api.py` (views) e `estoque/api_urls.py` (rotas), sem dependências novas.
- Reaproveita `ProdutoQuerySet`, portanto as regras de estoque baixo e vencimento são idênticas às do dashboard e dos relatórios.
- Testes em `estoque/tests/test_api.py` (autenticação, métodos, filtros, paginação, erros e conteúdo).
- Possíveis evoluções: autenticação por token, endpoints de escrita e documentação OpenAPI.
