# PocketOption Auto Trading Engine API

API intermediária assíncrona para conexão, análise técnica, geração de sinais e execução controlada de ordens via uma API externa da Pocket Option. A aplicação usa FastAPI, Pydantic v2, HTTPX, SQLAlchemy 2 assíncrono, pandas e NumPy.

> Software de negociação envolve risco financeiro. O padrão é `ENGINE_MODE=signal_only`, conta `demo` e live trading bloqueado. Valide longamente em modo de sinais e demo. Este projeto não promete lucro e não implementa Martingale, Soros ou recuperação agressiva.

## Requisitos e instalação

- Python 3.12
- pip ou Docker

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python main.py
```

Documentação interativa local: `http://localhost:8000/docs`; esquema OpenAPI: `http://localhost:8000/openapi.json`. Pelo Docker Compose, a porta publicada continua sendo `8001`.

## Configuração segura

Edite `.env` e substitua `ENGINE_MASTER_KEY`. Não versionar `.env`. Os principais limites são `MAX_ORDER_AMOUNT`, `MAX_DAILY_LOSS`, `MAX_CONSECUTIVE_LOSSES`, `MAX_ORDERS_PER_HOUR`, `MIN_SIGNAL_SCORE`, `ORDER_COOLDOWN_SECONDS` e `LOSS_COOLDOWN_SECONDS`.

Modos:

- `signal_only`: calcula e registra, nunca envia ordem (recomendado inicialmente);
- `demo_auto`: permite automação somente em demo;
- `live_auto`: requer também `ALLOW_LIVE_TRADING=true` e conta real confirmada.

O SSID existe apenas em memória. Persistem somente UUID interno, hash SHA-256, modo e estado. Logs estruturados mascaram valores sensíveis. Em implantação com múltiplas réplicas, use um cofre de segredos e coordenação distribuída; a memória local e o rate limit em memória não são compartilhados.

## Fluxo de uso

Conectar uma sessão:

```bash
curl -X POST http://localhost:8001/api/v1/connection/session \
  -H "Content-Type: application/json" \
  -d '{"ssid":"SSID_COMPLETO","persistent_connection":true,"auto_reconnect":true,"connect_after_init":true}'
```

Iniciar em modo seguro de sinais:

```bash
curl -X POST http://localhost:8001/api/v1/engine/start \
  -H "Content-Type: application/json" -H "X-Engine-Key: SUA_CHAVE" \
  -d '{"session_id":"UUID_DA_SESSAO","asset":"EURGBP_otc","timeframe_seconds":5,"expiration_seconds":30,"amount":1,"profile":"balanced","auto_execute":false,"account_mode":"demo"}'
```

Parar:

```bash
curl -X POST http://localhost:8001/api/v1/engine/stop \
  -H "Content-Type: application/json" -H "X-Engine-Key: SUA_CHAVE" \
  -d '{"engine_id":"UUID_DO_MOTOR"}'
```

## Endpoints

| Método | Rota | Proteção |
|---|---|---|
| POST / DELETE | `/api/v1/connection/session`, `/api/v1/connection/session/{id}` | validação e rate limit |
| GET | `/api/v1/account/{session_id}` | sessão válida |
| POST | `/api/v1/engine/start`, `stop`, `pause`, `resume`, `unlock-risk` | `X-Engine-Key` |
| GET / PATCH | `/api/v1/engine/config/{engine_id}` | `X-Engine-Key` |
| GET | `/api/v1/engine/status/{engine_id}` | leitura |
| GET | `/api/v1/signals`, `/api/v1/signals/latest/{engine_id}` | leitura e filtros |
| GET | `/health`, `/ready`, `/live` | probes |

Filtros de sinais: `engine_id`, `asset`, `direction`, `classification`, `decision`, `date_from`, `date_to`, `limit` e `offset`.

## Motor e estratégia

Estados válidos: `STOPPED → STARTING → RUNNING`; `RUNNING ↔ PAUSED`; e saídas para `CONNECTION_LOST`, `RISK_LOCKED`, `ERROR` ou `STOPPING → STOPPED`. Saída de `RISK_LOCKED` exige `/unlock-risk` com `confirmation=UNLOCK_RISK`.

Cada ciclo valida conexão e atualidade dos candles, calcula ADX/DMI 5/1, 10/2 e 14/14, Bollinger 20/2, Momentum 5, ZigZag 2/8/2, estrutura e SuperTrend 10/3. CALL e PUT recebem scores independentes. Diferença menor que `MIN_DIRECTION_SCORE_DIFFERENCE` não é inequívoca. Bloqueios críticos prevalecem sobre score.

Perfis: `aggressive` exige uma leitura, `balanced` duas e `conservative` três; eles também ajustam o score mínimo. A assinatura SHA-256 combina ativo, direção, timeframe, candle, cruzamento e pivô. O envio de ordem não tem retry: timeout ou falha de rede após submissão produz estado `UNKNOWN`.

## Banco e registros

SQLite assíncrono é o padrão. As tabelas são `engine_sessions`, `engine_instances`, `signal_records`, `order_records`, `risk_events` e `engine_events`. Para produção concorrente, use PostgreSQL assíncrono, migrações Alembic e armazenamento distribuído de locks/assinaturas.

As migrations são executadas com:

```bash
alembic upgrade head
```

URLs `postgres://` ou `postgresql://` fornecidas pelo Railway são normalizadas para o driver `asyncpg`. Em produção use `AUTO_CREATE_SCHEMA=false`; o pre-deploy do Railway executa Alembic antes de iniciar a aplicação.

## Railway

O arquivo `railway.toml` configura Dockerfile, `alembic upgrade head`, `/health` e reinício em falhas. O Railway injeta `PORT`; `main.py` lê essa variável e escuta em `0.0.0.0`.

Configure no painel pelo menos:

- `ENGINE_MASTER_KEY` com valor aleatório forte;
- `DATABASE_URL` do serviço PostgreSQL;
- `CORS_ORIGINS` com os domínios reais do frontend;
- `TRUSTED_HOSTS` incluindo o domínio público e `healthcheck.railway.app`;
- `ENVIRONMENT=production`, `AUTO_CREATE_SCHEMA=false` e `ALLOW_LIVE_TRADING=false`.

A aplicação recusa iniciar em produção enquanto a chave de exemplo não for substituída. Railway usa o `PORT` injetado também para o health check. HTTPS termina no proxy; a API respeita `X-Forwarded-Proto` e envia HSTS em requisições HTTPS.

## Docker

```bash
copy .env.example .env
docker compose up --build
```

O processo roda como usuário não-root e persiste o SQLite no volume `trading-data`.

## Testes

```bash
python -m pytest -q
python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=70
python -m compileall -q app tests
python -c "from app.main import app; print(app.openapi()['info'])"
```

Os testes usam `httpx.MockTransport`; não acessam nem enviam ordens reais. Antes de produção, adicione testes contratuais contra um ambiente sandbox da API externa, observabilidade centralizada, TLS no proxy, autenticação de leitura e um rate limiter compartilhado.
