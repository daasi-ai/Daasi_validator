import ssl
import json
import logging
import asyncio
import aiohttp
import aiofiles
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI, HTTPException

# Import files & folders
from validators.query.table_node_detail import *

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
HOST: str
PORT: int

app = FastAPI()

async def load_cert_from_db(host):
    """Loads the certificate from the database based on the host."""
    try:

        node_detail = get_node_detail_by_ip(host)
        if node_detail is not None:
            return node_detail[8]
        else:
            return None
    except FileNotFoundError:
        logger.warning("db.json not found")
    except json.JSONDecodeError:
        logger.error("Error decoding db.json")
    logger.warning(f"No certificate found in db.json for {host}")
    return None

async def fetch_from_server(endpoint: str, method: str):
    """Fetches data from the server using the specified endpoint and method."""
    trusted_cert_pem = await load_cert_from_db(HOST)
    print("trusted_cert_pem...", trusted_cert_pem)
    if not trusted_cert_pem:
        logger.error(f"No trusted certificate found for {HOST}")
        return None

    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    try:
        cert = x509.load_pem_x509_certificate(trusted_cert_pem.encode())
        cert_der = cert.public_bytes(serialization.Encoding.DER)
        ssl_context.load_verify_locations(cadata=cert_der)
    except Exception as e:
        logger.error(f"Error loading certificate: {e}")
        return None

    url = f"https://{HOST}:{PORT}{endpoint}"
    headers = {"Host": HOST}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, url, ssl=ssl_context, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Request failed with status code: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error during request: {e}")
            return None

# @app.get("/fetch_token_usage/")
async def api_fetch_token_usage(host: str, port: int):
    """API endpoint to fetch token usage data."""
    global HOST
    global PORT
    
    HOST = host
    PORT = port
    logger.info(f"::HOST:: {HOST}")
    logger.info(f"::PORT:: {PORT}")
    result = await fetch_from_server("/fetch_token_usage/", "GET")
    if result:
        return result
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch token usage data")