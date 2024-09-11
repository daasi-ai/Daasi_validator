import aiohttp
import asyncio
import json
import logging
import os
import requests
from requests.exceptions import RequestException
from collections import defaultdict
import torch
from colorama import Fore, Style, init
import bittensor as bt
from abc import ABC, abstractmethod
from template.protocol import *
from ssl_pinning_client import api_fetch_token_usage
from sqLite import *
from validators.query.table_miner_data import *
from validators.query.table_node_detail import *
from validators.query.table_normalized_score import *
from time import sleep

node_info_usage_detail = {}

init()

# Create a logger
logger = logging.getLogger('colorful_logger')
logger.setLevel(logging.DEBUG)

# Create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Define the log format
log_format = "%(asctime)s |     %(levelname)s     | %(message)s"
log_formats = {
    logging.DEBUG: Fore.BLUE + log_format + Style.RESET_ALL,
    logging.INFO: Fore.GREEN + log_format + Style.RESET_ALL,
    logging.WARNING: Fore.YELLOW + log_format + Style.RESET_ALL,
    logging.ERROR: Fore.RED + log_format + Style.RESET_ALL,
    logging.CRITICAL: Fore.RED + Style.BRIGHT + log_format + Style.RESET_ALL
}

# Create a custom formatter
class ColorFormatter(logging.Formatter):
    def format(self, record):
        log_fmt = log_formats.get(record.levelno, log_format)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Add the custom formatter to the console handler
ch.setFormatter(ColorFormatter())

# Add the console handler to the logger
logger.addHandler(ch)

node_detail = {}
miner_data = {}
normalized_score = []

class BaseValidator(ABC):
    def __init__(self, dendrite, config, subtensor, wallet, timeout=5, db_path='/home/ubuntu/verifier/db.json'):
        bt.logging.info("BaseValidator initialized.")
        self.dendrite = dendrite
        self.config = config
        self.subtensor = subtensor
        self.wallet = wallet
        self.timeout = timeout
        self.streaming = False
        self.metagraph = subtensor.metagraph(config.netuid)
        self.db_path = db_path

