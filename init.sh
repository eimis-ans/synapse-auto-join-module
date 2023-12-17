#!/bin/bash

source .env
SUB_DOMAINS=($SUB_DOMAIN_1 $SUB_DOMAIN_2)

for SUB_DOMAIN in "${SUB_DOMAINS[@]}"; do
    mkdir -p ./$SUB_DOMAIN/mx-data
    mkdir -p ./$SUB_DOMAIN/mx-conf
    cp element-config.template.json ./$SUB_DOMAIN/element-config.json
    docker run -it --rm \
        -v "./$SUB_DOMAIN/mx-data:/data" \
        -v "./$SUB_DOMAIN/mx-conf:/mx-conf" \
        -e SYNAPSE_SERVER_NAME=$SUB_DOMAIN.${DOMAIN} \
        -e SYNAPSE_CONFIG_PATH=/mx-conf/homeserver.yaml \
        -e SYNAPSE_REPORT_STATS=no \
        matrixdotorg/synapse:${SYNAPSE_VERSION} generate

    sed -i -e "s/{{ DOMAIN }}/${DOMAIN}/g" ./$SUB_DOMAIN/element-config.json
    sed -i -e "s/{{ SUB_DOMAIN }}/${SUB_DOMAIN}/g" ./$SUB_DOMAIN/element-config.json
    
    sudo chmod a+wr ./$SUB_DOMAIN/mx-conf/homeserver.yaml
    echo "
serve_server_wellknown: true
modules:
- module: broadcast_module.EimisBroadcast
  config:
    directory_url: ${DIRECTORY_URL}
" >> ./$SUB_DOMAIN/mx-conf/homeserver.yaml

done

sed -i -e "s/{{SUB_DOMAIN_1}}/${SUB_DOMAIN_1}/g" ./synapse/handlers/receipts.py
sed -i -e "s/{{SUB_DOMAIN_2}}/${SUB_DOMAIN_2}/g" ./synapse/handlers/receipts.py