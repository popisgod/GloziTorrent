# Import necessary modules and functions
from __future__ import annotations
import socket
import pickle
import multiprocessing.pool
import select
import os
import shutil
import json
from threading import Thread
import utils.networking_utils as networking_utils
import utils.torrent_utils as torrent_utils
import utils.setup as setup
from pathlib import Path
import time
from typing import List, Dict, Union
# --- Network Configuration ---


# Define host IP address, TCP port, and buffer size
HOST = ''
TORRENT_SERVER = '10.100.102.3'
TORRENT_PORT = 50142
HOST_IP = networking_utils.get_host_ip()
TCP_PORT = networking_utils.get_open_port()
BUFSIZ = 4096


class PeerToPeer(socket.socket):
    '''
    peer_to_peer server class
    '''
    @staticmethod
    def server() -> PeerToPeer:
        '''
        placeholder

        '''
        server = PeerToPeer()
        handle_connections_thread = Thread(
            target=server.handle_connections)
        handle_connections_thread.daemon = True
        handle_connections_thread.start()
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
        # self.bind((HOST, TCP_PORT))
        # self.listen(5)
        # self.setblocking(0)
        self.CONNECTION_LIST : List[socket.socket] = [self,]
        self.file_downloads = {}
        self.file_uploads = {}

                                  
    def handle_connections(self) -> None:
        '''
        Handles incoming connections .

        Args:
            None.
            
        Returns:
            None.
        '''


        # Bind the server socket
        self.bind((HOST, TCP_PORT))
        self.listen(5)
        self.setblocking(False)

        print('---Server is running---')


        while True:
            # Get the list sockets which are ready to be read or write through select
            read_sockets, write_sockets, error_sockets = select.select(
                self.CONNECTION_LIST, self.CONNECTION_LIST, [])

            # Loop over sockets and accept new connections
            for sock in read_sockets:
                if sock == self:
                    new_socket, address = sock.accept()
                    print('Connect:', address, id(new_socket))
                    self.CONNECTION_LIST.append(new_socket)
                else:
                    try:
                        data : bytes = sock.recv(BUFSIZ)

                        if not data:
                            self.disconnect(sock)

                        else:
                            if self.file_uploads.get(sock, ''):
                                file = self.file_uploads[sock]['file']
                                remaining_size = self.file_uploads[sock]['remaining_size']
                                file.write(data)
                                self.file_uploads[sock]['remaining_size'] = remaining_size - len(
                                    data)

                                # If the entire file is received, close the file and remove the client from the dictionary
                                if self.file_uploads[sock]['remaining_size'] <= 0:
                                    file.close()
                                    print(f"File {self.file_uploads[sock]['file_name']} has been received from",sock.getpeername())
                                    
                                    # extract tar file and delete it 
                                    file_dir = os.path.join(os.getcwd(), self.file_uploads[sock]['file_name'] + '.torrent')
                                    os.makedirs(file_dir)
                                    torrent_utils.extract_tar_file(self.file_uploads[sock]['file_path'], file_dir)
                                    os.remove(self.file_uploads[sock]['file_path'])
                                    self.disconnect(sock)
                            else:
                                self.handle_client_commands(sock, data.decode())


                    # In case of connection error, disconnect the client
                    except (ConnectionResetError, Exception) as E:
                        self.disconnect(sock)
                        
            for sock in write_sockets:
                if self.file_downloads.get(sock,''):
                    file = self.file_downloads[sock]['file']
                    sock.send(file.read(BUFSIZ))
                    self.file_downloads[sock]['remaining_size'] -= BUFSIZ
                    if self.file_downloads[sock]['remaining_size'] < 0:
                        file.close()
                        print(f"File {self.file_downloads[sock]['file_name']} has been downloaded from",sock.getpeername())
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
        parts = command.split()
        msg_return = ''

        if parts[0] == '/upload_part':
            file_name, file_size = parts[1], parts[2]
            file_size = int(file_size)

            self.file_uploads[client] = {
                'file_name': None,
                'file': None,
                'remaining_size': 0,
                'file_path' : None,
                'file_status' : 'UP'
            }  

            # Open the file for writing
            file_path = os.path.join(os.getcwd(),file_name)
            self.file_uploads[client]['file_path'] = file_path
            self.file_uploads[client]['file_name'] = file_name
            self.file_uploads[client]['file'] = open(file_path, 'wb')
            self.file_uploads[client]['remaining_size'] = file_size

            client.send('!OK'.encode())

        elif parts[0] == '/download':
            self.file_downloads[client] = {
                'file_name': None,
                'file': None,
                'remaining_size': 0,
                'file_path' : None,
                'file_status' : 'DOWN'
            }  
            
            with open(os.path.join(parts[1] + '.torrent','metadata.json'), 'r') as file:
                metadata = json.loads(file.read())
            file_path = os.path.join(parts[1] + '.torrent', metadata['parts'][parts[2]] + '.bin')

            self.file_downloads[client]['file_name'] = parts[1]
            self.file_downloads[client]['file'] = open(file_path, 'rb')
            self.file_downloads[client]['remaining_size'] = os.path.getsize(file_path)
            print('size', parts[1], )
            client.send(str(self.file_downloads[client]['remaining_size']).encode())

            
        elif parts[0] == '/disconnect':
            pass
        elif parts[0] == '/upload_complete':
            pass
        elif parts[0] == '/download_complete':
            pass

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
        
        print('socket has been disconnected', sock.getpeername())
        self.CONNECTION_LIST.remove(sock)
        if sock in self.file_downloads:
            del self.file_downloads[sock]
        if sock in self.file_uploads:
            del self.file_uploads[sock]
        sock.close()


