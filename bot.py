import requests
import time
import docker
from datetime import datetime
from colorama import init, Fore, Style
from shareithub import HTTPTools, ASCIITools

ASCIITools.print_ascii_intro()

init(autoreset=True)

client = docker.from_env()

def read_proxies_from_file():
    proxies = []
    try:
        with open('proxy.txt', 'r') as file:
            proxies = file.read().splitlines()
        return proxies
    except Exception as e:
        log_error(f"Terjadi kesalahan saat membaca proxy: {e}")
        return []

def choose_proxy(proxies):
    if not proxies:
        log_warning("Tidak ada proxy yang tersedia.")
        return None

    log_info("Pilih proxy yang ingin digunakan:")
    for i, proxy in enumerate(proxies, 1):
        print(f"{i}. {proxy}")
    print(f"{len(proxies) + 1}. Tidak menggunakan proxy")

    choice = int(input("\nMasukkan nomor pilihan: "))
    if 1 <= choice <= len(proxies):
        selected_proxy = proxies[choice - 1]
        log_info(f"Proxy yang dipilih: {selected_proxy}")
        return {
            "http": f"http://{selected_proxy}",
            "https": f"https://{selected_proxy}"
        }
    else:
        log_info("Tidak menggunakan proxy.")
        return None

def read_token_from_file():
    try:
        with open('token.txt', 'r') as file:
            token = file.read().strip()
            return token
    except Exception as e:
        log_error(f"Terjadi kesalahan saat membaca token: {e}")
        return None

def log_info(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.GREEN}[INFO] {timestamp} - {message}")

def log_warning(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.YELLOW}[WARNING] {timestamp} - {message}")

# Fungsi untuk mencetak log error dengan timestamp dan warna
def log_error(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.RED}[ERROR] {timestamp} - {message}")

# Fungsi untuk mengambil data gas fee dari API
def fetch_gas_fee(proxies=None):
    url = "https://api.vanascan.io/api/v2/stats"
    try:
        response = requests.get(url, proxies=proxies)
        if response.status_code == 200:
            return response.json()  # Parse respons JSON
        elif response.status_code == 403:
            log_warning("Gagal mengambil data: 403. Akan mencoba ulang dengan proxy.")
            # Ulangi permintaan dengan proxy
            if proxies:
                response_with_proxy = requests.get(url, proxies=proxies)
                if response_with_proxy.status_code == 200:
                    return response_with_proxy.json()  # Berhasil dengan proxy
                else:
                    log_error(f"Gagal mengambil data dengan proxy: {response_with_proxy.status_code}")
            return None
        else:
            log_error(f"Gagal mengambil data: {response.status_code}")
            return None
    except Exception as e:
        log_error(f"Terjadi kesalahan: {e}")
        return None

def fetch_volara_stats(token, proxies=None):
    url = "https://api.volara.xyz/v1/user/stats"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(url, headers=headers, proxies=proxies)
        if response.status_code == 200:
            return response.json()  
        else:
            log_error(f"Gagal mengambil data Volara: {response.status_code}")
            return None
    except Exception as e:
        log_error(f"Terjadi kesalahan saat mengambil data Volara: {e}")
        return None

def list_running_containers():
    try:
        containers = client.containers.list()  
        if not containers:
            log_warning("Tidak ada container yang berjalan saat ini.")
            return None

        log_info("Daftar container yang berjalan:")
        for idx, container in enumerate(containers, start=1):
            print(f"{idx}. {container.name} (Image: {container.image.tags[0] if container.image.tags else 'No image'})")
        
        choice = int(input("\nPilih nomor container yang ingin dimonitor: "))
        if choice < 1 or choice > len(containers):
            log_error("Pilihan tidak valid.")
            return None
        
        selected_container = containers[choice - 1]
        log_info(f"Anda memilih container: {selected_container.name}")
        return selected_container
    except Exception as e:
        log_error(f"Terjadi kesalahan: {e}")
        return None

def pause_container(container):
    try:
        log_info(f"Menjeda container: {container.name}")
        container.pause()
        log_info(f"Container {container.name} telah dijeda.")
    except Exception as e:
        log_error(f"Terjadi kesalahan saat menjeda container: {e}")

def unpause_container(container):
    try:
        log_info(f"Melanjutkan container: {container.name}")
        container.unpause()
        log_info(f"Container {container.name} telah dilanjutkan.")
    except Exception as e:
        log_error(f"Terjadi kesalahan saat melanjutkan container: {e}")


def monitor_gas_fee_and_manage_docker(container, token, proxies=None):
    container_paused = False 

    while True:

        data = fetch_gas_fee(proxies)


        volara_data = fetch_volara_stats(token, proxies)

        if data:
            log_info("Gas Fee Tracker:")
            
            if 'gas_prices' in data:
                average_gas = data['gas_prices'].get('average', None)
                
                if average_gas is not None:
                    log_info(f"Gas Fee Average: {average_gas}")

                    if average_gas > 0.3:
                        if not container_paused:
                            log_warning("Gas fee tinggi! Menjeda container.")
                            pause_container(container)
                            container_paused = True  
                        else:
                            log_info("Gas fee masih tinggi. Tidak ada tindakan tambahan.")
                    elif average_gas < 0.2:
                        if container_paused:
                            log_info("Gas fee rendah. Melanjutkan container.")
                            unpause_container(container)
                            container_paused = False
                        else:
                            log_info("Gas fee masih rendah. Tidak ada tindakan tambahan.")
                    else:
                        log_info("Gas fee normal. Tidak ada perubahan pada container.")
                else:
                    log_warning("Data gas fee average tidak ditemukan.")
            else:
                log_warning("Data gas_prices tidak ditemukan dalam respons.")
        else:
            log_warning("Tidak dapat mengambil data gas fee.")


        if volara_data and volara_data.get("success"):
            log_info("\nVolara Stats:")
            index_stats = volara_data.get('data', {}).get('indexStats', {})
            reward_stats = volara_data.get('data', {}).get('rewardStats', {})
            rank_stats = volara_data.get('data', {}).get('rankStats', {})

            total_indexed_tweets = index_stats.get("totalIndexedTweets", "Tidak tersedia")
            vortex_score = reward_stats.get("vortexScore", "Tidak tersedia")
            vortex_rank = rank_stats.get("vortexRank", "Tidak tersedia")

            log_info(f"Total Indexed Tweets: {total_indexed_tweets}")
            log_info(f"Vortex Score: {vortex_score}")
            log_info(f"Vortex Rank: {vortex_rank}")
        else:
            log_warning("Tidak dapat mengambil data Volara atau respons tidak berhasil.")

        time.sleep(60) 


def main():

    token = read_token_from_file()
    if not token:
        log_error("Token tidak ditemukan. Program dihentikan.")
        return


    proxies = read_proxies_from_file()


    proxy_settings = choose_proxy(proxies)

    container = list_running_containers()
    if container:
        log_info(f"Memulai monitoring untuk container {container.name}...")
        monitor_gas_fee_and_manage_docker(container, token, proxy_settings)

if __name__ == "__main__":
    main()
