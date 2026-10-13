#!/usr/bin/env bash

set -euo pipefail

run_privileged() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

if [[ "$(uname -s)" != "Linux" ]] || [[ ! -r /etc/os-release ]]; then
  echo "Este script solo es compatible con Ubuntu Linux." >&2
  exit 1
fi

. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "Sistema operativo no compatible: ${PRETTY_NAME:-desconocido}. Se requiere Ubuntu." >&2
  exit 1
fi

if [[ "${EUID}" -ne 0 ]] && ! command -v sudo >/dev/null 2>&1; then
  echo "Se requiere sudo si el script no se ejecuta como root." >&2
  exit 1
fi

echo "Instalando Docker Engine, Compose v2 y UFW..."
run_privileged apt-get update
run_privileged apt-get install -y ca-certificates curl git docker.io docker-compose-v2 ufw
run_privileged systemctl enable --now docker

target_user="${SUDO_USER:-${USER:-}}"
if [[ -n "${target_user}" ]] && [[ "${target_user}" != "root" ]]; then
  run_privileged usermod -aG docker "${target_user}"
  echo "Se agregó ${target_user} al grupo docker; inicia una nueva sesión para aplicar el cambio."
fi

ssh_port="${SSH_PORT:-22}"
if [[ -n "${SSH_CONNECTION:-}" ]]; then
  read -r _ _ _ ssh_port <<< "${SSH_CONNECTION}"
elif command -v sshd >/dev/null 2>&1; then
  configured_ssh_port="$(run_privileged sshd -T | awk '$1 == "port" { print $2; exit }')"
  if [[ -n "${configured_ssh_port}" ]]; then
    ssh_port="${configured_ssh_port}"
  fi
fi

if [[ ! "${ssh_port}" =~ ^[0-9]+$ ]] || (( ssh_port < 1 || ssh_port > 65535 )); then
  echo "Puerto SSH no válido: ${ssh_port}" >&2
  exit 1
fi

run_privileged ufw allow "${ssh_port}/tcp"
run_privileged ufw allow 443/tcp
if ! run_privileged ufw status | grep -q "Status: active"; then
  run_privileged ufw --force enable
fi

echo "Aprovisionamiento completado. El Gateway solo escucha en loopback; usa un túnel SSH o configura un proxy TLS."
echo "Las reglas de entrada de Oracle Cloud se gestionan aparte en la lista de seguridad o el grupo de red del VCN."