class TorrentClient(socket.socket):
    '''
    Torrent client class 
    '''
    @staticmethod
    def server() -> TorrentClient:
        '''
        placeholder
        '''
        server = TorrentClient()
        receive_thread = Thread(
            target=server.receive_wrapper)
        receive_thread.daemon = True
        receive_thread.start()
        return server

    def __init__(self) -> None:
        '''
        intiate client socket and connect it to the server.

        Args: 
            None.

        Returns:
            None.

        '''

        super().__init__(socket.AF_INET, socket.SOCK_STREAM)

        # connect to the server socket
        self.connect((TORRENT_SERVER, TORRENT_PORT))
        self.actions = {}
        
    def receive_wrapper(self) -> None:
        '''
        placeholder
        '''

        while True:
            try:
                res = self.recv(BUFSIZ)
                
                if not res:
                    print('server has disconnected') 
                    break 
                
                res_loaded = pickle.loads(res)
                
                if res_loaded[0] in self.actions.keys():
                    command = self.actions[res_loaded[0]]
                    del self.actions[res_loaded[0]]
                    self.execute_command(command, res_loaded[1])                
                
                if type(res_loaded[0]) == str and res_loaded[0] == '/peerinfo':
                    # get the UUID    
                    with open('settings.json','r') as f: 
                        settings = json.load(f)
                    
                    msg_return = ' '.join(('!peerinfo', str(TCP_PORT), settings['UUID']))
                    self.send(msg_return.encode())
                    
                if type(res_loaded[0]) == str and res_loaded[0] == '/received_update':
                    self.received_update = True

            # In case of connection error, disconnect the client
            except (ConnectionResetError, Exception) as e:
                self.close()
                print('server has closed, closing socket...')


    def send_command(self, command: str) -> None:
        '''
        placeholder
    
        '''
        if not command:
            print('command cannot be empty')
            return
            
        num_of_action = len(self.actions)
        self.actions[str(num_of_action)] = command
        self.send(' '.join((command,str(num_of_action))).encode())

    def update_torrent_server(self, update: bytes) -> None:
        '''
        placeholder
        '''
        self.send(update)

    def execute_command(self, command: str, other : list) -> None:
        '''
        Process a command received from the client.

        '''
        parts = command.split(' ')
        msg_return = ''

        if parts[0] == '/upload':
            if os.path.exists(parts[1]):
                self.upload_file_to_network(other, parts[1],parts[-1]) # type: ignore
            else:
                print('error: path does not exist')
                return 
            
        elif parts[0] == '/download':
            self.download_file((other[0],other[1]),other[2],parts[1])
        elif parts[0] == '/disconnect':
            pass
        elif parts[0] == '/upload_complete':
            pass
        elif parts[0] == '/download_complete':
            pass

    def upload_file_to_network(self, peers_info: dict, file_path: str, raid_level_option : str) -> None:
        '''
        divides the file and uploads it to the peers that are in the provided list. 
        updates the torrent server about the upload.

        Args: 
            peers list[(str,int)]: ip and port pairs of the peers sockets 
            file_path (str): file path 

        Returns: 
            None.
        '''
        if raid_level_option == 'high':
            raid_level = 0
        elif raid_level_option == 'low':
            raid_level = len(peers_info[0])
        else: 
            raid_level = int(len(peers_info[0]) / 2)
        

        # get the file name from the file path
        file_name = Path(file_path).name.split('.')[0]
        
        peers = peers_info.keys()
        file_parts_paths = torrent_utils.package_computer_parts(
            file_name, file_path, len(peers), raid_level)

        # create socket connection with peers
        socket_peers = list()
        for peer in peers:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(peer)
                socket_peers.append(s)
            except ConnectionRefusedError:
                continue
            
        # create processesing pool and start sending the files
        with multiprocessing.pool.ThreadPool(processes=len(peers)) as pool:
            for file_status in pool.starmap(send_file, zip(file_parts_paths, socket_peers)):
                if file_status[0]:
                    print('updated server')
                    update_command = '!update'.encode() + pickle.dumps([file_status[1], peers_info[file_status[2].getpeername()]])
                    self.update_torrent_server(update_command)
                    
                    while True:
                        data = self.recv(BUFSIZ)
                        if pickle.loads(data)[0] == '/received_update':
                            break 
                                            
                else:
                    pass

        # close the peer sockets
        for peer in socket_peers:
            peer.close()

        # delete the temp dir storing the tar files
        shutil.rmtree(os.path.dirname(file_parts_paths[0][0]))

    def download_file( self, peer_info, parts, file_path : str) -> None:
        '''
        divides the file and uploads it to the peers that are in the provided list. 
        updates the torrent server about the upload.

        Args: 
            peers list[(str,int)]: ip and port pairs of the peers sockets 
            file_path (str): file path 

        Returns: 
            None.
        '''

        # get the file name from the file path
        file_name = file_path.split('.')[0]
        file_size =  len(parts.keys())    
        peers = peer_info[0].keys()
        selected_ids = {}
        socket_peers = {}
        used_ids = []
        
        for part_num, ids in parts.items():
            for id_ in ids:
                if id_ in peer_info[1] and id_ not in used_ids:
                    selected_ids[part_num] = id_
                    used_ids.append(id_)
                    break
            else:
                for id_ in ids:
                    if id_ in peer_info[1]:
                        selected_ids[part_num] = id_
                        continue
            if selected_ids.get(part_num,None) is None:
                print(f'No peers available for part {part_num}')
                return
                                        
        for id in selected_ids.values():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(peer_info[1][id])
            socket_peers[s.getpeername()] = s

        os.makedirs(file_name + '.download')
        # create processesing pool and start sending the files
        with multiprocessing.pool.ThreadPool(processes=len(peers)) as pool:
            for download_status in pool.starmap(download, [(selected_ids[str(i)],str(i),socket_peers,peer_info[1],file_name, i) for i in range(file_size)]):
                success = download_status[0]
                part = download_status[1]
                
                if success:       
                    print('finished', part)
                else:
                    print('failed', part)
                
        # close the peer sockets
        for peer in socket_peers.values():
            peer.close()
        print('finished downloading')
        
        with open(os.path.join(file_name + '.download', file_path),'wb') as file:
            for i in range(len(parts.keys())):
                with open(os.path.join(file_name + '.download', str(i)),'rb') as part: 
                    file.write(part.read())
                    
                    
            


