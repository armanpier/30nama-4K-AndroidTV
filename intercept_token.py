import socket
import select
import threading
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

LISTEN_PORT = 18888
FORWARD_PORT = 10808
FORWARD_HOST = '127.0.0.1'

token_found = None

def handle_client(client_socket):
    global token_found
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        remote_socket.connect((FORWARD_HOST, FORWARD_PORT))
    except Exception as e:
        client_socket.close()
        return

    sockets = [client_socket, remote_socket]
    while sockets:
        readable, _, _ = select.select(sockets, [], [], 10)
        if not readable:
            break
        for s in readable:
            other = remote_socket if s is client_socket else client_socket
            try:
                data = s.recv(4096)
                if not data:
                    sockets = []
                    break
                
                # Check for c-token in client requests
                if s is client_socket:
                    text = data.decode('utf-8', errors='ignore')
                    if 'c-token' in text.lower() or 'bearer' in text.lower():
                        print("\n" + "="*50)
                        print("[INTERCEPTED AUTH TRAFFIC]")
                        print(text[:800])
                        print("="*50 + "\n")
                        m = re.search(r'c-token:\s*([a-zA-Z0-9_-]+)', text, re.I)
                        if m:
                            token_found = m.group(1)
                            print(f"[FOUND TOKEN]: {token_found}")
                            with open('captured_c_token.txt', 'w') as f:
                                f.write(token_found)
                
                other.sendall(data)
            except Exception:
                sockets = []
                break

    client_socket.close()
    remote_socket.close()

def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', LISTEN_PORT))
    server.listen(10)
    print(f"Intercepting proxy listening on 127.0.0.1:{LISTEN_PORT} -> forwarding to 127.0.0.1:{FORWARD_PORT}")
    
    server.settimeout(60)
    start_time = time.time()
    while time.time() - start_time < 60 and not token_found:
        try:
            client, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client,))
            t.daemon = True
            t.start()
        except socket.timeout:
            continue
        except Exception:
            break
    server.close()

if __name__ == '__main__':
    import time
    run_server()
