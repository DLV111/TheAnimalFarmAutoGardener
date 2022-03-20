import os
import sys
import logging
import traceback
from settings import *
from animalfarm import *
from web3 import Web3
from utils import decimal_round, pancakeswap_api_get_price
from decimal import Decimal
import time
import random

VERSION = "1.0"

POOL_DICT = {}

TOTAL_WORTH = Decimal(0.0)

def main():
    global POOL_DICT
    os.system("clear")
    
    # Setup logger.
    log_format = '%(asctime)s: %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)
    logging.info('Honest Work v%s Started!' % VERSION)
    logging.info('----------------')
    logging.info('Strategy: %s.' % ACTION_LIST)
    
    client = AnimalFarmClient(
        PRIVATE_KEY, txn_timeout=TXN_TIMEOUT, gas_price=GAS_PRICE_IN_WEI, rpc_host=RPC_HOST)

    first_run = True

    while True:
        # handle the garden actions.
        secondsUntilNextPlant = handle_garden(client,first_run)

        first_run = False
        # take care of all the pools user is in! check settings.py
        #handle_pools(client)
        
        logging.info('----------------')
        logging.info('Total Value: $%s' % TOTAL_WORTH)
        logging.info('----------------')
        logging.info('%s for %s seconds' % (random.choice(FARMING_PHRASES),secondsUntilNextPlant+1))
        time.sleep(secondsUntilNextPlant+1)
        
def get_garden_data(garden, max_tries=1):
    for _ in range(max_tries):
        try:
            seed_count = garden.get_user_seeds(garden.address)
            plant_count = garden.get_my_plants()
            seeds_per_plant = garden.get_seeds_per_plant()
            seedsPerDay=plant_count*86400
            seedsPerSecond=seedsPerDay/24/60/60
            secondsUntilNextPlant=round((seeds_per_plant-(seed_count%seeds_per_plant))/seedsPerSecond)
            if seed_count >= seeds_per_plant:
                new_plants = seed_count // seeds_per_plant
            else:
                new_plants = 0
            unclaimed_lp = decimal_round(garden.get_user_lp(seed_count), 4)
            drip_busd_lp = garden.get_drip_busd_lp_price()
            if drip_busd_lp is None:
                time.sleep(30)
                continue
            unclaimed_worth = drip_busd_lp["price"] * unclaimed_lp
            return {
                'secondsUntilNextPlant' : secondsUntilNextPlant,
                'seeds': seed_count,
                'plants': plant_count,
                'seeds_per_plant': seeds_per_plant,
                'new_plants': new_plants,
                'unclaimed_lp': unclaimed_lp,
                'unclaimed_worth': unclaimed_worth,
                'drip_busd': drip_busd_lp
            }
        except:
            logging.debug(traceback.format_exc())
    return {}

def get_token_price(token):
    price_dict = pancakeswap_api_get_price(token)
    token_price = Decimal(price_dict["data"]["price"])
    return token_price

def save_stats(last_action, claimed, planted):
    try:
        with open('stats.log', 'w') as fp:
            fp.write('%s,%s,%s\n' %(last_action, claimed, planted))
    except:
        logging.debug(traceback.format_exc())

def load_stats():
    try:
        with open('stats.log', 'r') as fp:
            temp_lines = fp.readlines()
        stats_data = temp_lines[0].strip().split(',')
        stats_data[0] = int(stats_data[0])
        if stats_data[0] >= len(ACTION_LIST):
            stats_data[0] = 0
        stats_data[1] = int(stats_data[1])
        stats_data[2] = int(stats_data[2])
    except:
        stats_data = [0, 0, 0]
        logging.debug(traceback.format_exc())
    return stats_data

