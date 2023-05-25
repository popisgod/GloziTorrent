# Import necessary modules and functions
import socket
from networking_utils import *
from select import select 
import csv 
import pickle 

# --- Network Configuration --- 

# Define host IP address, TCP port, and buffer size
HOST = ''
HOST_IP = get_host_ip()
TCP_PORT =  50142        # get_open_port()
BUFSIZ = 4096  

class torrent_server(socket.socket):
    '''
    Torrent server class
    '''
    @staticmethod
    def server() -> str:
        server = torrent_server()
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
                read_sockets, write_sockets, error_sockets = select.select(
                    self.CONNECTION_LIST, set(self.CONNECTION_LIST).difference(self), self.CONNECTION_LIST)

                for sock in read_sockets: 
                        if sock == self:
                            new_socket, address = sock.accept()
                            self.CONNECTION_LIST.append(new_socket)
                            self.ID_BY_SOCKET[new_socket] = get_mac_address(new_socket)
                            self.ID_BY_IP[get_host_ip(new_socket)] = self.ID_BY_SOCKET[new_socket] 
                        else: 
                            
                            try: 
                                res = sock.recv(BUFSIZ).decode()
                                self.handle_client_commands(sock, res)
                                
                            # In case of connection error, disconnect the client
                            except (ConnectionResetError, Exception) as E:
                                self.disconnect(sock)
                                
                for sock in write_sockets:
                    if sock not in self.PEER_PORT.keys():
                        sock.send('/port'.encode())
                    
    
    def handle_client_commands(self, client : socket.socket, command :  str) -> None: 
        '''
        Process a command received from a client.

        Args:
            command (str): The command received from the client.
            sock (socket.socket): The client's socket connected to the server.
        
        Returns:
            str: A message to be sent back to the client.
        '''
        parts = command.split() 
        msg_return = ''
        
        if parts[0] == '/upload':
            peers = self.PEER_INFO
            msg_return = pickle.dumps((command,(peers,self.ID_BY_IP)))
            
        elif parts[0] == '/download':
            pass
        elif parts[0] == '/disconnect':
            pass
        elif parts[0] == '/upload_complete':
            pass
        elif parts[0] == '/download_complete':
            pass
        elif parts[0] == '!port':
            peer_port = int(parts[1])
            self.PEER_PORT[client] = peer_port
            self.PEER_INFO[self.ID_BY_SOCKET[client]] = (get_host_ip(client), peer_port)
        
        if msg_return:
            client.send(msg_return)
                    
    def disconnect(self, sock : socket.socket) -> None: 
        '''
        Disconnects a client from the server, removes them from the active connection list.

        Args: 
            sock (socket):  socket of the client to be disconnected.
            
        Returns:
            None.
        '''
        
        self.CONNECTION_LIST.remove(sock)
        sock.close()
    
if __name__=='__main__':
    server = torrent_server.server()