# Import necessary modules and functions
import socket
import select
import pickle
import sqlite3 
import json
import os 
import utils.networking_utils as networking_utils
import utils.setup as setup 

# --- Network Configuration ---

# Define host IP address, TCP port, and buffer size
HOST = ''
HOST_IP = networking_utils.get_host_ip()
TCP_PORT = 50142        # get_open_port()
BUFSIZ = 4096


class TorrentServer(socket.socket):
    '''
    Torrent server class
    '''
    @staticmethod
    def server() -> str:
        '''
        placeholder
        '''
        server = TorrentServer()
        server.handle_connections()
        return server

    def __init__(self) -> None:
        '''
        intiate server socket and bind it.

        Args: 
            None.

        Returns:
            None.

        '''
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the server socket
        self.bind((HOST, TCP_PORT))
        self.listen(5)
        self.setblocking(0)
        self.CONNECTION_LIST = [self,]
        self.ID_BY_SOCKET = {}
        self.ID_BY_IP = {}
        self.PEER_PORT = {}
        self.PEER_INFO = {}

    def handle_connections(self) -> None:
        '''
        Handles incoming connections from clients and creates sessions.

        Args:
            None.

        Returns:
            None.
        '''
        while True:

            # Get the list sockets which are ready to be read or write through select
            read_sockets, write_sockets, _ = select.select(
                self.CONNECTION_LIST, set(self.CONNECTION_LIST).difference([self,]), 
                self.CONNECTION_LIST)

            for sock in read_sockets:
                if sock == self:
                    new_socket, address = sock.accept()
                    print(f'socket has joined from {address}')
                    self.CONNECTION_LIST.append(new_socket)
                    new_socket.send(pickle.dumps(['/peerinfo',]))
                else:
                    try:
                        sock_data = sock.recv(BUFSIZ).decode()
                        self.handle_client_commands(sock, sock_data)

                    # In case of connection error, disconnect the client
                    except (ConnectionResetError, Exception) as e:
                        self.disconnect(sock)

            for sock in write_sockets:
                try:     
                    if sock not in self.PEER_PORT:
                        sock.send(pickle.dumps(['/peerinfo',]))
                except (ConnectionResetError, Exception) as e:
                    self.disconnect(sock)
                

    def handle_client_commands(self, client: socket.socket, command:  str) -> None:
        '''
        Process a command received from a client.

        Args:
            command (str): The command received from the client.
            sock (socket.socket): The client's socket connected to the server.

        Returns:
            str: A message to be sent back to the client.
        '''
        parts = command.split(' ')
        msg_return = ''

        if parts[0] == '/upload':
            print('hello')
            msg_return = pickle.dumps((parts[-1], (self.PEER_INFO, self.ID_BY_IP)))

        elif parts[0] == '/download':
            pass
        elif parts[0] == '/disconnect':
            pass
        elif parts[0] == '/upload_complete':
            pass
        elif parts[0] == '/download_complete':
            pass
        elif parts[0] == '!peerinfo':
            peer_port = int(parts[1])
            PEER_UUID = parts[2]
            client_ip = networking_utils.get_ip_adress(client)

            self.ID_BY_SOCKET[client] = PEER_UUID
            self.ID_BY_IP[client_ip] = PEER_UUID

          
            self.PEER_PORT[client] = peer_port
            self.PEER_INFO[PEER_UUID] = (
                client_ip, peer_port)
            
        elif parts[0] == '!update':
            metadata = json.loads(parts[1])
            peer_id = parts[2]
            
       
            sql_data = [metadata['file_name'], metadata['file_extension'],int(metadata['file_size']), metadata['parts']]
            sql = '''
            INSERT INTO torrent (file_name, file_extension, file_size, parts)
            VALUES (?,?,?,?)
          '''
            
            with sqlite3.connect('torrent.db') as conn:
                c = conn.cursor()
                c.execute(sql,sql_data)
                conn.commit()
                
          
            




        if msg_return:
            client.send(msg_return)

    def disconnect(self, sock: socket.socket) -> None:
        '''
        Disconnects a client from the server, removes them from the active connection list.

        Args: 
            sock (socket):  socket of the client to be disconnected.

        Returns:
            None.
        '''
        if sock in self.CONNECTION_LIST: 
            self.CONNECTION_LIST.remove(sock)
            print(f'{sock.getpeername()} has left')
        sock.close()


if __name__ == '__main__':
    if not os.path.exists(os.path.join(os.getcwd(),'torrent.db')):
        setup.setup_server()
    torrent_server = TorrentServer.server()
