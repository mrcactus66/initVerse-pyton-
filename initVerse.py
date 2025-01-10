import time
from web3 import Web3

# 配置网络
rpc_url = "https://rpc-testnet.inichain.com"  # Genesis Testnet RPC URL
web3 = Web3(Web3.HTTPProvider(rpc_url))

# 检查是否成功连接
if not web3.is_connected():
    print("无法连接到网络，请检查连接。")
    input("按任意键退出...")  # 等待用户查看错误信息
    exit()

# 获取私钥
Private_key_Wallet_2 = '替换为钱包私钥'

# 创建签名钱包对象
PA = web3.eth.account.from_key(Private_key_Wallet_2)

# 获取钱包的公共地址
Public_Address = PA.address
print(f"钱包公共地址: {Public_Address}")

# 设置代币合约 ABI（确保 ABI 配置格式正确）
token_abi = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# 设置 DEX 合约 ABI（请根据你的合约修改 ABI）
dex_abi = [
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# 代币地址
ini_token_address = "0xfbECae21C91446f9c7b87E4e5869926998f99ffe"  # 替换为实际 WINI 代币地址
usdt_token_address = "0xcF259Bca0315C6D32e877793B6a10e97e7647FdE"  # 替换为实际 USDT 代币地址
dex_contract_address = "0x4ccB784744969D9B63C15cF07E622DDA65A88Ee7"  # 替换为实际 DEX 合约地址

# 创建代币合约实例
ini_token_contract = web3.eth.contract(address=ini_token_address, abi=token_abi)
usdt_token_contract = web3.eth.contract(address=usdt_token_address, abi=token_abi)

# 创建 DEX 合约实例
dex_contract = web3.eth.contract(address=dex_contract_address, abi=dex_abi)

# 获取用户余额并打印
def get_balances():
    try:
        ini_balance = ini_token_contract.functions.balanceOf(Public_Address).call()
        usdt_balance = usdt_token_contract.functions.balanceOf(Public_Address).call()

        print(f"INI 余额: {web3.from_wei(ini_balance, 'ether')} INI")
        print(f"USDT 余额: {web3.from_wei(usdt_balance, 'ether')} USDT")
        return ini_balance, usdt_balance
    except Exception as e:
        print(f"获取余额时出错: {e}")
        input("按任意键退出...")  # 错误发生时，暂停程序，等待查看错误信息
        return 0, 0

# 获取当前区块的 Gas 价格并稍微增加它
def get_optimal_gas_price():
    try:
        # 获取当前区块的 gas 价格
        gas_price = web3.eth.gas_price
        print(f"当前 Gas 价格: {web3.from_wei(gas_price, 'gwei')} gwei")
        
        # 提高 gas 价格以加速交易（增加 200%）
        optimal_gas_price = int(gas_price * 2.00)  # 提高 200%
        print(f"优化后的 Gas 价格: {web3.from_wei(optimal_gas_price, 'gwei')} gwei")
        
        return optimal_gas_price
    except Exception as e:
        print(f"获取优化 Gas 价格失败: {e}")
        return web3.to_wei('10', 'gwei')  # 默认返回 10gwei

# 执行交易
def swap_tokens(amount_in, path, to_address):
    try:
        gas_price = get_optimal_gas_price()

        # 批准 DEX 合约使用代币
        print(f"批准 DEX 合约使用 {path[0]} 代币...")
        approve_tx = ini_token_contract.functions.approve(dex_contract_address, amount_in).build_transaction({
            'from': Public_Address,
            'gas': 200000,
            'gasPrice': gas_price,
            'nonce': web3.eth.get_transaction_count(Public_Address),
        })
        signed_approve_tx = web3.eth.account.sign_transaction(approve_tx, private_key=Private_key_Wallet_2)
        tx_hash_approve = web3.eth.send_raw_transaction(signed_approve_tx.raw_transaction)
        print(f"批准交易已发送，交易哈希: {tx_hash_approve.hex()}")

        # 等待交易被确认
        print("等待批准交易被矿工确认...")
        web3.eth.wait_for_transaction_receipt(tx_hash_approve)
        print("批准交易已确认。")

        # 执行交换
        print(f"执行 {path[0]} -> {path[1]} 交换...")
        swap_tx = dex_contract.functions.swapExactTokensForTokens(
            amount_in,
            0,  # 最小输出设为 0
            path,
            to_address,
            int(web3.eth.get_block('latest')['timestamp']) + 60  # 设置 60 秒后的截止时间
        ).build_transaction({
            'from': Public_Address,
            'gas': 200000,
            'gasPrice': gas_price,
            'nonce': web3.eth.get_transaction_count(Public_Address),
        })
        signed_swap_tx = web3.eth.account.sign_transaction(swap_tx, private_key=Private_key_Wallet_2)
        tx_hash_swap = web3.eth.send_raw_transaction(signed_swap_tx.raw_transaction)
        print(f"交换交易已发送，交易哈希: {tx_hash_swap.hex()}")

        # 等待交易被确认
        print("等待交换交易被矿工确认...")
        web3.eth.wait_for_transaction_receipt(tx_hash_swap)
        print(f"{path[0]} -> {path[1]} 交换已确认。")
    except Exception as e:
        print(f"交换操作失败: {e}")
        input("按任意键退出...")  # 错误发生时，暂停程序，等待查看错误信息

# 主循环，每次检查余额后执行交换
loop_count = 0
while True:
    print("\n检查余额并尝试交换...\n")
    
    # 获取当前余额
    ini_balance, usdt_balance = get_balances()

    # 判断 INI 余额不足时，直接将 USDT 兑换回 INI
    if web3.from_wei(ini_balance, 'ether') < 0.01:
        if usdt_balance > 0:
            print("INI余额不足，开始执行 USDT -> INI 兑换...")
            swap_tokens(web3.to_wei(0.01, 'ether'), [usdt_token_address, ini_token_address], Public_Address)
        else:
            print("USDT余额不足，无法进行兑换。")
            break  # 结束循环

    # 如果 USDT 余额大于 0，则执行 INI -> USDT 交换
    elif usdt_balance > 0:
        print("INI 余额充足，开始执行 INI -> USDT 兑换...")
        swap_tokens(web3.to_wei(0.01, 'ether'), [ini_token_address, usdt_token_address], Public_Address)
    
    # 输出当前的余额和循环次数
    loop_count += 1
    print(f"\n循环次数: {loop_count}")
    
    # 计算并输出下一次循环倒计时
    countdown = 600  # 每次循环等待10分钟
    print(f"等待 {countdown} 秒后继续...")
    time.sleep(countdown)
