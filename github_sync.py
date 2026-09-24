import urllib.request
import urllib.parse
import json
import time
import os
import subprocess

CLIENT_ID = "178c6fc778ccc68e1d6a" # GitHub CLI client ID

def request_device_code():
    url = "https://github.com/login/device/code"
    data = urllib.parse.urlencode({"client_id": CLIENT_ID, "scope": "repo"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def poll_for_token(device_code, interval):
    url = "https://github.com/login/oauth/access_token"
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Accept": "application/json"})
    
    print("Aguardando autorização...")
    while True:
        try:
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read().decode())
                if "access_token" in res:
                    return res["access_token"]
                if res.get("error") != "authorization_pending":
                    print("Erro:", res)
                    return None
        except Exception as e:
            pass
        time.sleep(interval)

def create_repo(token, repo_name):
    url = "https://api.github.com/user/repos"
    data = json.dumps({"name": repo_name, "private": False}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 422: # Repo already exists
            print("Repositório já existe.")
            req_user = urllib.request.Request("https://api.github.com/user", headers={"Authorization": f"token {token}"})
            with urllib.request.urlopen(req_user) as r:
                user_info = json.loads(r.read().decode())
                return {"clone_url": f"https://github.com/{user_info['login']}/{repo_name}.git", "owner": {"login": user_info['login']}}
        raise e

def main():
    print("Iniciando conexão com o GitHub...")
    device_info = request_device_code()
    print("\n" + "="*50)
    print("AUTH_CODE_START")
    print(device_info['user_code'])
    print("AUTH_CODE_END")
    print(f"URI: {device_info['verification_uri']}")
    print("="*50 + "\n")
    
    token = poll_for_token(device_info['device_code'], device_info['interval'])
    if not token:
        return
        
    print("Autorizado com sucesso! Criando repositório 'torresweb-ads'...")
    repo_info = create_repo(token, "torresweb-ads")
    username = repo_info["owner"]["login"]
    
    print("Configurando o Git local e enviando os arquivos...")
    remote_url = f"https://{username}:{token}@github.com/{username}/torresweb-ads.git"
    
    subprocess.run(["git", "branch", "-M", "main"], check=True)
    subprocess.run(["git", "remote", "remove", "origin"], stderr=subprocess.DEVNULL)
    subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
    
    print("Enviando (push) para o GitHub...")
    subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
    
    clean_url = f"https://github.com/{username}/torresweb-ads.git"
    subprocess.run(["git", "remote", "set-url", "origin", clean_url], check=True)
    
    print(f"DONE: {clean_url}")

if __name__ == "__main__":
    main()
