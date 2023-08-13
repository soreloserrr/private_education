import asyncio

from web3 import Web3
from loguru import logger

from sdk.data.models import Networks
from sdk.client import Client

from private_data import private_key1, private_key2, private_key3, proxy


async def main():
    client = Client(private_key=private_key1, network=Networks.Optimism, proxy=proxy)
    # print(await client.wallet.balance(token_address='0xaf88d065e77c8cc2239327c5edb3a432268e5831'))
    balance = await client.wallet.balance()
    balance = await client.wallet.balance()
    balance = await client.wallet.balance()

# В файле app.py написать код, который сам генерирует приватный ключ и адрес к нему и после этого проверяет баланс
# эфира в сети эфира (брутфорсим кошельки). Код должен работать асинхронно


# async def check_eth(wallets_amount: int = 50):
#     client = Client(network=Networks.Ethereum)
#     for wallet in range(wallets_amount):
#         eth_balance = await client.wallet.balance()
#         print(f'Eth balance: {eth_balance}')
#         # return f'Eth balance: {eth_balance}'

async def check_eth_balance():
    client = Client(network=Networks.Ethereum)
    wallet_balance = await client.wallet.balance()
    return wallet_balance, client.account.key


async def check_eth(wallets_amount: int = 50):
    tasks = []
    for wallet in range(wallets_amount):
        tasks.append(asyncio.create_task(check_eth_balance()))
    await asyncio.wait([*tasks])
    for task in tasks:
        balance, key = task.result()
        logger.success(f'Eth balance: {balance.Ether, key}')


'''
token_address = Web3.to_checksum_address('0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')

tasks = []
for private_key in [private_key1, private_key2, private_key3]:
    client = Client(private_key=private_key, network=Networks.Arbitrum)
    tasks.append(asyncio.create_task(client.wallet.balance(token_address=token_address)))

await asyncio.gather(*tasks)
await asyncio.wait([*tasks])

for task in tasks:
    print(task.result())
'''
'''
asyncio.gather() принимает список асинхронных задач (coroutines) в качестве аргументов и запускает их одновременно.
Она возвращает список результатов, соответствующих выполненным задачам в том же порядке, в котором задачи были переданы в функцию.
Если во время выполнения задачи возникает исключение, asyncio.gather() прекращает выполнение остальных задач и сразу же выбрасывает исключение.

asyncio.wait() принимает список асинхронных задач (coroutines) в качестве аргументов и запускает их одновременно.
Она возвращает кортеж из двух множеств: множество выполненных задач и множество невыполненных задач.
Если во время выполнения задачи возникает исключение, asyncio.wait() продолжает выполнение остальных задач и не выбрасывает исключение.
'''


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.run_until_complete(check_eth())


