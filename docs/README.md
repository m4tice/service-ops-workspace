# Workspace Documentation

These documents describe the service operations workspace and its maintainer responsibilities. The **workspace maintainer** owns orchestration and operations; each **service maintainer** owns a service repository and its features. MCP server maintainers follow the MCP-specific template contract. A contributor may fill either or both roles. The docs do not specify how service product features should be developed.

MCP clients/hosts and Git hosting are external system actors, not workspace maintainer roles. Nginx ownership is an optional infrastructure responsibility; when it belongs to a separate person or team, refer to them as the **infrastructure operator**.

- [Use Case Requirements](USE_CASE_REQUIREMENTS.md): actors, goals, workflows, and scope boundaries.
- [System and Design Requirements](SYSTEM_AND_DESIGN_REQUIREMENTS.md): workspace structure, responsibilities, operating assumptions, and design constraints.
- [Software Requirements](SOFTWARE_REQUIREMENTS.md): functional behavior and verifiable quality requirements.
- [User Guide](USER_GUIDE.md): setup and day-to-day contributor procedures.

The repository-level [README](../README.md) is the quick start. The root [CHANGELOG](../CHANGELOG.md) records workspace-level changes.

For the current implementation snapshot, operational boundaries, and handoff notes, see the root [HANDOVER](../HANDOVER.md).
