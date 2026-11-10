import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('95.182.87.115', username='root', password='Arman4237340', timeout=10)

test_udp_script = r"""
import socket, struct, time, subprocess

proc = subprocess.Popen(['/usr/local/x-ui/bin/xray-linux-amd64', 'run', '-c', '/tmp/test_xray_client.json'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(2)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)
s.connect(('127.0.0.1', 20808))
s.sendall(b'\x05\x01\x00') # Ver 5, 1 method: No Auth
resp = s.recv(2)
print("SOCKS5 Auth resp:", resp)

# Request UDP Associate:
s.sendall(b'\x05\x03\x00\x01\x00\x00\x00\x00\x00\x00')
resp = s.recv(10)
print("SOCKS5 UDP Assoc resp:", resp)
if len(resp) >= 10 and resp[1] == 0:
    relay_ip = socket.inet_ntoa(resp[4:8])
    relay_port = struct.unpack('!H', resp[8:10])[0]
    print(f"UDP Relay is at {relay_ip}:{relay_port}")

    # Build DNS query for google.com
    dns_query = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06google\x03com\x00\x00\x01\x00\x01'
    socks_udp_pkt = b'\x00\x00\x00\x01\x08\x08\x08\x08\x00\x35' + dns_query

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.settimeout(5)
    start = time.time()
    udp_sock.sendto(socks_udp_pkt, (relay_ip, relay_port))
    try:
        data, addr = udp_sock.recvfrom(2048)
        print(f"Received UDP response ({len(data)} bytes) in {int((time.time()-start)*1000)}ms: {data[:20]}")
    except Exception as e:
        print("UDP DNS test failed:", e)
    udp_sock.close()
else:
    print("UDP Associate failed!")
s.close()
proc.terminate()
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/test_udp.py', 'w') as f:
    f.write(test_udp_script)
sftp.close()

_, stdout, stderr = ssh.exec_command('python3 /tmp/test_udp.py')
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
