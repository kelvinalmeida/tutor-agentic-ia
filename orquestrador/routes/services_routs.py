import os


def _running_in_docker() -> bool:
    return os.path.exists('/.dockerenv')


def _service_url(env_name: str, docker_default: str, local_default: str) -> str:
    # Permite sobrescrever por variável de ambiente quando necessário
    configured = os.getenv(env_name)
    if configured:
        return configured.rstrip('/')

    default_url = docker_default if _running_in_docker() else local_default
    return default_url.rstrip('/')


USER_URL = _service_url('USER_URL', 'http://user:5002', 'http://localhost:5002')
CONTROL_URL = _service_url('CONTROL_URL', 'http://agente_sessao:5001', 'http://localhost:5001')
STRATEGIES_URL = _service_url('STRATEGIES_URL', 'http://strategies:5003', 'http://localhost:5003')
DOMAIN_URL = _service_url('DOMAIN_URL', 'http://domain:5004', 'http://localhost:5004')