def download(selected_id: list, part: str, peers : dict, peer_info : dict, file_name, sleep_time : int) -> List[Union[bool, str]]:
    '''downloading a part from one of the peers socket provided'''
    peer = peers[peer_info[selected_id]]
    file_size = None
    file = open(os.path.join(file_name + '.download', part), 'wb')
    
    try: 
        msg = ' '.join(('/download',file_name,part))
        peer.send(msg.encode())
        data = peer.recv(BUFSIZ)
        file_size = int(data.decode()) 
        time.sleep(sleep_time)

        while file_size > 0:
            data = peer.recv(BUFSIZ)
            file_size = file_size - len(data)
            file.write(data)
            time.sleep(0.5)
        file.close()
        print('closed file', part)
        return [True,part]
                
    except (ConnectionRefusedError, ConnectionAbortedError) as e:
        file.close()
        return [False, part]
    

#  -> list[bool, str, socket.socket]
def send_file(file_parts_paths: str, peer: socket.socket):
    '''


    Returns:
        list[bool,str, socket.socket]:True if upload was successful false otherwise,  
                                        metadata of the file uploaded, and socket

    '''
    try:
        # get the file name and size to send the server
        file_path = file_parts_paths[0]
        file_name = Path(file_path).name.split('.')[0].split('-')[0]
        file_size = os.path.getsize(file_path)
        peer.send(f"/upload_part {file_name} {file_size}".encode())

        while True:
            status = peer.recv(BUFSIZ).decode()
            if status == '!OK':
                break
            else:
                return [False, file_parts_paths[1], peer] 
        # Open the file for reading
        with open(file_path, 'rb') as file:
            # Send file chunks until the entire file is sent
            while True:
                chunk = file.read(BUFSIZ)
                if not chunk:
                    break
                peer.send(chunk)
    except (ConnectionResetError) as e:
        return [False, file_parts_paths[1], peer]
    return [True, file_parts_paths[1], peer]


if __name__ == '__main__':
    if not os.path.exists(os.path.join(os.getcwd(),'settings.json')):
        setup.setup_peer()
    
    torrent_client = TorrentClient.server()
    peer_to_peer = PeerToPeer.server()

    while True:
        torrent_client.send_command(input().strip())
