import cloudscraper
import time
import docker
from datetime import datetime
from colorama import init, Fore, Style
from shareithub import shareithub

init(autoreset=True)

client = docker.from_env()

# Fungsi untuk membaca token dari file
def read_token_from_file():
    try:
        with open('token.txt', 'r') as file:
            token = file.read().strip()
            return token
    except Exception as e:
        log_error(f"Terjadi kesalahan saat membaca token: {e}")
        return None

# Fungsi untuk log info
def log_info(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.GREEN}[INFO] {timestamp} - {message}")

# Fungsi untuk log warning
def log_warning(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.YELLOW}[WARNING] {timestamp} - {message}")

# Fungsi untuk log error
def log_error(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{Fore.RED}[ERROR] {timestamp} - {message}")

# Fungsi untuk mengambil data gas fee dengan cloudscraper
def fetch_gas_fee():
    url = "https://api.vanascan.io/api/v2/stats"
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url)

        if response.status_code == 200:
            return response.json()  # Parse respons JSON
        elif response.status_code == 403:
            log_warning("Gagal mengambil data: 403.")
            return None
        else:
            log_error(f"Gagal mengambil data: {response.status_code}")
            return None
    except Exception as e:
        log_error(f"Terjadi kesalahan: {e}")
        return None

# Fungsi untuk mengambil data Volara
def fetch_volara_stats(token):
    url = "https://api.volara.xyz/v1/user/stats"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()  
        else:
            log_error(f"Gagal mengambil data Volara: {response.status_code}")
            return None
    except Exception as e:
        log_error(f"Terjadi kesalahan saat mengambil data Volara: {e}")
        return None

# Fungsi untuk memilih container yang berjalan
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

# Fungsi untuk menjeda container
def pause_container(container):
    try:
        container_status = container.attrs['State']
        is_running = not container_status.get('Paused', False) and container_status.get('Running', False)

        if is_running:
            log_info(f"Menjeda container: {container.name}")
            container.pause()
            log_info(f"Container {container.name} telah dijeda.")
        else:
            log_info(f"Container {container.name} sudah dalam status paused atau berhenti.")
    except Exception as e:
        log_error(f"Terjadi kesalahan saat menjeda container: {e}")

# Fungsi untuk melanjutkan container
def unpause_container(container):
    try:
        container_status = container.attrs['State']
        is_paused = container_status.get('Paused', False)

        if is_paused:
            log_info(f"Melanjutkan container: {container.name}")
            container.unpause()
            log_info(f"Container {container.name} telah dilanjutkan.")
        else:
            log_info(f"Container {container.name} tidak dalam status paused, jadi tidak perlu dilanjutkan.")
    except Exception as e:
        log_error(f"Terjadi kesalahan saat melanjutkan container: {e}")

def monitor_gas_fee_and_manage_docker(container, token, gas_fee_threshold_high=0.3, gas_fee_threshold_low=0.2):
    container_paused = False 

    while True:
        data = fetch_gas_fee()
        volara_data = fetch_volara_stats(token)

        if data:
            log_info("Gas Fee Tracker:")
            
            if 'gas_prices' in data:
                average_gas = data['gas_prices'].get('average', None)
                
                if average_gas is not None:
                    log_info(f"Gas Fee Average: {average_gas}")

                    if average_gas > gas_fee_threshold_high:
                        if not container_paused:
                            log_warning(f"Gas fee tinggi! Menjeda container.")
                            pause_container(container)
                            container_paused = True  
                        else:
                            log_info("Gas fee masih tinggi. Tidak ada tindakan tambahan.")
                    elif average_gas < gas_fee_threshold_low:
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

        time.sleep(15)

shareithub()

def main():
    token = read_token_from_file()
    if not token:
        log_error("Token tidak ditemukan. Program dihentikan.")
        return

    gas_fee_threshold_high = float(input("Masukkan batas atas gas fee untuk menjeda container (misalnya 0.3): "))
    gas_fee_threshold_low = float(input("Masukkan batas bawah gas fee untuk melanjutkan container (misalnya 0.2): "))

    container = list_running_containers()
    if container:
        log_info(f"Memulai monitoring untuk container {container.name}...")
        monitor_gas_fee_and_manage_docker(container, token, gas_fee_threshold_high, gas_fee_threshold_low)

if __name__ == "__main__":
    main()
