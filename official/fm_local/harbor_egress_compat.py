"""Keep APEX's port-bearing world service on its declared public network.

Harbor routes eligible Docker Compose services through its egress sidecar by
setting ``network_mode: service:<sidecar>``. Docker rejects that combination
for services whose images or Compose config expose ports. The task-agent
``main`` service remains on the relay-only sidecar; auxiliary task services
retain their declared Compose networking.
"""

from __future__ import annotations

from functools import wraps
from pathlib import Path

import yaml


def install() -> None:
    from harbor.environments.docker.docker import DockerEnvironment

    original = DockerEnvironment._egress_controlled_service_names
    if getattr(original, "_fm_c2_port_compat", False):
        return

    @wraps(original)
    def egress_controlled_service_names(self):
        names = original(self)
        network_mode = getattr(self.network_policy.network_mode, "value", None)
        if (
            self.environment_name != "apex-eurogrid-curtailment"
            or not self.session_id.endswith("__env")
            or network_mode != "public"
        ):
            return names

        task_services: set[str] = set()
        for compose_path in self._user_compose_paths():
            document = yaml.safe_load(Path(compose_path).read_text())
            services = document.get("services") if isinstance(document, dict) else None
            if not isinstance(services, dict):
                continue
            for name, config in services.items():
                if not isinstance(name, str) or not isinstance(config, dict):
                    continue
                if config.get("expose") or config.get("ports"):
                    task_services.add(name)
        return [name for name in names if name == "main" or name not in task_services]

    egress_controlled_service_names._fm_c2_port_compat = True
    DockerEnvironment._egress_controlled_service_names = egress_controlled_service_names
