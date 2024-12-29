import requests
import time
import docker
import requests

from shareithub import HTTPTools, ASCIITools

ASCIITools.print_ascii_intro()

client = docker.from_env()


PROXY = {
    "http": "PASTE YOUR CURL PROXY WITH HTTP://",
    "https": "PASTE YOUR CURL PROXY WITH HTTPS://",
}


def read_token_from_file():
    try:
        with open('token.txt', 'r') as file:
            token = file.read().strip()
            return token
    except Exception as e:
        print(f"Terjadi kesalahan saat membaca token: {e}")
        return None


def fetch_gas_fee():
    url = "https://api.vanascan.io/api/v2/stats"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()  
        elif response.status_code == 403:
            print("Gagal mengambil data: 403. Akan mencoba ulang dengan proxy.")

            response_with_proxy = requests.get(url, proxies=PROXY)
            if response_with_proxy.status_code == 200:
                return response_with_proxy.json() 
            else:
                print(f"Gagal mengambil data dengan proxy: {response_with_proxy.status_code}")
                return None
        else:
            print(f"Gagal mengambil data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        return None


def fetch_volara_stats(token):
    url = "https://api.volara.xyz/v1/user/stats"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json() 
        else:
            print(f"Gagal mengambil data Volara: {response.status_code}")
            return None
    except Exception as e:
        print(f"Terjadi kesalahan saat mengambil data Volara: {e}")
        return None


def list_running_containers():
    try:
        containers = client.containers.list() 
        if not containers:
            print("Tidak ada container yang berjalan saat ini.")
            return None

        print("Daftar container yang berjalan:")
        for idx, container in enumerate(containers, start=1):
            print(f"{idx}. {container.name} (Image: {container.image.tags[0] if container.image.tags else 'No image'})")
        
        choice = int(input("\nPilih nomor container yang ingin dimonitor: "))
        if choice < 1 or choice > len(containers):
            print("Pilihan tidak valid.")
            return None
        
        selected_container = containers[choice - 1]
        print(f"Anda memilih container: {selected_container.name}")
        return selected_container
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        return None


def pause_container(container):
    try:
        print(f"Menjeda container: {container.name}")
        container.pause()
        print(f"Container {container.name} telah dijeda.")
    except Exception as e:
        print(f"Terjadi kesalahan saat menjeda container: {e}")


def unpause_container(container):
    try:
        print(f"Melanjutkan container: {container.name}")
        container.unpause()
        print(f"Container {container.name} telah dilanjutkan.")
    except Exception as e:
        print(f"Terjadi kesalahan saat melanjutkan container: {e}")


def monitor_gas_fee_and_manage_docker(container, token):
    container_paused = False  

    while True:

        data = fetch_gas_fee()


        volara_data = fetch_volara_stats(token)

        if data:
            print("Gas Fee Tracker:")
            
            if 'gas_prices' in data:
                average_gas = data['gas_prices'].get('average', None)
                
                if average_gas is not None:
                    print(f"Gas Fee Average: {average_gas}")

                    if average_gas > 0.2:
                        if not container_paused:
                            print("Gas fee tinggi! Menjeda container.")
                            pause_container(container)
                            container_paused = True
                        else:
                            print("Gas fee masih tinggi. Tidak ada tindakan tambahan.")
                    elif average_gas < 0.1:
                        if container_paused:
                            print("Gas fee rendah. Melanjutkan container.")
                            unpause_container(container)
                            container_paused = False
                        else:
                            print("Gas fee masih rendah. Tidak ada tindakan tambahan.")
                    else:
                        print("Gas fee normal. Tidak ada perubahan pada container.")
                else:
                    print("Data gas fee average tidak ditemukan.")
            else:
                print("Data gas_prices tidak ditemukan dalam respons.")
        else:
            print("Tidak dapat mengambil data gas fee.")


        if volara_data and volara_data.get("success"):
            print("\nVolara Stats:")
            index_stats = volara_data.get('data', {}).get('indexStats', {})
            reward_stats = volara_data.get('data', {}).get('rewardStats', {})
            rank_stats = volara_data.get('data', {}).get('rankStats', {})

            total_indexed_tweets = index_stats.get("totalIndexedTweets", "Tidak tersedia")
            vortex_score = reward_stats.get("vortexScore", "Tidak tersedia")
            vortex_rank = rank_stats.get("vortexRank", "Tidak tersedia")

            print(f"Total Indexed Tweets: {total_indexed_tweets}")
            print(f"Vortex Score: {vortex_score}")
            print(f"Vortex Rank: {vortex_rank}")
        else:
            print("Tidak dapat mengambil data Volara atau respons tidak berhasil.")

        time.sleep(60)

def main():
  
    token = read_token_from_file()
    if not token:
        print("Token tidak ditemukan. Program dihentikan.")
        return
    
    container = list_running_containers()
    if container:
        print(f"Memulai monitoring untuk container {container.name}...")
        monitor_gas_fee_and_manage_docker(container, token)

if __name__ == "__main__":
    main()
