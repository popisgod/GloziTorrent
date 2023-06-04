import logging

# Crypt 
SECRET_KEY ="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600


# logging configuration 
logging.basicConfig(filename='tracker.log', level=logging.INFO, filemode='w', format='%(asctime)s - %(message)s',datefmt='%d-%b-%y %H:%M:%S')
