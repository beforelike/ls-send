"""
LS Send - File Transfer Module

HTTP-based file transfer with progress tracking.
"""

import socket
import threading
import json
import os
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Callable, Optional, List, Tuple
from urllib.parse import urlparse, parse_qs
import io

from . import (
    TRANSFER_PORT, FileInfo, TransferRequest, TransferResponse, ProgressMessage,
    calculate_file_hash, generate_device_id
)


class TransferHandler(BaseHTTPRequestHandler):
    """HTTP request handler for file transfers"""
    
    server_instance = None  # Will be set by TransferServer
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def do_GET(self):
        """Handle GET requests (progress, status)"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/status':
            self._send_status()
        elif parsed.path.startswith('/progress/'):
            session_id = parsed.path.split('/')[-1]
            self._send_progress(session_id)
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests (transfer, file upload)"""
        parsed = urlparse(self.path)
        
        if parsed.path == '/transfer':
            self._handle_transfer_request()
        elif parsed.path.startswith('/file/'):
            session_id = parsed.path.split('/')[-1]
            self._handle_file_upload(session_id)
        elif parsed.path.startswith('/cancel/'):
            session_id = parsed.path.split('/')[-1]
            self._handle_cancel(session_id)
        else:
            self.send_error(404, "Not Found")
    
    def _send_json(self, data: dict, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_status(self):
        """Send server status"""
        self._send_json({
            'status': 'running',
            'port': TRANSFER_PORT
        })
    
    def _send_progress(self, session_id: str):
        """Send progress for a session"""
        if self.server_instance:
            progress = self.server_instance.get_progress(session_id)
            if progress:
                self._send_json(progress)
            else:
                self.send_error(404, "Session not found")
        else:
            self.send_error(500, "Server not initialized")
    
    def _handle_transfer_request(self):
        """Handle incoming transfer request"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            request = TransferRequest.from_json(body)
            
            if self.server_instance and self.server_instance._on_transfer_request:
                accepted, session_id, message = self.server_instance._on_transfer_request(request)
                
                response = TransferResponse(
                    accepted=accepted,
                    session_id=session_id,
                    message=message
                )
                self._send_json(response.__dict__)
            else:
                self._send_json({
                    'type': 'transfer_response',
                    'accepted': False,
                    'message': 'Server not ready'
                }, 503)
        
        except Exception as e:
            self._send_json({
                'type': 'transfer_response',
                'accepted': False,
                'message': str(e)
            }, 400)
    
    def _handle_file_upload(self, session_id: str):
        """Handle file upload"""
        if not self.server_instance:
            self.send_error(500, "Server not initialized")
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        file_name = self.headers.get('X-File-Name', 'unknown')
        
        try:
            # Get save path from server
            save_path = self.server_instance.get_save_path(session_id, file_name)
            
            if not save_path:
                self._send_json({'error': 'Invalid session'}, 400)
                return
            
            # Read and save file in chunks
            bytes_received = 0
            chunk_size = 8192
            
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                while bytes_received < content_length:
                    chunk = self.rfile.read(min(chunk_size, content_length - bytes_received))
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_received += len(chunk)
                    
                    # Report progress
                    if self.server_instance._on_progress:
                        self.server_instance._on_progress(session_id, bytes_received, content_length, file_name)
            
            # Verify hash if provided
            expected_hash = self.headers.get('X-File-Hash', '')
            if expected_hash:
                actual_hash = calculate_file_hash(save_path)
                if actual_hash != expected_hash:
                    os.remove(save_path)
                    self._send_json({'error': 'Hash mismatch'}, 400)
                    return
            
            self._send_json({'success': True, 'bytes_received': bytes_received})
            
        except Exception as e:
            self._send_json({'error': str(e)}, 500)
    
    def _handle_cancel(self, session_id: str):
        """Handle transfer cancellation"""
        if self.server_instance and self.server_instance._on_cancel:
            self.server_instance._on_cancel(session_id)
            self._send_json({'success': True})
        else:
            self._send_json({'success': False}, 500)


class TransferServer:
    """
    HTTP server for handling file transfers.
    
    Runs on a separate thread and handles incoming transfer requests.
    """
    
    def __init__(self, device_id: str = None, save_dir: str = "./received_files"):
        self.device_id = device_id or generate_device_id()
        self.save_dir = save_dir
        
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Session management
        self.sessions: Dict[str, dict] = {}
        self.sessions_lock = threading.Lock()
        
        # Callbacks
        self._on_transfer_request: Optional[Callable[[TransferRequest], Tuple[bool, str, str]]] = None
        self._on_progress: Optional[Callable[[str, int, int, str], None]] = None
        self._on_complete: Optional[Callable[[str], None]] = None
        self._on_cancel: Optional[Callable[[str], None]] = None
    
    def set_callbacks(self,
                     on_transfer_request: Callable[[TransferRequest], Tuple[bool, str, str]] = None,
                     on_progress: Callable[[str, int, int, str], None] = None,
                     on_complete: Callable[[str], None] = None,
                     on_cancel: Callable[[str], None] = None):
        """Set callback functions for transfer events"""
        self._on_transfer_request = on_transfer_request
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_cancel = on_cancel
    
    def start(self):
        """Start the transfer server"""
        if self._running:
            return
        
        self._server = HTTPServer(('0.0.0.0', TRANSFER_PORT), TransferHandler)
        TransferHandler.server_instance = self
        
        self._running = True
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        
        print(f"Transfer server started on port {TRANSFER_PORT}")
    
    def stop(self):
        """Stop the transfer server"""
        self._running = False
        
        if self._server:
            self._server.shutdown()
            self._server = None
        
        if self._server_thread:
            self._server_thread.join(timeout=2.0)
    
    def create_session(self, request: TransferRequest) -> str:
        """Create a new transfer session"""
        import uuid
        session_id = str(uuid.uuid4())[:8]
        
        with self.sessions_lock:
            self.sessions[session_id] = {
                'request': request,
                'files_received': 0,
                'bytes_received': 0,
                'total_bytes': sum(f['size'] for f in request.files),
                'current_file': '',
                'status': 'pending'
            }
        
        return session_id
    
    def get_save_path(self, session_id: str, file_name: str) -> Optional[str]:
        """Get save path for a file in a session"""
        with self.sessions_lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            save_path = os.path.join(self.save_dir, session_id, file_name)
            
            # Update session
            session['current_file'] = file_name
            session['status'] = 'receiving'
        
        return save_path
    
    def get_progress(self, session_id: str) -> Optional[dict]:
        """Get progress for a session"""
        with self.sessions_lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            return {
                'session_id': session_id,
                'files_received': session['files_received'],
                'total_files': len(session['request'].files),
                'bytes_received': session['bytes_received'],
                'total_bytes': session['total_bytes'],
                'current_file': session['current_file'],
                'status': session['status']
            }
    
    def complete_session(self, session_id: str):
        """Mark a session as complete"""
        with self.sessions_lock:
            if session_id in self.sessions:
                self.sessions[session_id]['status'] = 'complete'
        
        if self._on_complete:
            self._on_complete(session_id)
    
    def cancel_session(self, session_id: str):
        """Cancel a session"""
        with self.sessions_lock:
            if session_id in self.sessions:
                self.sessions[session_id]['status'] = 'cancelled'
        
        if self._on_cancel:
            self._on_cancel(session_id)


class FileSender:
    """
    Client for sending files to a remote device.
    """
    
    def __init__(self, target_ip: str, target_port: int = TRANSFER_PORT):
        self.target_ip = target_ip
        self.target_port = target_port
        self._session_id = None
        self._on_progress: Optional[Callable[[str, int, int], None]] = None
    
    def set_progress_callback(self, callback: Callable[[str, int, int], None]):
        """Set progress callback"""
        self._on_progress = callback
    
    def send_files(self, files: List[str], sender_id: str, sender_name: str) -> Tuple[bool, str]:
        """
        Send files to remote device.
        
        Args:
            files: List of file paths to send
            sender_id: Sender device ID
            sender_name: Sender display name
        
        Returns:
            Tuple of (success, message)
        """
        import urllib.request
        import urllib.error
        
        try:
            # Prepare file info
            file_infos = []
            for filepath in files:
                if not os.path.exists(filepath):
                    return False, f"File not found: {filepath}"
                
                file_infos.append({
                    'name': os.path.basename(filepath),
                    'size': os.path.getsize(filepath),
                    'hash': calculate_file_hash(filepath)
                })
            
            # Create transfer request
            import uuid
            session_id = str(uuid.uuid4())[:8]
            
            request = TransferRequest(
                sender_id=sender_id,
                sender_name=sender_name,
                files=file_infos,
                session_id=session_id
            )
            
            # Send transfer request
            url = f"http://{self.target_ip}:{self.target_port}/transfer"
            data = json.dumps(request.__dict__).encode('utf-8')
            
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if not result.get('accepted', False):
                    return False, result.get('message', 'Transfer rejected')
                
                self._session_id = result.get('session_id', session_id)
            
            # Send each file
            for i, filepath in enumerate(files):
                success, msg = self._send_file(filepath, file_infos[i])
                if not success:
                    return False, f"Failed to send {os.path.basename(filepath)}: {msg}"
            
            return True, "Transfer complete"
        
        except Exception as e:
            return False, str(e)
    
    def _send_file(self, filepath: str, file_info: dict) -> Tuple[bool, str]:
        """Send a single file"""
        import urllib.request
        
        try:
            url = f"http://{self.target_ip}:{self.target_port}/file/{self._session_id}"
            
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            req = urllib.request.Request(url, data=file_data, method='POST')
            req.add_header('Content-Type', 'application/octet-stream')
            req.add_header('X-File-Name', file_info['name'])
            req.add_header('X-File-Hash', file_info['hash'])
            req.add_header('Content-Length', str(len(file_data)))
            
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get('success', False):
                    if self._on_progress:
                        self._on_progress(file_info['name'], result['bytes_received'], file_info['size'])
                    return True, "OK"
                else:
                    return False, result.get('error', 'Unknown error')
        
        except Exception as e:
            return False, str(e)
    
    def cancel(self):
        """Cancel the current transfer"""
        import urllib.request
        
        if self._session_id:
            try:
                url = f"http://{self.target_ip}:{self.target_port}/cancel/{self._session_id}"
                req = urllib.request.Request(url, method='POST')
                urllib.request.urlopen(req, timeout=5)
            except:
                pass
