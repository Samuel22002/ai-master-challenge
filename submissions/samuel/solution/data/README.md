# Dados — RavenStack (não incluídos)

Os cinco CSVs **não** são enviados nesta submissão. Eles são o dataset público do challenge, "SaaS Subscription & Churn Analytics", disponível no Kaggle sob licença MIT:
https://www.kaggle.com/datasets/rivalytics/saas-subscription-and-churn-analytics-dataset

Para reproduzir:

1. Baixe os 5 arquivos `ravenstack_*.csv`.
2. Coloque-os em `solution/data/ravenstack/`, ou aponte a variável de ambiente `RAVENSTACK_DATA` para a pasta onde estão.
3. Confira que são os mesmos arquivos usados na análise:

```bash
cd solution/data/ravenstack && sha256sum -c ../SHA256SUMS.txt
```

No Windows (PowerShell), compare com `Get-FileHash <arquivo> -Algorithm SHA256`.

`SHA256SUMS.txt` lista o hash SHA-256 de cada arquivo.

O Truth Lab e os outputs validados em `solution/outputs/` **não** precisam dos CSVs: só a reexecução dos scripts precisa.
