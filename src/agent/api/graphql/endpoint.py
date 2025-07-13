from fastapi import FastAPI, Request, Depends, HTTPException, status
from strawberry.fastapi import GraphQLRouter
import logging

from .schema import schema, GraphQLContext
from ...enterprise.auth import User

logger = logging.getLogger(__name__)


async def get_graphql_context(
    request: Request,
    current_user: User = None
) -> GraphQLContext:
    context = GraphQLContext(
        user=current_user,
        tenant_id=current_user.tenant_id if current_user else None
    )
    
    if hasattr(request.app.state, 'agent_registry'):
        context.agent_registry = request.app.state.agent_registry
    
    if hasattr(request.app.state, 'workflow_registry'):
        context.workflow_registry = request.app.state.workflow_registry
    
    return context


async def get_authenticated_context(
    request: Request,
    auth_deps: dict
) -> GraphQLContext:
    try:
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        
        security = HTTPBearer()
        credentials = await security(request)
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for GraphQL"
            )
        
        current_user = await auth_deps['get_current_user'](credentials)
        return await get_graphql_context(request, current_user)
    
    except Exception as e:
        logger.warning(f"GraphQL authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication for GraphQL"
        )


def create_graphql_router(auth_deps: dict, require_auth: bool = True) -> GraphQLRouter:
    if require_auth:
        async def context_getter(request: Request):
            return await get_authenticated_context(request, auth_deps)
    else:
        async def context_getter(request: Request):
            return await get_graphql_context(request)
    
    graphql_app = GraphQLRouter(
        schema,
        context_getter=context_getter,
        graphiql=True
    )
    
    return graphql_app