import os
from openai import OpenAI
from utils.config import config

# 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中
# 初始化Ark客户端，从环境变量中读取您的API Key
client = OpenAI(
    # 此为默认路径，您可根据业务所在地域进行配置
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    # 从环境变量中获取您的 API Key。此为默认方式，您可根据需要进行修改
    api_key=os.environ.get("ARK_API_KEY"),
)

# 使用配置管理模块获取 API key
api_key = config.get_env("ARK_API_KEY")

response = client.images.generate(
    # 指定您创建的方舟推理接入点 ID，此处已帮您修改为您的推理接入点 ID
    model="ep-20250522174711-h9n5l",
    prompt="一只大熊猫在跳舞",
    size="1024x1024",
    response_format="url"        
)
print(response.data[0].url)