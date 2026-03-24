#!/usr/bin/env python3
"""
Prova Técnica - Processamento de Municípios IBGE
Autor: Gabriel Laskos
"""

import csv
import json
import requests
import unicodedata
import os
from collections import defaultdict

# Diretório do script
SCRIPT_DIR = "/vercel/share/v0-project/scripts"

# Configurações do Supabase
SUPABASE_URL = "https://mynxlubykylncinttggu.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15bnhsdWJ5a3lsbmNpbnR0Z2d1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUxODg2NzAsImV4cCI6MjA4MDc2NDY3MH0.Z-zqiD6_tjnF2WLU167z7jT5NzZaG72dWH0dpQW1N-Y"
SUBMIT_URL = "https://mynxlubykylncinttggu.functions.supabase.co/ibge-submit"

# Credenciais serão solicitadas ao usuário

# Dados do input.csv embutidos diretamente
INPUT_DATA = [
    {"municipio": "Niteroi", "populacao": 515317},
    {"municipio": "Sao Gonçalo", "populacao": 1091737},
    {"municipio": "Sao Paulo", "populacao": 12396372},
    {"municipio": "Belo Horzionte", "populacao": 2530701},
    {"municipio": "Florianopolis", "populacao": 516524},
    {"municipio": "Santo Andre", "populacao": 723889},
    {"municipio": "Santoo Andre", "populacao": 700000},
    {"municipio": "Rio de Janeiro", "populacao": 6718903},
    {"municipio": "Curitba", "populacao": 1963726},
    {"municipio": "Brasilia", "populacao": 3094325},
]


def normalize_string(s: str) -> str:
    """
    Normaliza uma string removendo acentos e convertendo para minúsculas.
    Útil para comparação fuzzy de nomes de municípios.
    """
    if not s:
        return ""
    # Remove acentos
    nfkd = unicodedata.normalize('NFKD', s)
    without_accents = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Converte para minúsculas e remove espaços extras
    return without_accents.lower().strip()


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calcula a distância de Levenshtein entre duas strings.
    Usado para encontrar municípios com erros de digitação.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def login_supabase(email: str, password: str) -> str:
    """
    Faz login no Supabase e retorna o access_token.
    """
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY
    }
    data = {
        "email": email,
        "password": password
    }
    
    print(f"Fazendo login com o email: {email}")
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        access_token = result.get("access_token")
        user_email = result.get("user", {}).get("email", "")
        print(f"Login realizado com sucesso! Email: {user_email}")
        return access_token
    else:
        print(f"Erro no login: {response.status_code}")
        print(response.text)
        raise Exception("Falha no login")


def get_ibge_municipios() -> list:
    """
    Busca todos os municípios da API do IBGE.
    Retorna uma lista com informações completas de cada município.
    """
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    print("Buscando municípios da API do IBGE...")
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            municipios = response.json()
            print(f"Total de municípios obtidos do IBGE: {len(municipios)}")
            return municipios
        else:
            print(f"Erro ao buscar municípios: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão com a API do IBGE: {e}")
        return []


def build_municipio_index(municipios: list) -> dict:
    """
    Constrói um índice de municípios para busca rápida.
    O índice mapeia nomes normalizados para dados do município.
    """
    index = {}
    for m in municipios:
        try:
            nome = m.get("nome", "")
            nome_normalizado = normalize_string(nome)
            
            # Tentar diferentes estruturas da API do IBGE
            # Estrutura nova: municipio > microrregiao > mesorregiao > UF > regiao
            # Estrutura alternativa: municipio > regiao-imediata > regiao-intermediaria > UF > regiao
            
            uf_sigla = ""
            regiao_nome = ""
            
            # Tenta estrutura com microrregiao
            if "microrregiao" in m and m["microrregiao"]:
                mesorregiao = m["microrregiao"].get("mesorregiao", {}) or {}
                uf = mesorregiao.get("UF", {}) or {}
                uf_sigla = uf.get("sigla", "")
                regiao = uf.get("regiao", {}) or {}
                regiao_nome = regiao.get("nome", "")
            
            # Tenta estrutura com regiao-imediata
            elif "regiao-imediata" in m and m["regiao-imediata"]:
                regiao_inter = m["regiao-imediata"].get("regiao-intermediaria", {}) or {}
                uf = regiao_inter.get("UF", {}) or {}
                uf_sigla = uf.get("sigla", "")
                regiao = uf.get("regiao", {}) or {}
                regiao_nome = regiao.get("nome", "")
            
            info = {
                "nome": nome,
                "uf": uf_sigla,
                "regiao": regiao_nome,
                "id": m.get("id", "")
            }
            
            index[nome_normalizado] = info
        except Exception as e:
            print(f"Erro ao processar município: {m.get('nome', 'desconhecido')} - {e}")
            continue
    
    return index


