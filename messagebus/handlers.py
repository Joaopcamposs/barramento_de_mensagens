"""Módulo de registro de handlers de comandos e eventos."""

from messagebus.messagebus import CommandHandlers, EventHandlers
from business_contexts.domain.commands.company import (
    CreateCompany,
    UpdateCompany,
    DeleteCompany,
)
from business_contexts.domain.commands.user import (
    CreateUser,
    UpdateUser,
    DeleteUser,
)
from business_contexts.domain.events.company import (
    CompanyCreated,
    CompanyUpdated,
    CompanyDeleted,
)
from business_contexts.domain.events.user import (
    UserCreated,
    UserUpdated,
    UserDeleted,
    TimeToCreateInitialCompanyUser,
    TimeToCreateCompanyAdminUser,
)
from business_contexts.services.handlers.company import (
    create_company,
    update_company,
    delete_company,
    company_created,
    company_updated,
    company_deleted,
)
from business_contexts.services.handlers.user import (
    create_user,
    update_user,
    delete_user,
    user_created,
    user_updated,
    user_deleted,
)

COMMAND_HANDLERS: CommandHandlers = CommandHandlers(
    {
        CreateCompany: create_company,
        UpdateCompany: update_company,
        DeleteCompany: delete_company,
        CreateUser: create_user,
        UpdateUser: update_user,
        DeleteUser: delete_user,
    }
)

EVENT_HANDLERS: EventHandlers = EventHandlers(
    {
        CompanyCreated: [company_created],
        CompanyUpdated: [company_updated],
        CompanyDeleted: [company_deleted],
        UserCreated: [user_created],
        UserUpdated: [user_updated],
        UserDeleted: [user_deleted],
        TimeToCreateInitialCompanyUser: [create_user],
        TimeToCreateCompanyAdminUser: [create_user],
    }
)