def handle_garden(client,first_run):
    global TOTAL_WORTH
    # loading previous session stats, so we know where we left off.
    action_index, claimed_counter, compound_counter = load_stats()
    # Get token price info
    dogs_price = get_token_price(DOGS_TOKEN_ADDRESS)
    pigs_price = get_token_price(PIGS_TOKEN_ADDRESS)
    drip_price = get_token_price(DRIP_TOKEN_ADDRESS)
    # Get garden info.
    garden_data = get_garden_data(client, max_tries=MAX_TRIES)
    if len(garden_data) == 0:
        time.sleep(10)
        return
    seed_count = garden_data.get('seeds', 0)
    plant_count = garden_data.get('plants', 0)
    seeds_per_plant = garden_data.get('seeds_per_plant', 0)
    new_plants = garden_data.get('new_plants', 0)
    secondsUntilNextPlant = garden_data.get('secondsUntilNextPlant',180)
    if seed_count >= seeds_per_plant:
        new_plants = seed_count // seeds_per_plant
    else:
        new_plants = 0
    unclaimed_lp = garden_data.get('unclaimed_lp', 0)
    unclaimed_worth = garden_data.get('unclaimed_worth', 0)
    TOTAL_WORTH = decimal_round(unclaimed_worth, 2)
    # Report garden stats
    logging.info('----------------')
    logging.info('Seconds to next plant: %s.' % (secondsUntilNextPlant))
    logging.info('Seeds: %s. Plants: %s.' % (seed_count, plant_count))
    logging.info('New Plants: %s/%s.' % (new_plants, MINIMUM_NEW_PLANTS))
    logging.info('Pending: %s. Value: $%s.' % (unclaimed_lp, decimal_round(unclaimed_worth, 2)))
    logging.info('Sold: %s. Compounded: %s.' % (
        claimed_counter, compound_counter))
    logging.info('Next Action: %s. Position: %s.' % (ACTION_LIST[action_index], (action_index + 1)))
    logging.info('----------------')
    logging.info('DOGS:$%s PIGS:$%s DRIP:$%s' % (
        decimal_round(dogs_price, 2), decimal_round(pigs_price, 2), decimal_round(drip_price, 2)))
    response = ""
    # Save stats before current action changes!
    save_stats(action_index, claimed_counter, compound_counter)
    # Do actions in the garden.
    if new_plants >= MINIMUM_NEW_PLANTS and not first_run:
        if ACTION_LIST[action_index] == "compound":
            action_index += 1
            logging.info('Planting seeds (compounding)...')
            response = client.plant_seeds(max_tries=MAX_TRIES)
            if response and "status" in response and response["status"] == 1:
                compound_counter += 1
                logging.info('Done!')
            else:
                logging.info('There was a problem trying to plant seeds.')
        elif ACTION_LIST[action_index] == "sell":
            action_index += 1
            logging.info('Selling seeds...')
            response = client.sell_seeds(max_tries=MAX_TRIES)
            if response and "status" in response and response["status"] == 1:
                claimed_counter += 1
                # only deposit to drip farm if setting is set in settings.py
                if DEPOSIT_TO_DRIP_FARM is True:
                    logging.info('Waiting 2 mins before depositing LP into farm...')
                    time.sleep(60 * 2)
                    logging.info('Depositing seeds...')
                    response = client.deposit_drip_lp_farm(max_tries=MAX_TRIES)
                    if response and "status" in response and response["status"] == 1:
                        logging.info('Done!')
                    else:
                        logging.info(
                            'There was a problem depositing seeds into the drip/busd farm.')
        logging.debug('response: %s' % response)
    # Save stats 1 more time to make sure we are up to date!
    save_stats(action_index, claimed_counter, compound_counter)
    return secondsUntilNextPlant

def handle_pools(client):
    global POOL_DICT, TOTAL_WORTH
    if os.path.exists("pools.log") is True:
        POOL_DICT = load_json("pools.log")
        
    if len(POOL_DICT) == 0:
        logging.info("Downloading pool information...")
        dog_pools = client.get_all_pools(pigs_or_dogs="dogs")
        pig_pools = client.get_all_pools(pigs_or_dogs="pigs")
        POOL_DICT.update(pig_pools)
        POOL_DICT.update(dog_pools)
        save_json("pools.log", POOL_DICT)
    if len(POOL_DICT) > 0:
        drip_busd_lp = client.get_drip_busd_lp_price()
        pigs_price = client.get_pigs_price()
        dogs_price = client.get_dogs_price()
        logging.info('----------------')
        for pool_id in DOGS_POOLS:
            dict_key = "%s:dogs" % pool_id
            current_pool_dict = POOL_DICT[dict_key]
            # Get reward info from pools
            reward_data = client.get_pool_user_info(pool_id, pigs_or_dogs="dogs", max_tries=MAX_TRIES)
            amount = decimal_round(Decimal(reward_data["amount"]), 4)
            if pool_id == 2:
                # drips/busd farm
                usd_price = decimal_round(drip_busd_lp["price"] * amount, 2)
                TOTAL_WORTH += usd_price
                logging.info("%s: %s ($%s). " % (
                    current_pool_dict["symbol"], amount, usd_price))
            elif pool_id == 3:
                # single stake dogs pool
                usd_price = decimal_round(dogs_price * amount, 2)
                TOTAL_WORTH += usd_price
                logging.info("%s: %s ($%s). " % (
                    current_pool_dict["symbol"], amount, usd_price))
            else:
                logging.info("%s: %s." % (
                    current_pool_dict["symbol"], amount))
        for pool_id in PIGS_POOLS:
            dict_key = "%s:pigs" % pool_id
            current_pool_dict = POOL_DICT[dict_key]
            # Get reward info from pools
            reward_data = client.get_pool_user_info(pool_id, pigs_or_dogs="pigs", max_tries=MAX_TRIES)
            amount = decimal_round(Decimal(reward_data["amount"]), 4)
            if pool_id == 0:
                # pigs in the pigpen.
                usd_price = decimal_round(pigs_price * amount, 2)
                TOTAL_WORTH += usd_price
                logging.info("%s: %s ($%s). " % (
                    current_pool_dict["symbol"], amount, usd_price))
            elif pool_id == 19:
                usd_price = decimal_round(amount, 2)
                TOTAL_WORTH += usd_price
                logging.info("%s: %s ($%s). " % (
                    current_pool_dict["symbol"], amount, usd_price))
            else:
                logging.info("%s: %s. " % (
                    current_pool_dict["symbol"], amount))
    
def save_json(filename, dict_obj):
    try:
        with open(filename, 'w') as fp:
            fp.write(json.dumps(dict_obj))
    except:
        logging.debug(traceback.format_exc())
        
def load_json(filename):
    items = {}
    try:
        with open(filename, 'r') as fp:
            items = json.loads(fp.read())
    except:
        logging.debug(traceback.format_exc())
    return items

if __name__ == "__main__":
    main()
    
