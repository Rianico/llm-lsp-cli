import socket
import json
import threading

from llm_lsp_cli.lsp_client import LSPClient
from llm_lsp_cli.config import find_lang_server_executable, Config
from llm_lsp_cli.constants import CONFIG_DIR
import os

    def handle_client(self, conn: socket.socket):
        """Handle an incoming client connection."""
        buffer = ""
        try:
            while self._running:
                data = conn.recv(1024)
                if not data:
                    break
                buffer += data.decode('utf-8')
                if '\\n' in buffer:
                    request_str, buffer = buffer.split('\\n', 1)
                    request = json.loads(request_str)

                    command = request.get("command")
                    params = request.get("params", {})
                    workspace_root = params.get("workspace_root")

                    # A simple language detector
                    language = "python" if params.get('file_path', '').endswith('.py') else "typescript"

                    lsp_client = self.get_or_start_lsp_client(workspace_root, language)

                    # For now, we'll implement definition directly
                    if command == "request_definition":
                        def on_response(result):
                            response = {"success": True, "result": result.get('result')}
                            conn.sendall(json.dumps(response).encode('utf-8') + b'\\n')

                        lsp_params = {
                            "textDocument": {"uri": f"file://{os.path.abspath(params['file_path'])}"},
                            "position": {"line": params['line'] - 1, "character": params['character'] - 1}
                        }
                        lsp_client.request("textDocument/definition", lsp_params, on_response)
                    else:
                        response = {"success": False, "error": {"message": f"Unknown command: {command}"}}
                        conn.sendall(json.dumps(response).encode('utf-8') + b'\\n')

                    # Keep connection open for async response
                    return
        except Exception:
            # Handle client disconnection or errors
            pass
        finally:
            conn.close()


    def build_lsp_params(self, command: str, params: dict) -> dict:
        file_uri = f"file://{os.path.abspath(params['file_path'])}" if 'file_path' in params else None

        if command in ["request_definition", "request_references", "request_completions", "request_hover"]:
            return {
                "textDocument": {"uri": file_uri},
                "position": {"line": params['line'] - 1, "character": params['character'] - 1}
            }
        if command == "request_document_symbols":
            return {"textDocument": {"uri": file_uri}}
        if command == "request_workspace_symbol":
            return {"query": params["query"]}
        return {}

    def start(self):
        """Starts listening for connections."""
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.socket_path)
        self.server.listen(1)

        while self._running:
            try:
                conn, _ = self.server.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(conn,))
                client_thread.daemon = True
                client_thread.start()
            except Exception:
                break

    def stop(self):
        self._running = False
        if self.server:
            self.server.close()
