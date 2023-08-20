'''
Arbitrum:
arbitrum -> avalanche (2.5): https://arbiscan.io/tx/0x3ad0c8aa2b5675c3f6fbfde5fb6c668c95a99179db0b9f107a6068c7bfe0071b
arbitrum -> polygon (2.5): https://arbiscan.io/tx/0xad55c727e33ded6bfca74417705cebb31d307430b1da8dc8a17b02225e5a462a

Polygon:
polygon -> arbitrum (1): https://polygonscan.com/tx/0xc14084044d5abccb11647c9f6a6b2fa68df4551b828326d345bf27e77d755e38
polygon -> avalanche (1): https://polygonscan.com/tx/0x432b5592bb9bfdce14845844bd09c3bed9fc6bb54311608142ca60469e819346

Avalanche:
avalanche -> arbitrum (1): https://snowtrace.io/tx/0x0d14541440bf7731070649f9447365b61f7760b3f8895f8fa544265869a76e3c
avalanche -> polygon (1): https://snowtrace.io/tx/0x4716dcfa604b5e11cc8c930ecef8f7f0c42f05bd31d1eb1401c84fe798af9395

avalanche -> bsc (2.5 USDT): https://snowtrace.io/tx/0x47d2cfa1d89b1656c83c5548e0b5fd17cc54ea8f4674b3f02d0c324546778d53
'''

import asyncio
import random
from typing import Optional
from web3.types import TxParams
from web3.contract import AsyncContract

from tasks.base import Base
from py_eth_async.data.models import TxArgs, TokenAmount
from py_eth_async.data.models import Networks

from data.config import logger
from data.models import Contracts


