#!/bin/bash

# Кольори для краси
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}--- СТАТУС БЕЗПЕКИ NOBARA ---${NC}"

# 1. Перевірка Firewall
FW_STATUS=$(LC_ALL=C sudo ufw status | grep -o "active")
if [ "$FW_STATUS" == "active" ]; then
    echo -e "Firewall: ${GREEN}АКТИВНИЙ${NC}"
else
    echo -e "Firewall: ${RED}ВИМКНЕНИЙ${NC}"
fi

# 2. Перевірка IP та VPN (чи відрізняється від провайдера)
MY_IP=$(curl -s ifconfig.me)
echo -e "Твій поточний IP: ${BLUE}$MY_IP${NC}"

# 3. Перевірка DNS (чи використовується Cloudflare/NextDNS)
DNS_CHECK=$(nmcli dev show | grep 'IP4.DNS' | awk '{print $2}')
echo -e "Твої DNS сервери: ${BLUE}$DNS_CHECK${NC}"

echo -e "${BLUE}---------------------------${NC}"