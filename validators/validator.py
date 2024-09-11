import ssl
import json
import logging
import asyncio
import argparse
from pathlib import Path
from typing import List, Tuple

import aiohttp
import aiofiles
from aiohttp import web
from aiohttp.web_response import Response
import bittensor as bt

from validators.base_validator import BaseValidator, Validator, logger
from sqLite import *
from envparse import env

# Initialize the SQLite database table
create_node_detail_table()

group_chat_vali = None
metagraph = None

def get_config() -> bt.config:
    """Gets and sets the configuration for the application."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--netuid", type=int, default=77)
    parser.add_argument('--http_port', type=int, default=8090)
    bt.subtensor.add_args(parser)
    bt.logging.add_args(parser)
    bt.wallet.add_args(parser)
    config = bt.config(parser)
    _args = parser.parse_args()
    full_path = Path(
        f"{config.logging.logging_dir}/{config.wallet.name}/{config.wallet.hotkey}/netuid{config.netuid}/validator"
    ).expanduser()
    config.full_path = str(full_path)
    full_path.mkdir(parents=True, exist_ok=True)
    return config

def initialize_components(config: bt.config):
    """Initializes core components like wallet, subtensor, and dendrite."""
    global metagraph
    bt.logging(config=config, logging_dir=config.full_path)
    bt.logging.info(f"Running validator for subnet: {config.netuid} on network: {config.subtensor.chain_endpoint}")
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(config.netuid)
    dendrite = bt.dendrite(wallet=wallet)
    my_uid = metagraph.hotkeys.index(wallet.hotkey.ss58_address)
    if wallet.hotkey.ss58_address not in metagraph.hotkeys:
        bt.logging.error(
            f"Your validator: {wallet} is not registered to chain connection: "
            f"{subtensor}. Run btcli register --netuid 77 and try again."
        )
        sys.exit()

    return wallet, subtensor, dendrite, my_uid

def initialize_validators(vali_config, test=False):
    """Initializes the validators based on the provided configuration."""
    print(f"✅ ::initialize_validators::")
    global group_chat_vali
    try:
        group_chat_vali = Validator(**vali_config)
        print(f"✅ :: Validator validation initialization Done::")
    except Exception as e:
        print(f"❌ Failed to initialize group chat validator: {e}")
        group_chat_vali = None
    print("initialized_validators")

async def calculate_score(request: web.Request) -> Response:
    """Endpoint to calculate the score for miners."""
    try:
        await group_chat_vali.calculate_miners_scores_v2()
        return web.Response(status=200, text="Score calculation successful")
    except Exception as e:
        logger.error(f"Error in calculate_score: {e}")
        return web.Response(status=500, text="Internal error")

async def get_node_score_and_resource(request: web.Request) -> Response:
    """Endpoint to fetch node score and resources."""
    try:
        res = await group_chat_vali.fetch_node_score_and_resources()
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in get_node_score_and_resource: {e}")
        return web.Response(status=500, text="Internal error")

async def get_score_from_node(request: web.Request) -> Response:
    """Endpoint to fetch score from node."""
    try:
        res = await group_chat_vali.fetch_score_and_resources_from_node()
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in get_score_from_node: {e}")
        return web.Response(status=500, text="Internal error")

async def get_node_detail(request: web.Request) -> Response:
    """Endpoint to fetch node details and calculate score."""
    try:
        logger.info("Request made to fetch node details and calculate score per miner")
        res = await group_chat_vali.get_nodes_ip_and_status()
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in get_node_detail: {e}")
        return web.Response(status=500, text="Internal error")

async def get_miner_data(request: web.Request) -> Response:
    """Endpoint to fetch miner data."""
    try:
        logger.info("Request made to fetch miner data")
        res = await group_chat_vali.get_miner_data()
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in get_miner_data: {e}")
        return web.Response(status=500, text="Internal error")

async def ssl_client(request: web.Request) -> Response:
    """Endpoint to initiate SSL client."""
    try:
        logger.info("Request made to fetch node details and calculate score per miner")
        res = group_chat_vali.ssl_pinning_client()
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in ssl_client: {e}")
        return web.Response(status=500, text="Internal error")

async def get_node_list_detail(request: web.Request) -> Response:
    """Endpoint to fetch the list of node details."""
    try:
        logger.info("Request made to fetch node details list")
        res = group_chat_vali.get_node_list()
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in get_node_list_detail: {e}")
        return web.Response(status=500, text="Internal error")

async def get_node_list_system_usage(request: web.Request) -> Response:
    """Endpoint to fetch node usage details."""
    try:
        logger.info("Request made to fetch node usage details")
        res = group_chat_vali.get_node_info_usage_detail()
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in get_node_list_system_usage: {e}")
        return web.Response(status=500, text="Internal error")

async def insert_dummy_data(request: web.Request) -> Response:
    """Endpoint to insert dummy data."""
    try:
        logger.info("Request made to insert dummy data")
        res = group_chat_vali.insert_dummy_data()
        return web.json_response(res)
    except Exception as e:
        logger.error(f"Error in insert_dummy_data: {e}")
        return web.Response(status=500, text="Internal error")

class ValidatorApplication:
    """Main application class for managing the validator routes."""
    def __init__(self, *args, **kwargs):
        self.app = web.Application(*args, **kwargs)

    def add_routes(self, routes: List[Tuple]):
        """Adds routes to the web application."""
        for route in routes:
            self.app.router.add_route(*route)

validator_app = ValidatorApplication()

# validator_app.add_routes([
#     ('GET', '/calculate_score', calculate_score),
#     ('GET', '/get-node-score', get_score_from_node),
#     ('GET', '/get-node-detail', get_node_detail),
#     ('GET', '/get-node-list', get_node_list_detail),
#     ('GET', '/get-node-usage', get_node_list_system_usage),
# ])

async def schedule_get_node_detail():
    """Function to schedule get_node_detail every 15 minutes."""
    while True:
        try:
            logger.info("Scheduled task: Fetching node details.")
            res = await group_chat_vali.get_nodes_ip_and_status()  # Assuming this is the method you want to call.
            logger.info(f"Node details fetched: {res}")
        except Exception as e:
            logger.error(f"Error in scheduled get_node_detail task: {e}")
        await asyncio.sleep(1/2 * 60)  # Sleep for 15 minutes (15 * 60 seconds)



def main(run_aio_app=True, test=False) -> None:
    """Main function to run the validator application."""
    config = get_config()
    wallet, subtensor, dendrite, my_uid = initialize_components(config)
    logger.info(f"my_uid: {my_uid}")
    validator_config_global = {
        "dendrite": dendrite,
        "config": config,
        "subtensor": subtensor,
        "wallet": wallet
    }
    logger.info(f"::Dendrite Info :: {validator_config_global['dendrite']}")
    logger.info(f"::Config :: {validator_config_global['config']}")
    logger.info(f"::Subtensor Info :: {validator_config_global['subtensor']}")
    logger.info(f"::Wallet Info :: {validator_config_global['wallet']}")

    initialize_validators(validator_config_global, test)
    logger.info("✅ Initialization of all validators has been completed.")
    
    loop = asyncio.get_event_loop()

    # Schedule the task to run every 15 minutes
    loop.create_task(schedule_get_node_detail())

    if run_aio_app:
        try:
            web.run_app(validator_app.app, port=config.http_port, loop=loop)
        except KeyboardInterrupt:
            bt.logging.info("Keyboard interrupt detected. Exiting validator.")

if __name__ == "__main__":
    main()

