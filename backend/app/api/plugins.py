"""REST API for managing and introspecting registered plugins."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..api.auth import get_current_user
from ..models.user import User, UserRole
from ..plugins import registry

router = APIRouter(prefix="/plugins", tags=["plugins"])


class PluginInfo(BaseModel):
    name: str
    version: str
    description: str
    enabled: bool

    model_config = {"from_attributes": True}


class PluginToggle(BaseModel):
    enabled: bool


@router.get("/", response_model=list[PluginInfo])
async def list_plugins(current_user: User = Depends(get_current_user)):
    """List all registered plugins. Admin only."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso riservato agli amministratori.")
    return [
        PluginInfo(
            name=p.name,
            version=p.version,
            description=p.description,
            enabled=p.enabled,
        )
        for p in registry.list_all()
    ]


@router.patch("/{plugin_name}", response_model=PluginInfo)
async def toggle_plugin(
    plugin_name: str,
    body: PluginToggle,
    current_user: User = Depends(get_current_user),
):
    """Enable or disable a plugin at runtime. Admin only."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso riservato agli amministratori.")
    plugin = registry.get(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' non trovato.")
    plugin.enabled = body.enabled
    return PluginInfo(
        name=plugin.name,
        version=plugin.version,
        description=plugin.description,
        enabled=plugin.enabled,
    )
