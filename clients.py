# core/clients.py

CLIENTS = {
    "CC9999": {
        "client_id": "deb8f67a-1b19-4f97-9f71-83b125d729fc", # Key da sua lista
        "client_secret": "768bcd8d-ea07-450e-a034-ddb29c12ef7d", # Secret da sua lista
    },
    "VERO": {
        "client_id": "11a5c497-f52b-49fb-8a7b-3ae3e7716c1d",
        "client_secret": "2878db33-396e-45b0-83bd-38f946ecb277",
    },
    # Adicione os outros Client Partners aqui, seguindo o formato do PDF
    # Use as chaves (key) e segredos (secret) que você forneceu
    "TESTES_PS_FTTH": {
        "client_id": "34ae61fa-5afa-42eb-b763-b93bf2439ee0",
        "client_secret": "15d01649-3686-4f1f-a304-d68890d14144",
    },
    "TESTES_PS_FTTP": {
        "client_id": "f9a4d063-4fdf-41f9-b1d3-14914e75f46d",
        "client_secret": "093aba1e-cd5f-4ef2-9fe4-a98e47c26c37",
    },
    "TESTES_CC9999_CLARO": {
        "client_id": "2fee9892-0223-43c4-85fe-6e4675d79563",
        "client_secret": "adb2a20d-e06e-4d38-9d05-2bf8c8ee41ab",
    },
    "TESTES_VOALLE": {
        "client_id": "88eab197-1e5f-47db-9d2c-e52dc6c8e497",
        "client_secret": "4458cc78-84bf-4fef-a38c-503c61ee12f5",
    },
    "TESTES_TIM_BITSTREAM_TRG": {
        "client_id": "ef3b492b-94c3-43e4-bcd6-bc5d1b90e135",
        "client_secret": "f30957b3-e5c0-4b1b-8e6d-22a35c0ec179",
    },
    "TIM_WL": {
        "client_id": "49b5eb70-2aac-455f-a0ec-0f6c023c60b4",
        "client_secret": "00dd69e7-ed11-44ca-810e-1b1df163e658",
    },
    "TESTES_EQUATORIAL_TRG": {
        "client_id": "e160f920-e73e-419a-8330-9e5c1b4e59ea",
        "client_secret": "996ceb37-5a4a-4559-afcf-7a6555e2d3f4",
    },
    "TESTES_OI_TRG_CLIENTCO_OI": {
        "client_id": "7f4d2b66-cd0e-4bf6-85fe-46b8b16f1850",
        "client_secret": "b960960a-674d-476c-8117-742742911422",
    },
    "OI_SALESFORCE": { # Não fornecido na lista, mas no PDF
        "client_id": "OI_SALESFORCE_USERNAME", # Placeholder
        "client_secret": "OI_SALESFORCE_PASSWORD", # Placeholder
    },
    "OI_NIO": { # Não fornecido na lista, mas no PDF
        "client_id": "OI_NIO_USERNAME", # Placeholder
        "client_secret": "OI_NIO_PASSWORD", # Placeholder
    },
    "SKYFTTP_ENG_SKYBL": { # Ajustado para ser uma chave válida
        "client_id": "611b57d3-f0ad-4a7a-af3e-6ea074009aae",
        "client_secret": "57ce5e0c-4198-42eb-83a0-2406d8efae07",
    },
    "SKYFTTP_CORE": { # Ajustado para ser uma chave válida
        "client_id": "e40eff3e-0a2f-440b-a787-c18adad3209b",
        "client_secret": "5b23e210-9df1-4a72-afa3-0ddee73ff1b1",
    },
    "SKYFTTP_OTRS": { # Ajustado para ser uma chave válida
        "client_id": "fe83b040-d956-44da-a49f-f8080fa8146a",
        "client_secret": "9f148dbc-c3b5-42c4-89be-ebe70e04bf4d",
    },
    "ALGAR": {
        "client_id": "b12902ec-f59e-4405-b3f4-fbb935dd6c05",
        "client_secret": "2a9fbf54-4bc7-4aee-88b3-5019d883eef1",
    },
    "LIGGA": {
        "client_id": "058a2452-134d-4818-b30d-f2f2658fca3b",
        "client_secret": "3729e610-9223-49f6-94c5-af8ac6b36166",
    },
    # Os CPs HORIZON e MELHORPLANO têm chaves/segredos com caracteres especiais
    # que podem ser problemáticos se usados diretamente como client_id/client_secret
    # em Basic Auth sem URL encoding. Verifique como eles são tratados.
    # Por enquanto, vou deixá-los comentados ou com placeholders.
    "HORIZON": {
        "client_id": "9GzzQ3GsZMkmounDobxpNlzC0dH8sBINnvNRO1H2OwAYTwDO", # Placeholder
        "client_secret": "0tRTvbD8nRZvSpvJ5eu9uJbh1mGodoA6p8zfuO9Dz0wNg6cqfRpf352mRKsknmGY", # Placeholder
    },
    "MELHORPLANO": {
        "client_id": "srFkAfi2FfKkmXBg7CHB1A7NLqpJe546QhqDdQRUobnCVdUS", # Placeholder
        "client_secret": "yPUNpOOn4XHEZcvysxIVPju6MssvD3P5Azjr5DHiXGGNzC7DnJaaNxFksnKXUFK7", # Placeholder
    },
}