def has_repeated_chars_error(input_str: str, expected_str: str) -> bool:
    """
    Verifica se o input tem um erro de caractere repetido que não existe no esperado.
    Ex: "Santoo" tem "oo" mas "Santo" não tem.
    """
    # Encontra sequências de caracteres repetidos no input
    i = 0
    while i < len(input_str) - 1:
        if input_str[i] == input_str[i + 1]:
            # Encontrou uma repetição
            char = input_str[i]
            count_input = 0
            j = i
            while j < len(input_str) and input_str[j] == char:
                count_input += 1
                j += 1
            
            # Conta quantas vezes esse caractere aparece consecutivamente no esperado
            # na mesma posição relativa
            count_expected = 0
            # Procura no esperado por essa mesma sequência
            for k in range(len(expected_str) - 1):
                if expected_str[k] == char:
                    temp_count = 0
                    m = k
                    while m < len(expected_str) and expected_str[m] == char:
                        temp_count += 1
                        m += 1
                    count_expected = max(count_expected, temp_count)
            
            if count_input > count_expected:
                return True
            i = j
        else:
            i += 1
    return False


def find_municipio(nome_input: str, index: dict, all_normalized_names: list) -> tuple:
    """
    Encontra o município correspondente no índice do IBGE.
    Usa matching exato primeiro, depois fuzzy matching com Levenshtein.
    
    Retorna: (dados_municipio, status)
    """
    nome_normalizado = normalize_string(nome_input)
    
    # Matching exato
    if nome_normalizado in index:
        return index[nome_normalizado], "OK"
    
    # Fuzzy matching usando distância de Levenshtein
    best_match = None
    best_distance = float('inf')
    
    for nome_ibge in all_normalized_names:
        distance = levenshtein_distance(nome_normalizado, nome_ibge)
        
        if distance < best_distance:
            best_distance = distance
            best_match = nome_ibge
    
    # Aceita distância até 2, mas verifica se não é erro de caractere repetido
    if best_distance <= 2 and best_match:
        # Verifica se o erro é uma letra duplicada indevidamente
        if has_repeated_chars_error(nome_normalizado, best_match):
            return None, "NAO_ENCONTRADO"
        return index[best_match], "OK"
    
    return None, "NAO_ENCONTRADO"


def read_input_csv(filepath: str) -> list:
    """
    Lê o arquivo input.csv e retorna uma lista de dicionários.
    """
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                "municipio": row["municipio"],
                "populacao": int(row["populacao"])
            })
    print(f"Lidos {len(data)} municípios do input.csv")
    return data


def process_municipios(input_data: list, ibge_municipios: list) -> list:
    """
    Processa cada município do input, enriquecendo com dados do IBGE.
    """
    results = []
    
    if not ibge_municipios:
        # Se não conseguiu obter dados do IBGE, marca tudo como ERRO_API
        for item in input_data:
            results.append({
                "municipio_input": item["municipio"],
                "populacao_input": item["populacao"],
                "municipio_ibge": "",
                "uf": "",
                "regiao": "",
                "id_ibge": "",
                "status": "ERRO_API"
            })
        return results
    
    # Constrói índice para busca eficiente
    index = build_municipio_index(ibge_municipios)
    all_names = list(index.keys())
    
    for item in input_data:
        municipio_input = item["municipio"]
        populacao = item["populacao"]
        
        ibge_data, status = find_municipio(municipio_input, index, all_names)
        
        if ibge_data:
            results.append({
                "municipio_input": municipio_input,
                "populacao_input": populacao,
                "municipio_ibge": ibge_data["nome"],
                "uf": ibge_data["uf"],
                "regiao": ibge_data["regiao"],
                "id_ibge": ibge_data["id"],
                "status": status
            })
        else:
            results.append({
                "municipio_input": municipio_input,
                "populacao_input": populacao,
                "municipio_ibge": "",
                "uf": "",
                "regiao": "",
                "id_ibge": "",
                "status": status
            })
        
        print(f"  {municipio_input} -> {results[-1]['municipio_ibge'] or 'N/A'} ({status})")
    
    return results


