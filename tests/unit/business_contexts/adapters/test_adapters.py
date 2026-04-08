"""Testes unitários do contexto de adapters (ORM, repositórios e views)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
import uuid7

from business_contexts.adapters.orm import start_mappers
from business_contexts.adapters.repository.domain_repo.audit_log import (
    AbstractAuditLogDomainRepo,
    AuditLogDomainRepo,
)
from business_contexts.adapters.repository.domain_repo.company import (
    CompanyDomainRepo,
)
from business_contexts.adapters.repository.domain_repo.user import (
    UserDomainRepo,
)
from business_contexts.adapters.repository.mixins.public_user import PublicUserMixin
from business_contexts.adapters.repository.mixins.upsert import UpsertMixin
from business_contexts.adapters.repository.view_repo.audit_log import AuditLogViewRepo
from business_contexts.adapters.repository.view_repo.company import CompanyViewRepo
from business_contexts.adapters.repository.view_repo.user import UserViewRepo
from business_contexts.adapters.views.audit_log import view_audit_log
from business_contexts.adapters.views.company import view_company
from business_contexts.adapters.views.user import view_user
from business_contexts.domain.aggregate.company import Company
from business_contexts.domain.aggregate.user import PublicUser, User
from business_contexts.domain.excecoes import (
    CompanyAlreadyRegistered,
    CompanyNotFound,
    UserAlreadyRegistered,
    UserNotFound,
)
from business_contexts.domain.value_objects.enums import AuditOperation
from messagebus.entities import AuditableEvent, OperationType
from tests.unit.helpers import FakeAsyncSession, FakeResult, FakeUoW


class FakeQuery:
    """Query fake encadeável para simular where/order_by."""

    def where(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self

    def order_by(self, *args: Any, **kwargs: Any) -> "FakeQuery":
        return self


class TestOrmModule:
    """Testes do módulo ORM agregador."""

    def test_start_mappers_is_noop(self) -> None:
        """Cobre função start_mappers, que atualmente é no-op."""
        assert start_mappers() is None


class TestUpsertAndPublicUserMixins:
    """Testes para mixins reutilizáveis de persistência."""

    @pytest.mark.asyncio
    async def test_execute_upsert_insert_and_update_and_delete(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Executa caminhos de insert/update e soft delete no mixin."""

        class Repo(UpsertMixin):
            def __init__(self) -> None:
                self.session = FakeAsyncSession()

        class AggregateTable:
            id = "id-column"

        class InsertOp:
            def __init__(self, model: Any) -> None:
                self.model = model

            def values(self, data: dict[str, Any]) -> tuple[str, Any, dict[str, Any]]:
                return ("insert", self.model, data)

        class UpdateOp:
            def __init__(self, model: Any) -> None:
                self.model = model
                self.criteria: tuple[Any, ...] | None = None

            def where(self, *criteria: Any) -> "UpdateOp":
                self.criteria = criteria
                return self

            def values(
                self, data: dict[str, Any]
            ) -> tuple[str, Any, tuple[Any, ...] | None, dict[str, Any]]:
                return ("update", self.model, self.criteria, data)

        monkeypatch.setattr(
            "business_contexts.adapters.repository.mixins.upsert.insert",
            lambda model: InsertOp(model),
        )
        monkeypatch.setattr(
            "business_contexts.adapters.repository.mixins.upsert.update",
            lambda model: UpdateOp(model),
        )

        aggregate = SimpleNamespace(
            id=uuid7.create(),
            deleted_at=datetime.now(timezone.utc),
            deleted_by=uuid7.create(),
            operation_type=OperationType.INSERT,
        )

        repo = Repo()
        await repo._execute_upsert(AggregateTable, aggregate, {"id": aggregate.id})

        aggregate.operation_type = OperationType.UPDATE
        await repo._execute_upsert(AggregateTable, aggregate, {"id": aggregate.id})

        await repo._execute_soft_delete(AggregateTable, aggregate)

        assert len(repo.session.execute_calls) == 3

    @pytest.mark.asyncio
    async def test_public_user_mixin_get_add_and_remove(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valida busca, escrita e remoção lógica no mixin de usuário público."""

        class Repo(PublicUserMixin):
            def __init__(self, session: FakeAsyncSession) -> None:
                self.session = session

        monkeypatch.setattr(
            "business_contexts.adapters.repository.mixins.public_user.select",
            lambda *_: FakeQuery(),
        )

        row = SimpleNamespace(
            id=uuid7.create(),
            company=uuid7.create(),
            email_encrypted=b"encrypted",
            email_lookup_hmac="hash",
            cpf_lookup_hmac="cpf-hash",
        )
        session = FakeAsyncSession(execute_results=[FakeResult(scalar=row)])
        repo = Repo(session)

        found = await repo.get_public_user_by_id(row.id)
        assert found is not None
        assert found.id == row.id

        missing_repo = Repo(FakeAsyncSession(execute_results=[FakeResult(scalar=None)]))
        not_found = await missing_repo.get_public_user_by_id(uuid7.create())
        assert not_found is None

        public_user = PublicUser(
            id=row.id,
            company=row.company,
            email_encrypted=b"x",
            email_lookup_hmac="h",
            cpf_lookup_hmac="cpf-hash",
        )
        await repo.add_public_user(public_user)

        public_user.update_cpf(cpf="12345678901")
        await repo.update_public_user_cpf(public_user)

        public_user.remove()
        await repo.remove_public_user(public_user)

        assert len(session.execute_calls) == 4


class TestDomainRepositories:
    """Testes dos repositórios de domínio concretos e abstratos."""

    @pytest.mark.asyncio
    async def test_abstract_audit_repo_add_tracks_seen_items(self) -> None:
        """Adiciona item em seen ao usar método add do repositório abstrato."""

        class Repo(AbstractAuditLogDomainRepo):
            async def _add(self, audit_log: Any) -> None:
                return None

        repo = Repo()
        from business_contexts.domain.aggregate.audit_log import AuditLog

        audit = AuditLog.create_aggregate(
            entity_type="User",
            entity_id=uuid7.create(),
            operation="CREATE",
        )

        await repo.add(audit)

        assert audit in repo.seen

    @pytest.mark.asyncio
    async def test_company_domain_repo_create_aggregate_and_get_by_legal_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cobre criação/busca de agregados no repositório de empresa."""
        monkeypatch.setattr(
            "business_contexts.adapters.repository.domain_repo.company.select",
            lambda *_: FakeQuery(),
        )

        repo = CompanyDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=None)])
        )
        monkeypatch.setattr(repo, "validate_company_email", AsyncMock())

        aggregate = await repo.create_aggregate(
            legal_name="Acme",
            trade_name="Acme",
            responsible_name="John",
            email="john@example.com",
            cpf="12345678901",
            cnpj=None,
            active=True,
        )
        assert aggregate.legal_name == "Acme"

        repo_dup = CompanyDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=object())])
        )
        monkeypatch.setattr(repo_dup, "validate_company_email", AsyncMock())
        with pytest.raises(CompanyAlreadyRegistered):
            await repo_dup.create_aggregate(
                legal_name="Acme",
                trade_name=None,
                responsible_name="J",
                email="j@example.com",
                cpf="12345678901",
                cnpj=None,
                active=True,
            )

        row = SimpleNamespace(
            id=uuid7.create(),
            legal_name="Acme",
            trade_name="Acme",
            responsible_name="John",
            email="john@example.com",
            cpf="12345678901",
            cnpj=None,
            active=True,
            created_at=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
            deleted_at=None,
            deleted_by=None,
        )
        repo_found = CompanyDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=row)])
        )
        found = await repo_found.get_by_legal_name("Acme")
        assert found.email == "john@example.com"

        repo_missing = CompanyDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=None)])
        )
        with pytest.raises(CompanyNotFound):
            await repo_missing.get_by_legal_name("missing")

    @pytest.mark.asyncio
    async def test_company_domain_repo_add_and_remove_and_seen(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cobre persistência via _add/_remove e rastreamento de agregados."""
        repo = CompanyDomainRepo(session=FakeAsyncSession())
        company = Company.create_aggregate(
            legal_name="Acme",
            trade_name=None,
            responsible_name="John",
            email="john@example.com",
            cpf="12345678901",
            cnpj=None,
            active=True,
        )
        company.create(password="secret")

        called: dict[str, Any] = {}

        async def fake_execute_upsert(
            model: Any, aggregate: Any, data: dict[str, Any]
        ) -> None:
            called["upsert"] = (model, aggregate, data)

        async def fake_soft_delete(model: Any, aggregate: Any) -> None:
            called["soft_delete"] = (model, aggregate)

        monkeypatch.setattr(repo, "_execute_upsert", fake_execute_upsert)
        monkeypatch.setattr(repo, "_execute_soft_delete", fake_soft_delete)

        await repo.add(company)
        company.delete()
        await repo.remove(company)

        assert company in repo.seen
        assert called["upsert"][1] is company
        assert called["soft_delete"][1] is company

    @pytest.mark.asyncio
    async def test_company_domain_repo_validate_company_email_calls_infra(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Encaminha validação de email para camada de infraestrutura."""
        captured: list[str] = []

        async def fake_validate(email: str) -> None:
            captured.append(email)

        monkeypatch.setattr("infra.database.validate_company_email", fake_validate)

        await CompanyDomainRepo.validate_company_email("john@example.com")

        assert captured == ["john@example.com"]

    @pytest.mark.asyncio
    async def test_user_domain_repo_create_and_get_and_add_remove(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cobre caminhos de criação, leitura e persistência do usuário."""
        monkeypatch.setattr(
            "business_contexts.adapters.repository.domain_repo.user.select",
            lambda *_: FakeQuery(),
        )

        repo = UserDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=None)])
        )
        aggregate = await repo.create_aggregate(
            company=uuid7.create(),
            email="user@example.com",
            cpf="12345678901",
            password="secret",
        )
        assert aggregate.email == "user@example.com"

        repo_dup = UserDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=object())])
        )
        with pytest.raises(UserAlreadyRegistered):
            await repo_dup.create_aggregate(
                company=uuid7.create(),
                email="user@example.com",
                cpf="12345678901",
                password="secret",
            )

        row = SimpleNamespace(
            id=uuid7.create(),
            company=uuid7.create(),
            email="user@example.com",
            cpf="12345678901",
            password_hash="hash",
            active=True,
            admin=False,
            created_at=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
            deleted_at=None,
            deleted_by=None,
        )
        repo_found = UserDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=row)])
        )
        found_by_email = await repo_found.get_by_email("user@example.com")
        assert found_by_email.id == row.id

        repo_by_id = UserDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=row)])
        )
        found_by_id = await repo_by_id.get_by_id(row.id)
        assert found_by_id.email == "user@example.com"

        repo_missing = UserDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=None)])
        )
        with pytest.raises(UserNotFound):
            await repo_missing.get_by_email("missing")

        repo_missing_id = UserDomainRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=None)])
        )
        with pytest.raises(UserNotFound):
            await repo_missing_id.get_by_id(uuid7.create())

        called: dict[str, Any] = {}

        async def fake_execute_upsert(
            model: Any, aggregate: Any, data: dict[str, Any]
        ) -> None:
            called["upsert"] = (model, aggregate, data)

        async def fake_soft_delete(model: Any, aggregate: Any) -> None:
            called["soft_delete"] = (model, aggregate)

        repo_actions = UserDomainRepo(session=FakeAsyncSession())
        monkeypatch.setattr(repo_actions, "_execute_upsert", fake_execute_upsert)
        monkeypatch.setattr(repo_actions, "_execute_soft_delete", fake_soft_delete)

        user = User.create_aggregate(
            company=uuid7.create(),
            email="user@example.com",
            cpf="12345678901",
            password="secret",
        )
        user.create()
        await repo_actions.add(user)
        user.delete()
        await repo_actions.remove(user)

        assert user in repo_actions.seen
        assert called["upsert"][1] is user
        assert called["soft_delete"][1] is user

    @pytest.mark.asyncio
    async def test_audit_log_domain_repo_create_from_event_and_add(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cria log a partir de evento auditável e persiste dados."""

        @dataclass(kw_only=True, frozen=True)
        class DemoEvent(AuditableEvent):
            id: Any

        event = DemoEvent(
            id=uuid7.create(), entity_type="User", old_data={"a": 1}, new_data={"a": 2}
        )

        repo = AuditLogDomainRepo(session=FakeAsyncSession())
        monkeypatch.setattr(repo, "add", AsyncMock())

        created = await repo.create_from_event(
            event=event,
            entity_id=event.id,
            operation=AuditOperation.UPDATE,
            user_id=uuid7.create(),
        )

        assert created.entity_type == "User"
        repo.add.assert_awaited_once()  # type: ignore[union-attr]

        class InsertOp:
            def __init__(self, model: Any) -> None:
                self.model = model

            def values(self, data: dict[str, Any]) -> tuple[str, Any, dict[str, Any]]:
                return ("insert", self.model, data)

        monkeypatch.setattr(
            "business_contexts.adapters.repository.domain_repo.audit_log.insert",
            lambda model: InsertOp(model),
        )

        audit = created
        repo_persist = AuditLogDomainRepo(session=FakeAsyncSession())
        await repo_persist._add(audit)
        assert repo_persist.session.execute_calls


class TestViewRepositoriesAndAdaptersViews:
    """Testes para repositórios de leitura e adapters de view."""

    @pytest.mark.asyncio
    async def test_company_view_repo_and_view_adapter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cobre busca por nome e listagem de empresas."""
        monkeypatch.setattr(
            "business_contexts.adapters.repository.view_repo.company.select",
            lambda *_: FakeQuery(),
        )

        row = SimpleNamespace(
            id=uuid7.create(),
            legal_name="Acme",
            trade_name="Acme",
            responsible_name="John",
            email="john@example.com",
            cpf="12345678901",
            cnpj=None,
            active=True,
            created_at=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
            deleted_at=None,
            deleted_by=None,
        )

        repo = CompanyViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=row)])
        )
        found = await repo.get_by_legal_name("Acme", include_deleted=True)
        assert found and found.legal_name == "Acme"

        repo_none = CompanyViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=None)])
        )
        assert await repo_none.get_by_legal_name("missing") is None

        repo_all = CompanyViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalars=[row])])
        )
        assert len(await repo_all.get_all()) == 1

        repo_empty = CompanyViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalars=[])])
        )
        assert await repo_empty.get_all(include_deleted=True) == []

        view_repo = SimpleNamespace(
            get_by_legal_name=AsyncMock(return_value=row),
            get_all=AsyncMock(return_value=[row]),
        )
        uow = FakeUoW(view_repo=view_repo)

        single = await view_company(uow, legal_name="Acme", include_deleted=False)
        all_companies = await view_company(uow, legal_name=None, include_deleted=True)

        assert len(single) == 1
        assert all_companies == [row]

        view_repo_missing = SimpleNamespace(
            get_by_legal_name=AsyncMock(return_value=None),
            get_all=AsyncMock(return_value=[]),
        )
        empty = await view_company(FakeUoW(view_repo=view_repo_missing), legal_name="X")
        assert empty == []

    @pytest.mark.asyncio
    async def test_user_view_repo_and_view_adapter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cobre consulta de usuários privados e públicos."""
        monkeypatch.setattr(
            "business_contexts.adapters.repository.view_repo.user.select",
            lambda *_: FakeQuery(),
        )

        row = SimpleNamespace(
            id=uuid7.create(),
            company=uuid7.create(),
            email="user@example.com",
            cpf="12345678901",
            active=True,
            admin=False,
            password_hash="hash",
            created_at=None,
            created_by=None,
            updated_at=None,
            updated_by=None,
            deleted_at=None,
            deleted_by=None,
            email_encrypted=b"x",
            email_lookup_hmac="h",
            cpf_lookup_hmac="cpf-hash",
        )

        repo = UserViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=row)])
        )
        assert (await repo.get_by_email("user@example.com")) is not None

        repo_none = UserViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=None)])
        )
        assert await repo_none.get_by_email("missing", include_deleted=True) is None

        repo_id = UserViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=row)])
        )
        assert (await repo_id.get_by_id(row.id)) is not None

        repo_id_none = UserViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=None)])
        )
        assert await repo_id_none.get_by_id(uuid7.create()) is None

        repo_all = UserViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalars=[row])])
        )
        assert len(await repo_all.get_all()) == 1

        repo_all_empty = UserViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalars=[])])
        )
        assert await repo_all_empty.get_all(include_deleted=True) == []

        repo_public = UserViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=row)])
        )
        monkeypatch.setattr(
            PublicUser,
            "compute_email_lookup_hmac",
            staticmethod(lambda email: f"h:{email}"),
        )
        assert (
            await repo_public.get_public_user_by_email("user@example.com")
        ) is not None

        repo_public_none = UserViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalar=None)])
        )
        assert (
            await repo_public_none.get_public_user_by_email("missing@example.com") is None
        )

        view_repo = SimpleNamespace(
            get_by_email=AsyncMock(return_value=row),
            get_all=AsyncMock(return_value=[row]),
        )
        uow = FakeUoW(view_repo=view_repo)
        single = await view_user(uow, email="user@example.com")
        many = await view_user(uow, include_deleted=True)

        assert len(single) == 1
        assert many == [row]

        empty = await view_user(
            FakeUoW(
                view_repo=SimpleNamespace(
                    get_by_email=AsyncMock(return_value=None),
                    get_all=AsyncMock(return_value=[]),
                )
            ),
            email="missing@example.com",
        )
        assert empty == []

    @pytest.mark.asyncio
    async def test_audit_log_view_repo_and_view_adapter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cobre filtros por entidade e consulta total de auditoria."""
        monkeypatch.setattr(
            "business_contexts.adapters.repository.view_repo.audit_log.select",
            lambda *_: FakeQuery(),
        )
        monkeypatch.setattr(
            "business_contexts.adapters.repository.view_repo.audit_log.desc",
            lambda value: value,
        )

        row = SimpleNamespace(
            id=uuid7.create(),
            entity_type="User",
            entity_id=uuid7.create(),
            operation="UPDATE",
            old_data={"a": 1},
            new_data={"a": 2},
            user_id=uuid7.create(),
            created_at=datetime.now(timezone.utc),
        )

        repo = AuditLogViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalars=[row])])
        )
        by_entity = await repo.get_by_entity("User", row.entity_id)
        assert len(by_entity) == 1

        repo_type = AuditLogViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalars=[row])])
        )
        by_type = await repo_type.get_by_entity_type("User")
        assert len(by_type) == 1

        repo_all = AuditLogViewRepo(
            session=FakeAsyncSession(execute_results=[FakeResult(scalars=[row])])
        )
        all_logs = await repo_all.get_all()
        assert len(all_logs) == 1

        view_repo = SimpleNamespace(
            get_by_entity=AsyncMock(return_value=[row]),
            get_by_entity_type=AsyncMock(return_value=[row]),
            get_all=AsyncMock(return_value=[row]),
        )
        uow = FakeUoW(view_repo=view_repo)

        filtered_both = await view_audit_log(
            uow, entity_type="User", entity_id=row.entity_id
        )
        filtered_type = await view_audit_log(uow, entity_type="User")
        unfiltered = await view_audit_log(uow)

        assert filtered_both == [row]
        assert filtered_type == [row]
        assert unfiltered == [row]
