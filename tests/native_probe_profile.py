"""Overrides for owned synthetic tool probes, never owner configuration."""
import os
from pathlib import Path


def isolated_overrides():
    # Reviewed native catalog: tool_mode=code_mode_only. Its executor is
    # necessary to reach dynamic tools, even though shell/MCP stay disabled.
    result={k:False for k in ('features.shell_tool','features.unified_exec','features.web_search',
        'features.apps','features.plugins','features.multi_agent','features.goals','features.memories',
        'features.node_repl','tools.view_image')}
    result.update({'features.code_mode':True,'features.code_mode_host':True,'web_search':'disabled'})
    config=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'config.toml'
    if config.exists():
        # Lazy import avoids a Client/config-helper cycle in standalone probes.
        from tests.run_policy_trials import mcp_overrides
        result.update(mcp_overrides(config.read_text(encoding='utf-8-sig')))
    return result
