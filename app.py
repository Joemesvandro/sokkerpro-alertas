import pandas as pd
import requests
import time
from playwright.sync_api import sync_playwright
from datetime import datetime
import os
import re

# === CONFIGURAÇÕES TELEGRAM ===
TELEGRAM_TOKEN = "7028700069:AAGKGhCAkN96_BkAf9Nwu08kfpkpMoXn7gA"
CHAT_ID = "-1002050829155"

CSV_TEMP = "estatisticas_live_games_temp.csv"
CSV_LIMPO = "estatisticas_live_games_limpo.csv"
CSV_ENVIADOS = "partidas_enviadas.csv"

def enviar_telegram(mensagem, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("📤 Mensagem enviada ao Telegram!")
    else:
        print("❌ Erro ao enviar:", response.text)

def limpar_dados_csv(csv_sujo, csv_limpo):
    if not os.path.exists(csv_sujo):
        return
    df = pd.read_csv(csv_sujo, encoding="utf-8-sig")
    def extrair_int_dupla(val):
        try:
            return list(map(int, re.findall(r'\d+', str(val))))[:2]
        except:
            return [0, 0]
    def extrair_float_dupla(val):
        try:
            return list(map(float, re.findall(r'[\d.]+', str(val))))[:2]
        except:
            return [0.0, 0.0]
    df["Mandante"] = df["Mandante"].astype(str).str.strip()
    df["Visitante"] = df["Visitante"].astype(str).str.strip()
    df["Tempo"] = df["Tempo"].astype(str).str.extract(r'(\d+)').astype(float).fillna(0).astype(int)
    gols = df["Placar"].apply(extrair_int_dupla)
    df["Gols_Mandante"] = gols.apply(lambda x: x[0])
    df["Gols_Visitante"] = gols.apply(lambda x: x[1])
    corners = df["Corners"].apply(extrair_int_dupla)
    df["Escanteios_Mandante"] = corners.apply(lambda x: x[0])
    df["Escanteios_Visitante"] = corners.apply(lambda x: x[1])
    dapm = df["Da.p.m"].apply(extrair_float_dupla)
    df["DaPM_Mandante"] = dapm.apply(lambda x: x[0] if len(x) > 0 else 0.0)
    df["DaPM_Visitante"] = dapm.apply(lambda x: x[1] if len(x) > 1 else 0.0)
    finalizacoes = df["Shots on"].apply(extrair_int_dupla)
    df["Final_Mandante"] = finalizacoes.apply(lambda x: x[0])
    df["Final_Visitante"] = finalizacoes.apply(lambda x: x[1])
    colunas_finais = [
        "Mandante", "Visitante", "Tempo", "Gols_Mandante", "Gols_Visitante",
        "Escanteios_Mandante", "Escanteios_Visitante", "DaPM_Mandante", "DaPM_Visitante",
        "Final_Mandante", "Final_Visitante"
    ]
    df[colunas_finais].to_csv(csv_limpo, index=False, encoding="utf-8-sig")
    os.remove(csv_sujo)
    print("🧼 CSV sujo limpo e salvo como versão final:", csv_limpo)

def coletar_dados():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://sokkerpro.com/", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        botoes_menu = page.query_selector_all("div.totalmenuLine > div")
        for botao in botoes_menu:
            if "LIVE GAMES" in botao.inner_text().strip().upper():
                botao.evaluate("e => e.click()")
                break
        page.wait_for_timeout(8000)
        partidas = page.query_selector_all("div.match.live")
        print(f"🎯 [{datetime.now().strftime('%H:%M:%S')}] Partidas encontradas: {len(partidas)}")
        dados = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for partida in partidas:
            try:
                nomes = partida.query_selector_all("div.teamname")
                equipe_mandante = nomes[0].inner_text().strip() if len(nomes) > 0 else "N/A"
                equipe_visitante = nomes[1].inner_text().strip() if len(nomes) > 1 else "N/A"
                tempo = "N/A"
                for div in partida.query_selector_all("div"):
                    texto = div.inner_text().strip()
                    if "'" in texto and len(texto) <= 6:
                        tempo = texto
                        break
                placar_elem = partida.query_selector("div.score")
                placar = placar_elem.inner_text().strip() if placar_elem else "N/A"
                estatisticas = partida.query_selector_all("div.stats-container div.hidable")
                estat_map = [e.inner_text().strip() for e in estatisticas]
                dados.append({
                    "Timestamp": timestamp,
                    "Mandante": equipe_mandante,
                    "Visitante": equipe_visitante,
                    "Tempo": tempo,
                    "Placar": placar,
                    "Corners": estat_map[0] if len(estat_map) > 0 else "N/A",
                    "Ball %": estat_map[1] if len(estat_map) > 1 else "N/A",
                    "D. Attacks": estat_map[2] if len(estat_map) > 2 else "N/A",
                    "Da.p.m": estat_map[3] if len(estat_map) > 3 else "N/A",
                    "Shots on": estat_map[4] if len(estat_map) > 4 else "N/A",
                })
            except Exception as e:
                print("⚠️ Erro ao processar partida:", e)
        df = pd.DataFrame(dados)
        if not df.empty:
            df.to_csv(CSV_TEMP, index=False, encoding="utf-8-sig")
            limpar_dados_csv(CSV_TEMP, CSV_LIMPO)
        else:
            print("⚠️ Nenhum dado coletado nesta rodada.")
        browser.close()

def analisar_e_enviar():
    if not os.path.exists(CSV_LIMPO):
        print("⚠️ Arquivo CSV limpo ainda não existe.")
        return
    df = pd.read_csv(CSV_LIMPO, encoding="utf-8-sig")
    if os.path.exists(CSV_ENVIADOS):
        enviados_df = pd.read_csv(CSV_ENVIADOS, encoding="utf-8-sig")
        mandantes_datas_enviadas = set(zip(enviados_df["Mandante"].astype(str), enviados_df["Data"].str[:10]))
    else:
        enviados_df = pd.DataFrame()
        mandantes_datas_enviadas = set()
    df = df[((df["Tempo"] >= 25) & (df["Tempo"] <= 30)) | ((df["Tempo"] >= 75) & (df["Tempo"] <= 80))]
    candidatos = []
    for _, row in df.iterrows():
        hoje = datetime.now().strftime("%Y-%m-%d")
        chave = (row["Mandante"].strip(), hoje)
        if chave in mandantes_datas_enviadas:
            continue
        gols_mandante = row["Gols_Mandante"]
        gols_visitante = row["Gols_Visitante"]
        dapm_mandante = row["DaPM_Mandante"]
        dapm_visitante = row["DaPM_Visitante"]
        if gols_mandante == gols_visitante:
            if dapm_mandante > 0.9 or dapm_visitante > 0.9:
                candidatos.append((row, chave))
        elif abs(gols_mandante - gols_visitante) == 1:
            if gols_mandante < gols_visitante and dapm_mandante > 0.9 and dapm_mandante > dapm_visitante:
                candidatos.append((row, chave))
            elif gols_visitante < gols_mandante and dapm_visitante > 0.9 and dapm_visitante > dapm_mandante:
                candidatos.append((row, chave))
    if candidatos:
        mensagem = ""
        novos_alertas = []
        for row, chave in candidatos:
            mensagem += (
                "🚨 ALERTA ESCANTEIOS - PRESSÃO

"
                f"📈 Placar: {row['Gols_Mandante']} - {row['Gols_Visitante']}
"
                f"⚽ {row['Mandante']} x {row['Visitante']} ({row['Tempo']}' min)
"
                f"📊 DaPM: {row['DaPM_Mandante']:.2f} - {row['DaPM_Visitante']:.2f}
"
                f"📈 Escanteios: {row['Escanteios_Mandante']} - {row['Escanteios_Visitante']}
"
                f"🥅 Finalizações: {row['Final_Mandante']} - {row['Final_Visitante']}

"
            )
            novos_alertas.append({
                "ID_Partida": f"{row['Mandante'].strip()}_{row['Visitante'].strip()}_{row['Tempo']}",
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Mandante": row["Mandante"],
                "Visitante": row["Visitante"],
                "Tempo": row["Tempo"],
                "Gols_Mandante": row["Gols_Mandante"],
                "Gols_Visitante": row["Gols_Visitante"],
                "Escanteios_Mandante": row["Escanteios_Mandante"],
                "Escanteios_Visitante": row["Escanteios_Visitante"],
                "DaPM_Mandante": row["DaPM_Mandante"],
                "DaPM_Visitante": row["DaPM_Visitante"],
                "Final_Mandante": row["Final_Mandante"],
                "Final_Visitante": row["Final_Visitante"],
            })
        enviar_telegram(mensagem, TELEGRAM_TOKEN, CHAT_ID)
        df_novos = pd.DataFrame(novos_alertas)
        if os.path.exists(CSV_ENVIADOS):
            df_novos.to_csv(CSV_ENVIADOS, mode='a', header=False, index=False, encoding="utf-8-sig")
        else:
            df_novos.to_csv(CSV_ENVIADOS, index=False, encoding="utf-8-sig")
        print(f"📍 {len(df_novos)} alerta(s) registrado(s).")
    else:
        print("🟡 Nenhuma partida com pressão suficiente para alerta.")

print("🚀 Coleta + análise + alerta rodando...
")
try:
    while True:
        agora = datetime.now()
        if 8 <= agora.hour <= 20:
            coletar_dados()
            analisar_e_enviar()
        else:
            print(f"🕗 Horário fora do intervalo 08:00-20:00: {agora.strftime('%H:%M:%S')}. Aguardando...")
        time.sleep(300)
except KeyboardInterrupt:
    print("🛑 Execução encerrada pelo usuário.")
