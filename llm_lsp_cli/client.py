import socket
import json
import os

from llm_lsp_cli.constants import DEFAULT_SOCKET_PATH

class LspCliClient:
    def __init__(self, socket_path: str = str(DEFAULT_SOCKET_PATH)):
        self.socket_path = socket_path

    def ping(self) -> bool:
        """Checks if the daemon is alive."""
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.0)
                sock.connect(self.socket_path)
                request_data = {"command": "ping", "params": {}}
                sock.sendall(json.dumps(request_data).encode('utf-8') + b'\\n')
                buffer = sock.recv(1024)
                return b"pong" in buffer
        except (socket.timeout, ConnectionRefusedError, FileNotFoundError):
            return False

        """Sends a request to the daemon."""
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(self.socket_path)

            # Resolve workspace root to absolute path
            if 'workspace_root' in params:
                params['workspace_root'] = os.path.abspath(params['workspace_root'])

            request_data = {"command": command, "params": params}
            sock.sendall(json.dumps(request_data).encode('utf-8'))
            sock.sendall(b'\\n') # Delimiter

            buffer = b""
            while True:
                data = sock.recv(1024)
                if not data:
                    break
                buffer += data
                if b'\\n' in buffer:
                     break

            response = json.loads(buffer.decode('utf-8').strip())
            return response
