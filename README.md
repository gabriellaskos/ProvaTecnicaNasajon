
# Prova Técnica - Enriquecimento de Dados com IBGE

## Objetivo

Script Python que enriquece dados de municípios brasileiros usando a API do IBGE, com correção de erros de digitação via fuzzy matching.

## O que faz

1. **Login** no Supabase para obter token de autenticação
2. **Leitura** dos municípios do input (nome + população)
3. **Busca na API do IBGE** para obter UF e região de cada município
4. **Fuzzy matching** com distância de Levenshtein para corrigir erros de digitação
5. **Cálculo de estatísticas**: totais, população e médias por região
6. **Envio** dos resultados para a API de correção

## Fuzzy Matching

- Corrige erros como "Belo Horzionte" → "Belo Horizonte"
- Rejeita erros de caracteres duplicados como "Santoo Andre"
- Usa distância de Levenshtein com threshold de 2

## Execução

```bash
#certifique que o arquivo import.csv esteja na mesma pasta que o código!

# Entre na pasta dos scripts
cd scripts

# Execute o desafio
python prova_tecnica.py

# Coloque suas credenciais

```

## Resultado

Score: **10/10**