class Validator(BaseValidator):
    def __init__(self, dendrite=None, config=None, subtensor=None, wallet=None):
        super().__init__(dendrite, config, subtensor, wallet, timeout=5)
        
        # Define the version of the template module.
        __version__ = "1.4.1"
        version_split = __version__.split(".")
        self.__version_as_int__ = (100 * int(version_split[0])) + (10 * int(version_split[1])) + (1 * int(version_split[2]))
        bt.logging.info("GroupChat Validator initialized.")

    async def query_miner(self, metagraph, miner_uid, syn, timeout=5):
        try:
            if not (0 <= miner_uid < len(metagraph.hotkeys)):
                bt.logging.error("Invalid miner UID or no miner available to query.")
                return {"status": None, 'error': "Invalid miner UID or no miner available to query."}
            bt.logging.info(f"Querying miner {miner_uid} with {syn}")
            response = await self.dendrite([metagraph.axons[miner_uid]], syn, deserialize=False, timeout=timeout)
            return response
        except Exception as e:
            bt.logging.error(f"Error in query_miner: {e}")
            return {"status": None, 'error': str(e)}

    def get_valid_miners_info(self):
        return [int(uid) for uid in self.metagraph.uids]

    def set_weights(self, score, miner_id):
        try:
            if score < 0:
                score = 0
            score_tensor = torch.tensor([score])  # Wrap score in a list
            logger.info("score_tensor: %s", score_tensor)
            weights: torch.FloatTensor = torch.nn.functional.normalize(score_tensor, p=1.0, dim=0).float()
            logger.info("weight: %s", weights)
            bt.logging.info(f"🏋️ Weight of miners : {weights.tolist()}")
            result = self.subtensor.set_weights(
                wallet=self.wallet,
                netuid=self.config.netuid,
                uids=[miner_id],
                weights=weights,
                wait_for_inclusion=False,
                wait_for_finalization=False,
                version_key=self.__version_as_int__
            )

            if result[0]['code'] == 0:
                bt.logging.success("✅ Successfully set weights.")
            else:
                bt.logging.error(f"❌ Failed to set weights. Error: {result[0]['message']}")
        except Exception as e:
            bt.logging.error(f"An error occurred while setting weights: {e}")

    async def calculate_miners_scores_v2(self):
        try:
            miner_data = miner_data_get_all()
            logger.info("Request initiated to normalize node score")

            if len(miner_data) > 0:
                score_result = self.normalize_scores(miner_data)
                print("score_result...", score_result)
                for score in score_result:
                    insert_data_in_normalized_score(score)
                logger.info("Normalized score saved successfully...")
            
            normalized_score = get_all_data_from_normalized_score()
            logger.info("Normalized score result obtained successfully")
            for score in normalized_score:
                id, miner_id, miner_score, rank = score
                logger.info(f"Sending score to the respective miner: {miner_score}")
                
                miner_node_detail = {'score': miner_score, 'rank': rank, 'Validator_name': 'Validator-1.0'}
                syn = SendMinerScore(details=miner_node_detail)
                await self.query_miner(self.metagraph, miner_id, syn) 
                logger.info(f"Setting weight for miner {miner_id}")
                self.set_weights(miner_score, miner_id)

            # miner_data = {}

        except Exception as e:
            logger.error(f"Error in calculate_miners_scores_v2: {e}")
            return False

    async def fetch_score_and_resources_from_node(self, node_info):
        try:
            logger.info("Request initiated to fetch node score.")
            await self.get_node_score(node_info)
        except Exception as e:
            logger.error(f"Error in fetch_score_and_resources_from_node: {e}")
            return False

    async def get_nodes_ip_and_status(self):
        try:
            logger.info("Request initiated to get nodes IP and status...")
            syn = GetNodeDetail()

            # miner_id = 69
            uids = self.get_valid_miners_info()
            # uids = [59]
            hotkeys = self.metagraph.hotkeys
            print("uids...", uids)
            for item in uids:
                # if item == miner_id:
                    nodes_list_res = (await self.query_miner(self.metagraph, item, syn))[0]
                    print("Node list res...", nodes_list_res)
                    print("fetching data for miner...", item)

                    retry_count = 0
                    while not nodes_list_res.response and retry_count < 1:
                        logger.info(f"Retrying query for miner {item}")
                        nodes_list_res = (await self.query_miner(self.metagraph, item, syn))[0]
                        retry_count += 1
                    
                    if nodes_list_res.response:
                        index = uids.index(item)
                        hotkey = hotkeys[index]
                        await self.create_node_detail(nodes_list_res.response, item, hotkey)
                        
                    else:
                        logger.warning(f"Failed to get response from miner {item} after retry")
                        index = uids.index(item)
                        hotkey = hotkeys[index]
                        node_detail = {
                                    "ip": None,             # TEXT
                                    "name": None,           # TEXT
                                    "status": None,         # TEXT
                                    "hotkey": None,         # TEXT
                                    "certificate": None,    # TEXT
                                    "usage_port": 0,        # INTEGER
                                    "port": 0,              # INTEGER
                        }
                        
                        node_value = {item: [node_detail]}
                        upsert_data_in_node_detail(item, node_value) 
            
            node_info = get_all_data_in_node_detail()
            print("node_info...", node_info)

            await self.fetch_score_and_resources_from_node(node_info)
            await self.calculate_miners_scores_v2()
            logger.info("Node Details fetched successfully")
            return {"message": 'Node details fetched successfully', "success": True, "status": 200}
        except Exception as e:
            logger.error(f"Error in get_nodes_ip_and_status: {e}")
            return False

    # def normalize_scores(self, miner_data):
    #     base_scores = {}
    #     error_rates = {}
    #     adjusted_scores = {}

    #     for data in miner_data:
    #         id, miner_id, cpu_score, ram_score, disk_score, openai_tokens, groq_tokens, claude_tokens, gemini_tokens, total_requests, zero_value_entries = data
    #         base_score = (
    #                 cpu_score * 0.1 + 
    #                 ram_score * 0.05 + 
    #                 disk_score * 0.05 +
    #                 groq_tokens * 0.25 + 
    #                 openai_tokens * 0.15 + 
    #                 claude_tokens * 0.15 + 
    #                 gemini_tokens * 0.25
    #         )
    #         base_scores[miner_id] = base_score

    #         error_rate = zero_value_entries / total_requests if total_requests > 0 else 0
    #         error_rates[miner_id] = error_rate

    #     adjusted_scores = self.calculate_adjustment(base_scores, error_rates)
    #     total_score = sum(adjusted_scores.values())
    #     normalized_scores = {miner_id: score/total_score for miner_id, score in adjusted_scores.items()}

    #     final_results = [(miner_id, score) for miner_id, score in normalized_scores.items()]
    #     final_results.sort(key=lambda x: x[1], reverse=True)
    #     ranked_results = [(miner_id, score, rank + 1) for rank, (miner_id, score) in enumerate(final_results)]

    #     return ranked_results
    
    def normalize_scores(self, miner_data):
        base_scores = {}
        error_rates = {}
        adjusted_scores = {}

        for data in miner_data:
            # Unpack values and handle None values by replacing them with 0
            id, miner_id, cpu_score, ram_score, disk_score, openai_tokens, groq_tokens, claude_tokens, gemini_tokens, total_requests, zero_value_entries = data

            cpu_score = cpu_score if cpu_score is not None else 0
            ram_score = ram_score if ram_score is not None else 0
            disk_score = disk_score if disk_score is not None else 0
            openai_tokens = openai_tokens if openai_tokens is not None else 0
            groq_tokens = groq_tokens if groq_tokens is not None else 0
            claude_tokens = claude_tokens if claude_tokens is not None else 0
            gemini_tokens = gemini_tokens if gemini_tokens is not None else 0
            total_requests = total_requests if total_requests is not None else 0
            zero_value_entries = zero_value_entries if zero_value_entries is not None else 0

            # Base score calculation
            base_score = (
                cpu_score * 0.1 + 
                ram_score * 0.05 + 
                disk_score * 0.05 +
                groq_tokens * 0.25 + 
                openai_tokens * 0.15 + 
                claude_tokens * 0.15 + 
                gemini_tokens * 0.25
            )
            base_scores[miner_id] = base_score

            # Error rate calculation
            error_rate = zero_value_entries / total_requests if total_requests > 0 else 0
            error_rates[miner_id] = error_rate

        # Adjust the scores using the provided method
        adjusted_scores = self.calculate_adjustment(base_scores, error_rates)

        # Normalize the adjusted scores
        total_score = sum(adjusted_scores.values())
        normalized_scores = {miner_id: score / total_score for miner_id, score in adjusted_scores.items() if total_score > 0}

        # Rank the results
        final_results = [(miner_id, score) for miner_id, score in normalized_scores.items()]
        final_results.sort(key=lambda x: x[1], reverse=True)
        ranked_results = [(miner_id, score, rank + 1) for rank, (miner_id, score) in enumerate(final_results)]

        return ranked_results

    async def create_node_detail(self, nodes, miner_uid, hotkey):
        try:
            for item in nodes:
                item['miner_id'] = miner_uid
                item['hotkey'] = hotkey

                single_node_detail = {miner_uid: [item]}
                miner_detail_exist = get_data_in_node_detail(item['miner_id'], item['ip'])
                # print("Miner detail exist...", miner_detail_exist)
                # print("URL to get attestation...", f"http://{item['ip']}:{item['port']}/report")
                ip_res = self.make_get_request(f"http://{item['ip']}:{item['port']}/report")
                if ip_res is not None:
                    send_report_res = self.send_report(ip_res)
                    print("send report res....", send_report_res)
                    
                    if send_report_res[0] is None:
                        miner_node_detail = {'Validator_name': 'Validator-1.0', 'message':f'Attestation report failed for ip: {item["ip"]}'}
                        syn = SendMinerScore(details=miner_node_detail)
                        await self.query_miner(self.metagraph, miner_uid, syn)
                        return    
                    verifier_data = self.get_verifier_data(item['ip']) # This method fetch the certificate from verifier
                else:
                    miner_node_detail = {'Validator_name': 'Validator-1.0', 'message':f'Server response failed for ip: {item["ip"]}'}
                    syn = SendMinerScore(details=miner_node_detail)
                    await self.query_miner(self.metagraph, miner_uid, syn)
                    return

                if miner_detail_exist is None and send_report_res[0] == 200:

                    single_node_detail[miner_uid][0]['certificate'] = verifier_data['cert']
                    upsert_data_in_node_detail(miner_uid, single_node_detail)
                    
                elif miner_detail_exist is not None and send_report_res[0] == 200:
                    print("miner_detail_exist...", miner_detail_exist)
                    # id, name, status, ip, miner_id, hotkey, certificate = miner_detail_exist
                    id, name, status, ip, port, usage_port, miner_id, hotkey, certificate = miner_detail_exist
                    if certificate == verifier_data['cert']:
                        print("Certificate is same...")
                        continue
                    else:
                        print("Certificate is not same...")
                        update_certificate_in_node_detail(miner_id, ip, verifier_data['cert'])
                else:
                    print("Verifier or attestation report Failed...")
                    verifier_data = { "cert": None }  
                    update_certificate_in_node_detail(miner_id, ip, verifier_data['cert'])
                    continue
            res = get_all_data_in_node_detail()
            return res
        except Exception as e:
            logger.error(f"Error in create_node_detail: {e}")
            return False

    def find_details_by_miner_id(self, miner_id):
        return node_detail.get(miner_id)

    def update_score_of_miner(self, node_info, miner_id):
        miner_node_score = miner_data[miner_id]

        cpu_score = node_info['benchmark_data']['CPU']['CPU Score']
        ram_score = node_info['benchmark_data']['RAM']['RAM Score']
        disk_score = node_info['benchmark_data']['Disk']['Disk Score']
        open_ai = node_info['usage_summary']['openai']['total_tokens_last_12_hours']
        groq = node_info['usage_summary']['groq']['total_tokens_last_12_hours']
        claud = node_info['usage_summary']['gemini']['total_tokens_last_12_hours']
        gemini = node_info['usage_summary']['claude']['total_tokens_last_12_hours']

        update_ram_score = miner_node_score[2] + ram_score
        update_cpu_score = miner_node_score[1] + cpu_score
        update_disk_score = miner_node_score[3] + disk_score
        update_openai_score = miner_node_score[4] + open_ai
        update_groq_score = miner_node_score[5] + groq
        update_claud_score = miner_node_score[6] + claud
        update_gemini_score = miner_node_score[7] + gemini

        miner_data[miner_id] = (miner_id, update_cpu_score, update_ram_score, update_disk_score, update_openai_score, update_groq_score, update_claud_score, update_gemini_score)

    def miner_id_exists(self, data, mid):
        return mid in data

    def get_data_by_miner_id(self, miner_id):
        return miner_data.get(miner_id)

    def remove_tupple_score(miner_id):
        global normalized_score
        normalized_score = [t for t in normalized_score if t[0] != miner_id]

    async def fetch_node_score(self, session, url):
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.info(f"Attempt {attempt} failed with status code {response.status}. Retrying...")
                        if attempt < attempts:
                            await asyncio.sleep(2)
            except Exception as e:
                logger.info(f"Attempt {attempt} failed with error: {e}. Retrying...")
                if attempt < attempts:
                    await asyncio.sleep(2)
        logger.info("** Error in fetch_node_score **: Max retries reached. Exiting.")
        return None

    async def process_node(self, item, session):
        print("Node processing is in progress...")
        
        uuid, name, status, ip, port, usage_port, miner_id, hotkey, certificate = item
        print("Ip...", ip)
        print("Port...", port)
        # host = url.split("//")[1].split(":")[0]
        # port = url.split("//")[1].split(":")[1]
        retries = 3

        if ip is not None and usage_port is not 0: 
            for attempt in range(retries):
                try:
                    node_info = await api_fetch_token_usage(ip, usage_port)
                    print("node_info...", node_info)
                    
                    if node_info:
                        if 'hotkey' in node_info and node_info['hotkey'] != hotkey:
                            node_info = None
                            miner_node_detail = {'Validator_name': 'Validator-1.0', 'message':f'node {ip} hotkey mismatch'}
                            syn = SendMinerScore(details=miner_node_detail)
                            await self.query_miner(self.metagraph, miner_id, syn) 
                            return
                        else:
                            break
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(2)  # Wait for 2 seconds before retrying
            else:
                logger.error(f"Failed to fetch token usage after {retries} attempts")
                node_info = None
        else:
            node_info = None

        if node_info is not None:
            node_detail = {
                "miner_id": miner_id,
                "ip": ip,
                "hotkey": hotkey,
                "usage_summary": node_info['usage_summary'],
            }
            self.save_node_info_detail(node_detail)

        if node_info is not None:
            print("Calculating node info...")
            existing_miner_data = miner_data_get_one(miner_id)
            print("existing_miner_data...", existing_miner_data)
            print("miner_id...",   miner_id)
            if existing_miner_data:
                id, miner_id, cpu_score, ram_score, disk_score, openai_tokens, groq_tokens, claude_tokens, gemini_tokens, total_requests, zero_value_entries = existing_miner_data[0]
                print("id...", id)
                print("miner_id...", miner_id)
                print("cpu_score...", cpu_score)
                print("ram_score...", ram_score)
                print("disk_score...", disk_score)
                print("openai_tokens...", openai_tokens)
                print("groq_tokens...", groq_tokens)
                print("claude_tokens...", claude_tokens)
                print("gemini_tokens...", gemini_tokens)
                print("total_requests...", total_requests)
                print("zero_value_entries...", zero_value_entries)

                cpu_score += node_info['benchmark_data']['CPU']['CPU Score']
                ram_score += node_info['benchmark_data']['RAM']['RAM Score']
                disk_score += node_info['benchmark_data']['Disk']['Disk Score']

                openai_tokens += node_info['usage_summary']['openai']['total_tokens_last_24_hours']
                groq_tokens += node_info['usage_summary']['groq']['total_tokens_last_24_hours']
                claude_tokens += node_info['usage_summary']['claude']['total_tokens_last_24_hours']
                gemini_tokens += node_info['usage_summary']['gemini']['total_tokens_last_24_hours']

                total_requests += sum(api['total_requests_last_24_hours'] for api in node_info['usage_summary'].values())
                zero_value_entries += sum(api['zero_value_entries_last_24_hours'] for api in node_info['usage_summary'].values())

                miner_data[miner_id] = (miner_id, cpu_score, ram_score, disk_score, openai_tokens, groq_tokens, claude_tokens, gemini_tokens, total_requests, zero_value_entries)
                print("Accumlated sum of miner data...", miner_data[miner_id])
                miner_score_res = insert_data_in_miner_data(miner_id, miner_data[miner_id])
                logger.info(f"Miner score res: {miner_score_res}")
            else: 
                # id, miner_id, cpu_score, ram_score, disk_score, openai_tokens, groq_tokens, claude_tokens, gemini_tokens, total_requests, zero_value_entries = existing_miner_data
                cpu_score = node_info['benchmark_data']['CPU']['CPU Score']
                ram_score = node_info['benchmark_data']['RAM']['RAM Score']
                disk_score = node_info['benchmark_data']['Disk']['Disk Score']

                openai_tokens = node_info['usage_summary']['openai']['total_tokens_last_24_hours']
                groq_tokens = node_info['usage_summary']['groq']['total_tokens_last_24_hours']
                claude_tokens = node_info['usage_summary']['claude']['total_tokens_last_24_hours']
                gemini_tokens = node_info['usage_summary']['gemini']['total_tokens_last_24_hours']

                total_requests = sum(api['total_requests_last_24_hours'] for api in node_info['usage_summary'].values())
                zero_value_entries = sum(api['zero_value_entries_last_24_hours'] for api in node_info['usage_summary'].values())

                miner_data[miner_id] = (miner_id, cpu_score, ram_score, disk_score, openai_tokens, groq_tokens, claude_tokens, gemini_tokens, total_requests, zero_value_entries)
                miner_score_res = insert_data_in_miner_data(miner_id, miner_data[miner_id])
                logger.info(f"Miner score res: {miner_score_res}")
        else:

            print("Sending failed score to miner...")
            miner_node_detail = {'Validator_name': 'Validator-1.0', 'message':'Server response failed'}
            syn = SendMinerScore(details=miner_node_detail)
            await self.query_miner(self.metagraph, miner_id, syn) 


    async def get_node_score(self, node_info):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for item in node_info:
                print("Item...", item)
                tasks.append(self.process_node(item, session))
                if len(tasks) >= 20:
                    await asyncio.gather(*tasks)
                    tasks = []
            if tasks:
                await asyncio.gather(*tasks)

    def update_normalized_score(self, final_result):
        global normalized_score
        for new_tuple in final_result:
            miner_id = new_tuple[0]
            exists = False
            for i, old_tuple in enumerate(normalized_score):
                if old_tuple[0] == miner_id:
                    normalized_score[i] = new_tuple
                    exists = True
                    break
            if not exists:
                normalized_score.append(new_tuple)
                insert_data_in_normalized_score(new_tuple[0], str(new_tuple))


    def make_get_request(self, url, params=None, max_retries=3, retry_delay=2):
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params)

                if response.status_code == 200:
                    return response.json()
                else:
                    logging.warning(f"Request failed with status code {response.status_code} (Attempt {attempt + 1}/{max_retries})")

            except RequestException as e:
                logging.error(f"Request error occurred: {e} (Attempt {attempt + 1}/{max_retries})")

            if attempt < max_retries - 1:
                logging.info(f"Retrying in {retry_delay} seconds...")
                sleep(retry_delay)

        logging.error(f"Request failed after {max_retries} attempts")
        return None

    def send_report(self, ip_res, max_retries=3, retry_delay=2):
        url = "http://localhost:8080/report"
        headers = {"Content-Type": "application/json"}

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=ip_res)
                response.raise_for_status()
                return response.status_code, response.text
            except RequestException as e:
                logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    sleep(retry_delay)

        logger.error(f"Request failed after {max_retries} attempts")
        return None, None   

    def calculate_adjustment(self, base_scores, error_rates):
        adjusted_scores = {}
        max_error_rate = max(error_rates.values())

        for miner_id, base_score in base_scores.items():
            error_rate = error_rates[miner_id]

            if error_rate > 0.1:
                adjustment = 1 - (error_rate - 0.1) * 2
            elif 0.02 <= error_rate <= 0.1:
                adjustment = 1
            else:
                if max_error_rate > 0.1:
                    adjustment = 1 + (0.02 - error_rate) / 0.02 * 0.1
                else:
                    adjustment = 1

            adjusted_score = base_score * adjustment

            if max_error_rate > 0:
                relative_error = error_rate / max_error_rate
                adjusted_score *= (1 + (0.5 - relative_error))

            adjusted_scores[miner_id] = adjusted_score

        return adjusted_scores

    def get_node_list(self):
        logger.info("Request made to fetch node details and calculate score per miner")
        try:
            response = node_detail
            return response
        except Exception as e:
            print(f"An error occurred: {e}")
            
    def save_node_info_detail(self, node_detail):
        try:
            global node_info_usage_detail
            miner_id = node_detail['miner_id']
            node_ip = node_detail['ip']

            if miner_id in node_info_usage_detail:
                existing_ips = [node['node_ip'] for node in node_info_usage_detail[miner_id]['node_details']]
                print("**-- existing_ips --**", existing_ips)
                if node_ip in existing_ips:
                    node_info_usage_detail[miner_id]['node_details'].append(
                        {
                            "node_ip": node_detail['ip'],
                            "hotkey": node_detail['hotkey'],
                            "usage_summary": node_detail['usage_summary'],
                        }
                    )
            else:
                node_info_usage_detail[miner_id] = {
                    "node_details": [
                        {
                            "node_ip": node_detail['ip'],
                            "hotkey": node_detail['hotkey'],
                            "usage_summary": node_detail['usage_summary'],
                        }
                    ]
                }
                return True
            return True
        except Exception as e:
            logger.error(f"Error in save_node_info_detail: {e}")
            return False
        
    def get_node_info_usage_detail(self):
        try:
            return node_info_usage_detail
        except Exception as e:
            logger.error(f"Error in get_node_info_usage_detail: {e}")
            return False

    def get_verifier_data(self, search_ip):
        try:
            print(f"Searching for IP: {search_ip}")
            
            with open(self.db_path, 'r') as file:
                content = file.read()
            
            # Split the content into individual JSON objects
            json_objects = content.replace('}{', '}\n{').split('\n')
            
            # Parse each JSON object and store in a list
            data = []
            matching_object = None
            for obj in json_objects:
                try:
                    parsed_obj = json.loads(obj)
                    if parsed_obj['ip'] == search_ip:
                        matching_object = parsed_obj
                        print(f"Found matching IP. Certificate:\n{matching_object['cert']}")
                    else:
                        data.append(parsed_obj)
                except json.JSONDecodeError as json_err:
                    logger.warning(f"Error parsing JSON object: {json_err}")
                    logger.warning(f"Problematic JSON: {obj}")
            
            if matching_object:
                # Write the updated data back to the file
                with open(self.db_path, 'w') as file:
                    for item in data:
                        json.dump(item, file)
                        file.write('\n')
                print(f"Object with IP {search_ip} has been deleted from db.json")
                return matching_object
            else:
                print(f"No matching IP found for {search_ip}")
                return None
        except Exception as e:
            logger.error(f"Error in get_verifier_data: {str(e)}")
            return False