class Stargate(Base):
    contract_data = {
        Networks.Arbitrum.name: {
            'usdc_contract': Contracts.ARBITRUM_USDC_e,
            'stargate_contract': Contracts.ARBITRUM_STARGATE,
            'stargate_chain_id': 110,
            'src_pool_id': 1,
            'dst_pool_id': 1,
        },
        Networks.Avalanche.name: {
            'usdc_contract': Contracts.AVALANCHE_USDC,
            'stargate_contract': Contracts.AVALANCHE_STARGATE,
            'stargate_chain_id': 106,
            'src_pool_id': 1,
            'dst_pool_id': 1,
        },
        Networks.Polygon.name: {
            'usdc_contract': Contracts.POLYGON_USDC,
            'stargate_contract': Contracts.POLYGON_STARGATE,
            'stargate_chain_id': 109,
            'src_pool_id': 1,
            'dst_pool_id': 1,
        },
        Networks.BSC.name: {
            'stargate_chain_id': 102,
            'src_pool_id': 1,
            'dst_pool_id': 2,
        }
    }

    async def send_usdc(
            self,
            to_network_name: str,
            amount: Optional[TokenAmount] = None,
            slippage: float = 0.5,
            max_fee: float = 1
    ):
        failed_text = f'Failed to send {self.client.network.name} USDC to {to_network_name} USDC via Stargate'
        # try:
        if self.client.network.name == to_network_name:
            return f'{failed_text}: The same source network and destination network'

        usdc_contract = await self.client.contracts.default_token(
            contract_address=Stargate.contract_data[self.client.network.name]['usdc_contract'].address)
        stargate_contract = await self.client.contracts.get(
            contract_address=Stargate.contract_data[self.client.network.name]['stargate_contract'])

        if not amount:
            amount = await self.client.wallet.balance(token=usdc_contract.address)

        logger.info(
            f'{self.client.account.address} | Stargate | '
            f'send USDC from {self.client.network.name} to {to_network_name} | amount: {amount.Ether}')

        lz_tx_params = TxArgs(
            dstGasForCall=0,
            dstNativeAmount=0,
            dstNativeAddr='0x0000000000000000000000000000000000000001'
        )

        args = TxArgs(
            _dstChainId=Stargate.contract_data[to_network_name]['stargate_chain_id'],
            _srcPoolId=Stargate.contract_data[to_network_name]['src_pool_id'],
            _dstPoolId=Stargate.contract_data[to_network_name]['dst_pool_id'],
            _refundAddress=self.client.account.address,
            _amountLD=amount.Wei,
            _minAmountLD=int(amount.Wei * (100 - slippage) / 100),
            _lzTxParams=lz_tx_params.tuple(),
            _to=self.client.account.address,
            _payload='0x'
        )

        value = await self.get_value(
            router_contract=stargate_contract,
            to_network_name=to_network_name,
            lz_tx_params=lz_tx_params
        )
        if not value:
            return f'{failed_text} | can not get value ({self.client.network.name})'

        native_balance = await self.client.wallet.balance()
        if native_balance.Wei < value.Wei:
            return f'{failed_text}: To low native balance: balance: {native_balance.Ether}; value: {value.Ether}'

        token_price = await self.get_token_price(token=self.client.network.coin_symbol)
        network_fee = float(value.Ether) * token_price
        if network_fee > max_fee:
            return f'{failed_text} | too high fee: {network_fee} ({self.client.network.name})'

        if await self.approve_interface(
                token_address=usdc_contract.address,
                spender=stargate_contract.address,
                amount=amount
        ):
            await asyncio.sleep(random.randint(5, 10))
        else:
            return f'{failed_text} | can not approve'

        tx_params = TxParams(
            to=stargate_contract.address,
            data=stargate_contract.encodeABI('swap', args=args.tuple()),
            value=value.Wei
        )

        tx = await self.client.transactions.sign_and_send(tx_params=tx_params)
        receipt = await tx.wait_for_receipt(client=self.client, timeout=300)
        if receipt:
            return f'{amount.Ether} USDC was send from {self.client.network.name} to {to_network_name} via Stargate: {tx.hash.hex()}'
        return f'{failed_text}!'

        # except Exception as e:
        #     return f'{failed_text}: {e}'

    async def get_value(self, router_contract: AsyncContract, to_network_name: str,
                        lz_tx_params: TxArgs) -> Optional[TokenAmount]:
        res = await router_contract.functions.quoteLayerZeroFee(
            Stargate.contract_data[to_network_name]['stargate_chain_id'],
            1,
            self.client.account.address,
            '0x',
            lz_tx_params.list()
        ).call()
        return TokenAmount(amount=res[0], wei=True)

    async def send_usdc_from_avalanche_to_usdt_bsc(
            self,
            amount: Optional[TokenAmount] = None,
            dest_fee: Optional[TokenAmount] = None,
            slippage: float = 0.5,
            max_fee: float = 1
    ):
        failed_text = 'Failed to send Avalanche USDC to BSC USDT via Stargate'
        try:
            to_network_name = Networks.BSC.name
            if self.client.network.name != Networks.Avalanche.name:
                return f'{failed_text}: This feature only works from avalanche network'

            usdc_contract = await self.client.contracts.default_token(
                contract_address=Stargate.contract_data[self.client.network.name]['usdc_contract'].address)
            stargate_contract = await self.client.contracts.get(
                contract_address=Stargate.contract_data[self.client.network.name]['stargate_contract'])

            if not amount:
                await self.client.wallet.balance(token=usdc_contract.address)

            logger.info(
                f'{self.client.account.address} | Stargate | '
                f'send USDC from {self.client.network.name} to {to_network_name} | amount: {amount.Ether}')

            lz_tx_params = TxArgs(
                dstGasForCall=0,
                dstNativeAmount=dest_fee.Wei,
                dstNativeAddr=self.client.account.address
            )

            args = TxArgs(
                _dstChainId=Stargate.contract_data[to_network_name]['stargate_chain_id'],
                _srcPoolId=Stargate.contract_data[to_network_name]['src_pool_id'],
                _dstPoolId=Stargate.contract_data[to_network_name]['dst_pool_id'],
                _refundAddress=self.client.account.address,
                _amountLD=amount.Wei,
                _minAmountLD=int(amount.Wei * (100 - slippage) / 100),
                _lzTxParams=lz_tx_params.tuple(),
                _to=self.client.account.address,
                _payload='0x'
            )
            value = await self.get_value(
                router_contract=stargate_contract,
                to_network_name=to_network_name,
                lz_tx_params=lz_tx_params
            )
            if not value:
                return f'{failed_text} | can not get value ({self.client.network.name})'

            native_balance = await self.client.wallet.balance()
            if native_balance.Wei < value.Wei:
                return f'{failed_text}: To low native balance: balance: {native_balance.Ether}; value: {value.Ether}'

            token_price = await self.get_token_price(token=self.client.network.coin_symbol)
            dest_native_token_price = await self.get_token_price(token='BNB') # костыль
            dst_native_amount_dollar = float(dest_fee.Ether) * dest_native_token_price
            network_fee = float(value.Ether) * token_price
            if network_fee - dst_native_amount_dollar > max_fee:
                return f'{failed_text} | too high fee: {network_fee - dst_native_amount_dollar} ({self.client.network.name})'

            if await self.approve_interface(
                    token_address=usdc_contract.address,
                    spender=stargate_contract.address,
                    amount=amount
            ):
                await asyncio.sleep(random.randint(5, 10))
            else:
                return f'{failed_text} | can not approve'

            tx_params = TxParams(
                to=stargate_contract.address,
                data=stargate_contract.encodeABI('swap', args=args.tuple()),
                value=value.Wei
            )

            tx = await self.client.transactions.sign_and_send(tx_params=tx_params)
            receipt = await tx.wait_for_receipt(client=self.client, timeout=300)
            if receipt:
                return f'{amount.Ether} USDC was send from {self.client.network.name} to {to_network_name} via Stargate: {tx.hash.hex()}'
            return f'{failed_text}!'

        except Exception as e:
            return f'{failed_text}: {e}'


    # todo: написать функцию поиска usdc по доступным сетям
