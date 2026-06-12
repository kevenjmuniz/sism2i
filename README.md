# Sistema Comercial de Recuperacao de Clientes

Sistema web para analisar o historico comercial de clientes a partir do CSV de vendas. O foco principal nao e apenas relatorio de vendas: a aplicacao ajuda a identificar quem esta comprando, quem parou de comprar, ha quantos dias nao compra, o que costumava comprar e quais clientes devem ser priorizados para contato comercial.

## Objetivo

Responder rapidamente:

- Quem devo chamar hoje?
- Quem parou de comprar?
- Ha quantos dias esse cliente nao compra?
- O que esse cliente costumava comprar?
- Quanto esse cliente costumava comprar?
- Qual cliente tem maior chance de recuperacao?
- Qual cliente representa maior valor perdido?

## Estrutura

- `backend/app`: API FastAPI, importador CSV, integracao Supabase e calculos comerciais.
- `frontend/src`: interface React.
- `backend/supabase_schema.sql`: tabelas normalizadas no Supabase.
- `backend/supabase_rpc.sql`: funcoes opcionais RPC. A versao atual consulta as tabelas via REST e calcula no backend.
- `backend/data/compras.sqlite`: banco local usado apenas quando o modo Supabase nao esta ativo.

## Banco de Dados

O sistema usa Supabase como base via API REST.

Tabelas:

- `clientes`
- `produtos`
- `pedidos`
- `itens_pedido`
- `notas_fiscais`

## Regras de Status do Cliente

Quando ha historico suficiente, o status considera a frequencia media de compra do proprio cliente.

Quando nao ha historico suficiente, usa regra padrao:

- Ate 30 dias sem comprar: `Ativo`
- 31 a 60 dias: `Atencao`
- 61 a 90 dias: `Inativo`
- Acima de 90 dias: `Perdido`

Cores:

- Verde: Ativo
- Amarelo: Atencao
- Laranja: Inativo
- Vermelho: Perdido

## Calculos Comerciais

O backend calcula:

- Primeira compra
- Ultima compra
- Dias sem comprar
- Frequencia media de compra
- Ticket medio
- Total comprado
- Quantidade de pedidos
- Produtos recorrentes
- Status do cliente
- Prioridade de recuperacao

A prioridade considera:

- Dias sem comprar
- Valor total comprado
- Ticket medio
- Frequencia anterior de compra
- Recencia da ultima compra
- Status atual

## Telas

### Dashboard

Cards principais:

- Total de clientes
- Clientes ativos
- Clientes em atencao
- Clientes inativos
- Clientes perdidos
- Faturamento total
- Ticket medio
- Total de pedidos
- Data da ultima atualizacao dos dados

Tambem mostra faturamento por mes e clientes que mais compraram.

### Clientes para Recuperar

Tabela ordenada por prioridade comercial.

Colunas:

- Cliente
- Nome fantasia
- CNPJ/CPF
- Cidade/UF
- Vendedor
- Ultima compra
- Dias sem comprar
- Status
- Valor total comprado
- Ticket medio
- Frequencia media
- Produtos recorrentes

### Clientes

Permite buscar clientes e clicar em um cliente para abrir a analise.

Ao clicar, mostra:

- Resumo do cliente
- Primeira compra
- Ultima compra
- Dias sem comprar
- Status atual
- Total comprado
- Quantidade de pedidos
- Ticket medio
- Frequencia media
- Produtos mais comprados
- Historico de pedidos

### Produtos

Mostra:

- Produtos mais vendidos
- Produtos com maior faturamento
- Clientes que compraram cada produto
- Ultima data de venda
- Quantidade total vendida
- Valor total vendido

Ao clicar em um produto, mostra os clientes que compraram, quantidade por cliente, ultima compra e valor total.

### Pedidos e Notas

Mostra pedidos e notas com:

- Data do faturamento
- Cliente
- Pedido
- Nota fiscal
- Produto
- Quantidade
- Valor unitario
- Total mercadoria
- Total nota fiscal

## Filtros Globais

Filtros disponiveis:

- Periodo
- Status do cliente
- Vendedor
- Cidade
- Estado
- Produto
- Familia de produto

Use `Aplicar filtros` para atualizar as telas e `Limpar` para remover todos os filtros.

## Configurar Supabase

Crie `backend/.env`:

```powershell
cd backend
copy .env.example .env
```

Conteudo esperado:

```env
SUPABASE_REST_MODE=true
SUPABASE_URL=https://nrbsmyudmezslzolmakj.supabase.co
SUPABASE_PUBLISHABLE_KEY=sua_publishable_key
SUPABASE_SERVICE_ROLE_KEY=sua_service_role_key_opcional_para_importar
AUTH_USERNAME=admin
AUTH_PASSWORD=troque-esta-senha
AUTH_SECRET=troque-este-segredo-por-um-texto-longo
```

Para leitura, a publishable key pode funcionar se as policies permitirem. Para importar CSV, limpar tabelas e gravar dados pelo backend, use `SUPABASE_SERVICE_ROLE_KEY` ou policies que permitam escrita.

## Login

O sistema tem login simples por usuario e senha definidos no `backend/.env`.

Variaveis:

- `AUTH_USERNAME`
- `AUTH_PASSWORD`
- `AUTH_SECRET`

Se nao forem configuradas, o backend usa `admin` / `admin` como padrao. Em producao, sempre altere essas variaveis e recrie o container.

## Instalar

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Frontend

```powershell
cd ..\frontend
npm install
npm run build
```

## Importar CSV

Com o ambiente virtual ativo:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.seed "C:\Users\keven\Downloads\consolidado (1).csv"
```

O importador:

- Valida colunas obrigatorias
- Usa separador `;`
- Le em `UTF-8-SIG`
- Converte numeros e datas
- Ignora linhas sem data utilizavel
- Evita duplicidade de itens
- Substitui os dados atuais quando roda a importacao completa

## Rodar

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8013
```

Acesse:

```text
http://127.0.0.1:8013
```

## Observacoes

- O sistema nao inventa dados.
- Todas as analises usam apenas o CSV/banco atual.
- Nao ha cadastro de visitas, contatos ou observacoes.
- O foco e leitura comercial rapida para priorizar recuperacao de clientes.