def write_resultado_csv(results: list, filepath: str):
    """
    Escreve o arquivo resultado.csv.
    """
    fieldnames = ["municipio_input", "populacao_input", "municipio_ibge", "uf", "regiao", "id_ibge", "status"]
    
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Arquivo resultado.csv gerado com {len(results)} registros")


def calculate_statistics(results: list) -> dict:
    """
    Calcula as estatísticas exigidas pela prova.
    """
    total_municipios = len(results)
    total_ok = sum(1 for r in results if r["status"] == "OK")
    total_nao_encontrado = sum(1 for r in results if r["status"] == "NAO_ENCONTRADO")
    total_erro_api = sum(1 for r in results if r["status"] == "ERRO_API")
    
    # População total dos municípios com status OK
    pop_total_ok = sum(r["populacao_input"] for r in results if r["status"] == "OK")
    
    # Médias por região (apenas status OK)
    pop_por_regiao = defaultdict(list)
    for r in results:
        if r["status"] == "OK" and r["regiao"]:
            pop_por_regiao[r["regiao"]].append(r["populacao_input"])
    
    medias_por_regiao = {}
    for regiao, populacoes in pop_por_regiao.items():
        media = sum(populacoes) / len(populacoes)
        medias_por_regiao[regiao] = round(media, 2)
    
    stats = {
        "total_municipios": total_municipios,
        "total_ok": total_ok,
        "total_nao_encontrado": total_nao_encontrado,
        "total_erro_api": total_erro_api,
        "pop_total_ok": pop_total_ok,
        "medias_por_regiao": medias_por_regiao
    }
    
    return stats


def submit_results(access_token: str, stats: dict):
    """
    Envia os resultados para a API de correção.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {"stats": stats}
    
    print("\nEnviando resultados para a API de correção...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(SUBMIT_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("\n" + "="*50)
            print("RESULTADO DA CORREÇÃO")
            print("="*50)
            print(f"Email: {result.get('email', 'N/A')}")
            print(f"Score: {result.get('score', 'N/A')}")
            print(f"Feedback: {result.get('feedback', 'N/A')}")
            if 'components' in result:
                print(f"Componentes: {json.dumps(result['components'], indent=2)}")
            print("="*50)
            return result
        else:
            print(f"Erro ao submeter resultados: {response.status_code}")
            print(response.text)
            return None
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão ao submeter resultados: {e}")
        return None


def main():
    """
    Função principal que orquestra todo o processo.
    """
    print("="*50)
    print("PROVA TÉCNICA - PROCESSAMENTO DE MUNICÍPIOS IBGE")
    print("="*50)
    
    # 0. Solicitar credenciais
    print("\nPor favor, insira suas credenciais:")
    email = input("Email: ").strip()
    password = input("Senha: ").strip()
    
    # 1. Login no Supabase
    print("\n[1/6] Fazendo login no Supabase...")
    access_token = login_supabase(email, password)
    
    # 2. Usar dados do input
    print("\n[2/6] Carregando dados de entrada...")
    input_data = INPUT_DATA
    print(f"Carregados {len(input_data)} municípios")
    
    # 3. Buscar dados do IBGE
    print("\n[3/6] Buscando dados da API do IBGE...")
    ibge_municipios = get_ibge_municipios()
    
    # 4. Processar municípios
    print("\n[4/6] Processando municípios...")
    results = process_municipios(input_data, ibge_municipios)
    
    # 5. Mostrar resultados (sem salvar em arquivo)
    print("\n[5/6] Resultados processados:")
    for r in results:
        print(f"  {r['municipio_input']} -> {r['municipio_ibge']} ({r['uf']}, {r['regiao']}) - {r['status']}")
    
    # 6. Calcular estatísticas
    print("\n[6/6] Calculando estatísticas...")
    stats = calculate_statistics(results)
    
    print("\nEstatísticas calculadas:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 7. Enviar para API de correção
    submit_results(access_token, stats)
    
    print("\nProcessamento concluído!")


if __name__ == "__main__":
    main()
