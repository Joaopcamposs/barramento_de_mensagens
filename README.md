# Barramento de Mensagens

Barramento de mensagens (comandos e eventos) para integração entre contextos de negócio, implementado com **Python 3.11**, **FastAPI**, **SQLAlchemy** (async) e **PostgreSQL**. Segue os padrões de **Domain-Driven Design (DDD)**, **CQRS** e **Event-Driven Architecture**.

---

## Índice

- [Arquitetura](#arquitetura)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [O que foi implementado](#o-que-foi-implementado)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Como executar](#como-executar)
- [Testes](#testes)
- [Endpoints da API](#endpoints-da-api)
- [Como adicionar um novo domínio](#como-adicionar-um-novo-domínio)
- [Tecnologias](#tecnologias)

---

## Arquitetura

O projeto é organizado em torno de um **Message Bus** (barramento de mensagens) que roteia **Commands** e **Events** para seus respectivos handlers:

```
API (FastAPI)
  │
  ▼
Bootstrap ──► MessageBus
                │
        ┌───────┴───────┐
        ▼               ▼
   Commands          Events
   (1 handler)      (N handlers)
        │               │
        ▼               ▼
   Service Layer (Handlers)
        │
        ▼
   Unit of Work + Repositories
        │
        ▼
   PostgreSQL (asyncpg)
```

- **Command**: ação imperativa com um único handler (ex: `CreateCompany`). Retorna resultado.
- **Event**: notificação de algo que aconteceu, pode ter múltiplos handlers (ex: `CompanyCreated`). Não retorna resultado.
- **Unit of Work (UoW)**: gerencia transações e coleta eventos dos agregados após commit.
- **Bootstrap**: configura o MessageBus com injeção de dependências nos handlers.

---

## Estrutura do Projeto

```
barramento_de_mensagens/
├── messagebus/                    # Core do barramento de mensagens
│   ├── messagebus.py              # MessageBus, Command, Event
│   ├── bootstrap.py               # Bootstrap com injeção de dependências
│   ├── unity_of_work.py           # Unit of Work (abstrato e concreto)
│   ├── entities.py                # Aggregate, Repositories base, UserBase
│   ├── domains.py                 # Enum de domínios e seus repositórios
│   └── handlers.py                # Registro global de command/event handlers
│
├── business_contexts/             # Contexto de negócio (exemplo)
│   ├── main.py                    # App FastAPI (lifespan, routers)
│   ├── consts.py                  # Variáveis de ambiente
│   ├── domain/
│   │   ├── aggregate/             # Agregados (Company, User)
│   │   ├── commands/              # Comandos (Create, Update, Delete)
│   │   ├── events/                # Eventos (Created, Updated, Deleted)
│   │   ├── entitites/             # Entidades de leitura (frozen dataclasses)
│   │   └── excecoes.py            # Exceções de domínio (HTTPException)
│   ├── adapters/
│   │   ├── orm/                   # Mapeamento imperativo SQLAlchemy
│   │   ├── repository/
│   │   │   ├── domain_repo/       # Repositórios de escrita
│   │   │   └── view_repo/         # Repositórios de leitura
│   │   └── views/                 # Views (consultas via UoW)
│   ├── entrypoints/
│   │   ├── api/                   # Routers FastAPI (Company, User)
│   │   └── schemas/               # Schemas Pydantic (request/response)
│   └── services/
│       └── handlers/              # Handlers de comandos e eventos
│
├── infra/
│   └── database/                  # Engine, session factory, mapper registry
│
├── tests/
│   ├── unit/                      # Testes unitários (agregados, messagebus)
│   └── integration/               # Testes de integração (fluxo completo com DB)
│
├── pyproject.toml                 # Dependências e config do projeto
├── Dockerfile                     # Imagem Docker (Python 3.11 + uv)
├── docker-compose.yml             # API + PostgreSQL
├── docker-compose.test.yml        # PostgreSQL para testes de integração
└── Makefile                       # Atalhos de comandos
```

---

## O que foi implementado

### MessageBus (Core)
- **`MessageBus`**: processa mensagens (commands/events) em fila, coletando novos eventos gerados durante o processamento.
- **`Command`** e **`Event`**: classes base (dataclasses) para tipagem de mensagens.
- **`Bootstrap`**: inicializa o bus com injeção automática de dependências (UoW) nos handlers via introspecção de assinatura.
- **`Unit of Work`**: gerencia sessões SQLAlchemy (escrita + leitura separadas), transações com commit/rollback, e coleta de eventos dos agregados.
- **Tratamento de erros**: comandos sempre propagam exceções; eventos podem capturar e enviar ao Sentry em ambientes produtivos.

### Domínios de Negócio

#### Company
- **Agregado** com campos: `legal_name`, `trade_name`, `responsible_name`, `email`, `cpf`, `cnpj`, `active`.
- **Operações** `create`, `update`, `delete` — cada uma emite evento correspondente.
- **Comandos**: `CreateCompany`, `UpdateCompany`, `DeleteCompany`.
- **Eventos**: `CompanyCreated`, `CompanyUpdated`, `CompanyDeleted`.
- **Criação automática de usuários**: ao criar uma empresa, eventos `TimeToCreateInitialCompanyUser` e `TimeToCreateCompanyAdminUser` são emitidos (controlável via flag `should_create_user`).
- **API REST**: CRUD completo via endpoints `/v1/company`.
- **Validações**: razão social única (409), empresa não encontrada (404).

#### User
- **Agregado** com campos: `email`, `cpf`, `password`, `active`, `admin`.
- **Operações** `create`, `update`, `delete` — cada uma emite evento correspondente.
- **Comandos**: `CreateUser`, `UpdateUser`, `DeleteUser`.
- **Eventos**: `UserCreated`, `UserUpdated`, `UserDeleted`, `TimeToCreateInitialCompanyUser`, `TimeToCreateCompanyAdminUser`.
- **API REST**: CRUD completo via endpoints `/v1/user`.
- **Regra de consulta**: `company` é obrigatório em todas as consultas de usuário — somente usuários da empresa informada são retornados.
- **Validações**: email único (409), usuário não encontrado (404).
- **Relacionamento**: FK para `company`.

### Infraestrutura
- **PostgreSQL 16** via Docker.
- **SQLAlchemy async** com `asyncpg` e mapeamento imperativo (ORM).
- **Separação de sessões**: sessão de escrita (READ COMMITTED) e leitura (AUTOCOMMIT).
- **Criação automática de tabelas** no lifespan da aplicação.
- **UUID7** para geração de IDs ordenáveis.

### Testes
- **Unitários** (80 testes): agregados, comandos, eventos, entidades, schemas, MessageBus com fake UoW.
- **Integração** (39 testes): fluxo completo (create → view → update → delete) com PostgreSQL de teste, incluindo fluxo empresa → usuários, isolamento multi-empresa e ciclo de vida completo.
- **Fixtures**: engine com criação de tabelas e limpeza de dados entre testes (per-test scope para evitar problemas de event loop).

---

## Pré-requisitos

- **Python** >= 3.11
- **Docker** e **Docker Compose**
- **uv** (gerenciador de pacotes Python) — instalado automaticamente no Docker

---

## Instalação

### Local (desenvolvimento)

```bash
# Clone o repositório
git clone <repo-url>
cd barramento_de_mensagens

# Instale o uv (se ainda não tiver)
pip install uv

# Instale as dependências
uv sync
```

### Docker

```bash
# Sobe API + PostgreSQL
make compose
```

---

## Configuração

Crie um arquivo `.env` na raiz do projeto baseado no `.env_example`:

```env
DB_HOST=localhost
DB_PASSWORD=password
DB_USER=postgres
DB_NAME=postgres
```

> No Docker, `DB_HOST` é configurado automaticamente como `postgres` (nome do serviço).

---

## Como executar

### Via Docker (recomendado)

```bash
# API + banco de dados
make compose

# Apenas o PostgreSQL
make postgres
```

A API estará disponível em `http://localhost:8000`. Documentação interativa em `http://localhost:8000/docs`.

### Local

```bash
# Suba o PostgreSQL
make postgres

# Execute a API
uvicorn business_contexts.main:app --host 0.0.0.0 --port 8000
```

---

## Testes

```bash
# Testes unitários (sem dependências externas)
make test-unit

# Testes de integração (sobe/desce PostgreSQL de teste automaticamente)
make test-integration

# Todos os testes
make test-all
```

---

## Endpoints da API

### Health Check
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Health check |

### Company (`/v1/company`)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/v1/company` | Cria uma empresa |
| PUT | `/v1/company` | Atualiza uma empresa |
| GET | `/v1/company` | Lista empresas (filtro opcional por `legal_name`) |
| DELETE | `/v1/company` | Exclui uma empresa por `legal_name` |

### User (`/v1/user`)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/v1/user` | Cria um usuário |
| PUT | `/v1/user` | Atualiza um usuário |
| GET | `/v1/user` | Lista usuários por `company` (filtro opcional por `email`) |
| DELETE | `/v1/user` | Exclui um usuário por `company` + `email` |

---

## Como adicionar um novo domínio

Para adicionar um novo domínio (ex: `Product`), siga estes passos:

### 1. Criar o agregado

Crie `business_contexts/domain/aggregate/product.py`:

```python
@dataclass
class Product(Aggregate):
    id: UUID
    name: str
    price: float

    def __hash__(self) -> int:
        return hash(self.id)

    @staticmethod
    def create_aggregate(name: str, price: float) -> "Product":
        return Product(id=uuid7.create(), name=name, price=price)

    def create(self) -> None:
        self._operation_type = OperationType.INSERT
        self.add_event(ProductCreated(id=self.id))
```

### 2. Criar comandos e eventos

- `business_contexts/domain/commands/product.py` — ex: `CreateProduct(Command)`
- `business_contexts/domain/events/product.py` — ex: `ProductCreated(Event)`

### 3. Criar o mapeamento ORM

Crie `business_contexts/adapters/orm/product.py` com a `Table` e o `map_imperatively`. Importe-o em `business_contexts/adapters/orm/__init__.py`.

### 4. Criar repositórios

- `business_contexts/adapters/repository/domain_repo/product.py` — repositório de escrita
- `business_contexts/adapters/repository/view_repo/product.py` — repositório de leitura

### 5. Registrar o domínio

Em `messagebus/domains.py`, adicione:

```python
class Domain(Enum):
    product = (ProductDomainRepo, ProductViewRepo)
```

### 6. Criar handlers

Crie `business_contexts/services/handlers/product.py` com os handlers de comando e evento.

### 7. Registrar handlers

Em `messagebus/handlers.py`, adicione os comandos e eventos nos dicionários `COMMAND_HANDLERS` e `EVENT_HANDLERS`.

### 8. Criar endpoints, schemas e views

- `business_contexts/entrypoints/api/product.py` — router FastAPI
- `business_contexts/entrypoints/schemas/product.py` — schemas Pydantic
- `business_contexts/adapters/views/product.py` — view de consulta

Inclua o router em `business_contexts/main.py`.

### 9. Criar testes

- `tests/unit/test_product.py` — testes do agregado, comandos e eventos
- `tests/integration/test_product_integration.py` — testes de fluxo completo

---

## Tecnologias

| Tecnologia | Uso |
|------------|-----|
| **Python 3.11** | Linguagem principal |
| **FastAPI** | Framework web assíncrono |
| **SQLAlchemy 2.0** | ORM com mapeamento imperativo |
| **asyncpg** | Driver async para PostgreSQL |
| **PostgreSQL 16** | Banco de dados relacional |
| **Pydantic** | Validação de schemas |
| **uuid7** | Geração de UUIDs ordenáveis |
| **Sentry SDK** | Monitoramento de erros (produção) |
| **uv** | Gerenciador de pacotes e virtualenv |
| **Docker** | Containerização |
| **pytest** | Framework de testes |
| **Ruff** | Linter e formatter |

---

## Comandos úteis (Makefile)

```bash
make ruff              # Formata e lint do código
make compose           # Sobe API + PostgreSQL via Docker
make postgres          # Sobe apenas o PostgreSQL
make test-unit         # Testes unitários
make test-integration  # Testes de integração
make test-all          # Todos os testes
make docker-clean      # Limpa imagens/containers Docker
```
