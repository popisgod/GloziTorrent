import re
import logging
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Annotated, List, Dict, Callable
from classy_fastapi import Routable, get, post
from trackerAPI_dependencies.tracker_dao import TrackerDao, Peer, TrackerFile, ActiveUser, AdminUser
from pymongo import MongoClient
from starlette.authentication import requires
from starlette.authentication import AuthCredentials, AuthenticationError
from starlette.requests import HTTPConnection
from starlette.middleware.authentication import AuthenticationMiddleware


# logging configuration 
logging.basicConfig(filename='tracker.log', 
                    level=logging.INFO, 
                    filemode='w', 
                    format='%(asctime)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')


class TrackerWEB(Routable):
    pass