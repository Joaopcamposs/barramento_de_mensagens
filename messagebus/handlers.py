"""Módulo de registro de handlers de comandos e eventos."""

from business_contexts.domain.commands.company import (
    CreateCompany,
    DeleteCompany,
    UpdateCompany,
)
from business_contexts.domain.commands.security import AuthenticateUser
from business_contexts.domain.commands.user import (
    CreateUser,
    DeleteUser,
    UpdateUser,
)
from business_contexts.domain.events.company import (
    CompanyCreated,
    CompanyDeleted,
    CompanyUpdated,
)
from business_contexts.domain.events.user import (
    TimeToCreateCompanyAdminUser,
    TimeToCreateInitialCompanyUser,
    UserCreated,
    UserDeleted,
    UserUpdated,
)
from business_contexts.services.handlers.company import (
    company_created,
    company_deleted,
    company_updated,
    create_company,
    delete_company,
    update_company,
)
from business_contexts.services.handlers.security import authenticate_user
from business_contexts.services.handlers.user import (
    create_public_user,
    create_user,
    delete_user,
    remove_public_user,
    update_public_user,
    update_user,
    user_created,
    user_deleted,
    user_updated,
)
from messagebus.messagebus import CommandHandlers, EventHandlers

COMMAND_HANDLERS: CommandHandlers = CommandHandlers(
    {
        CreateCompany: create_company,
        UpdateCompany: update_company,
        DeleteCompany: delete_company,
        CreateUser: create_user,
        UpdateUser: update_user,
        DeleteUser: delete_user,
        AuthenticateUser: authenticate_user,
    }
)

EVENT_HANDLERS: EventHandlers = EventHandlers(
    {
        CompanyCreated: [company_created],
        CompanyUpdated: [company_updated],
        CompanyDeleted: [company_deleted],
        UserCreated: [user_created, create_public_user],
        UserUpdated: [user_updated, update_public_user],
        UserDeleted: [user_deleted, remove_public_user],
        TimeToCreateInitialCompanyUser: [create_user],
        TimeToCreateCompanyAdminUser: [create_user],
    }
)
