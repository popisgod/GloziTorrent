# Import necessary modules and functions
import random
import tarfile
import io
import json
import tempfile
import os
import pathlib

# --- file transportation --- 

def divide_into_parts(file_path: str, N: int) -> list[(int,bin)]:
    '''
    divides the file into equal binary parts 

    Args:
        N (int): Number of computers in the network 
        file_path (str): file path

    Returns: 
        list[bin]: a list with the divided file in binary format 

    '''
    with open(file_path, 'rb') as file:
        file_data = file.read()
    
    # calculate chuck size
    chunk_size = len(file_data) // N
    # divide data into chunks
    chunks = []
    for i in range(N):
        chunk = file_data[i*chunk_size:(i+1)*chunk_size]
        if i == N - 1:
            chunk = file_data[i*chunk_size:]

        chunks.append((i, chunk))

    return chunks


def divide_to_computers(file_path: str, N: int, M: int) -> list[list[(int,bin)]]:
    '''
    divides the parts into differnt computers and adds redundant parts for backup

    Args:
        M (int): Number of max failed computers in the network 
        N (int): Number of computers in the network 
        file_path (str): file path

    Returns: 
        list[list[bin]]: a combination list with parts for each computer in the network 


    '''
    # create data chunks
    chunks = divide_into_parts(file_path, N)
    redundancy_factor = N - M + 1

    # seperate the chunks into different computers and create redundant parts
    computer_parts = []
    for i in range(N):
        combination = []
        for j in range(redundancy_factor):
            combination.append(chunks[(j + i) % N])
        computer_parts.append(combination)

    return computer_parts


def package_computer_parts(file_name: str, file_path: str, N: int, M: int) -> list[str, dict]:
    '''
    packages the computer parts in a tar file for transporting 

    Args:
        M (int): Number of max failed computers in the network 
        N (int): Number of computers in the network 
        file_path (str): file path
        file_name (str): file name 

    Returns: 
        list[str, dict]: pairs of path and metadata of the tar files created 

    '''
    

    # seperate the file into different parts and create a temp directory for later storage
    computer_parts = divide_to_computers(file_path, N, M)
    temp_dir = tempfile.mkdtemp()

    paths_and_metadatas = []

    for i, computer in enumerate(computer_parts):

        # create a computer dict
        computer_dict = {i[0]: i[1] for i in computer}

        # create a hash for each part
        parts_hash = {i: generate_random_hash()
                      for i in map(lambda x: x[0], computer)}

        # create a dict to store metadata about the file parts
        metadata = {"file_name": file_name, "file_extension": file_path.split(
            '.')[-1],  "file_size": N, "parts": parts_hash}

        # store file name hashs and data
        files = [(''.join((hash, '.bin')), computer_dict[part])
                 for part, hash in metadata['parts'].items()]

        # store the metadata
        files.append(('metadata.json', json.dumps(metadata).encode()))

        # create the name of the tar file
        tar_name = ''.join((file_name,'-', str(i)))

        path_and_metadata = (os.path.join(temp_dir, tar_name), json.dumps(metadata))
        paths_and_metadatas.append(path_and_metadata)
        
        create_tar_file(files, os.path.join(temp_dir, tar_name))

    return paths_and_metadatas

def create_tar_file(file_data: list[str], output_path: str):
    '''
    packages files into a tar file

    Args:
        output_path (str): path where the tar file is stored 
        file_data (list): a list of file name and content pairs 


    Returns: 
        str: a path of the temp directory storing the file parts in a tar format 

    '''
    with tarfile.open(output_path, 'w') as tar:
        for file_name, file_content in file_data:
            tar_info = tarfile.TarInfo(name=file_name)
            file_content_bytes = file_content  # Convert string to bytes if needed
            tar_info.size = len(file_content_bytes)

            # Add the file to the TAR archive using the file content as a file-like object
            tar.addfile(tar_info, fileobj=io.BytesIO(file_content_bytes))


def extract_tar_file(tar_file_path: str, extract_dir: str):
    # extracts the files out of the tar file
    with tarfile.open(tar_file_path, 'r') as tar:
        tar.extractall(path=extract_dir)


def generate_random_hash():
    # Generate a random 128-bit hash as a hex string
    hash_value = format(random.getrandbits(128), '032x')

    return hash_value


def connect_file(chunks: list[bin]):
    '''

    '''


if __name__ == '__main__':
    pass
