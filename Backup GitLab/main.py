import os
import paramiko
import time
from scp import SCPClient

# SSH connection details
HOST = ''
PORT = 22
USERNAME = ''
SSH_KEY_PATH = ''

# Paths
BACKUP_CMD = 'gitlab-rake gitlab:backup:create'
BACKUP_PATH = '/var/opt/gitlab/backups/'
GITLAB_ETC_PATH = '/etc/gitlab/'
ARCHIVE_NAME = "gitlab_etc.tar.gz"
ARCHIVE_PATH_ON_SERVER = os.path.join(BACKUP_PATH, ARCHIVE_NAME)

# Local paths
LOCAL_DOWNLOAD_DIR = 'G:\\Backups\\GitLab\\'

print("Connecting to the server...")
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
private_key = paramiko.RSAKey(filename=SSH_KEY_PATH)
ssh_client.connect(HOST, port=PORT, username=USERNAME, pkey=private_key)
print("Connected!")

print("Creating backup on the server...")
channel = ssh_client.get_transport().open_session()
channel.exec_command(BACKUP_CMD)
while True:
    if channel.recv_ready():
        output = channel.recv(4096).decode('utf-8')
        print(output, end='')
    if channel.exit_status_ready():
        break

stdin, stdout, stderr = ssh_client.exec_command(f'ls -t {BACKUP_PATH} | head -n 1')
backup_filename = stdout.read().decode('utf-8').strip()

print("Compressing /etc/gitlab on the server in the backup path...")
ssh_client.exec_command(f'tar -czvf {ARCHIVE_PATH_ON_SERVER} -C /etc gitlab')

print("Downloading files...")
with SCPClient(ssh_client.get_transport()) as scp:
    scp.get(os.path.join(BACKUP_PATH, backup_filename), LOCAL_DOWNLOAD_DIR)
    scp.get(ARCHIVE_PATH_ON_SERVER, LOCAL_DOWNLOAD_DIR)

# Remove the compressed archive and backup from the server
ssh_client.exec_command(f'rm {os.path.join(BACKUP_PATH, backup_filename)}')
ssh_client.exec_command(f'rm {ARCHIVE_PATH_ON_SERVER}')

print("Closing SSH connection...")
ssh_client.close()

# Get the current Unix timestamp
timestamp = int(time.time())
print("Packing files into a final archive...")
os.chdir(LOCAL_DOWNLOAD_DIR)
os.system(f'tar -czvf {timestamp}_gitlab_full_backup.tar.gz {backup_filename} {ARCHIVE_NAME}')

# Remove downloaded files after packing
os.remove(os.path.join(LOCAL_DOWNLOAD_DIR, backup_filename))
os.remove(os.path.join(LOCAL_DOWNLOAD_DIR, ARCHIVE_NAME))

print("Archiving completed. Only the final archive remains.")
