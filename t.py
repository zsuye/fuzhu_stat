import tiktoken

def analyze_text(text):
    encoder = tiktoken.encoding_for_model("gpt-4")
    tokens = encoder.encode(text)
    
    print(f"文本: {text}")
    print(f"字符数: {len(text)}")
    print(f"Token数: {len(tokens)}")
    print("Token详情:")
    for token in tokens:
        print(f"Token ID: {token}, Text: {repr(encoder.decode([token]))}")
    print("-" * 50)

# 测试各种情况
texts = [
    "人工智能",      # 普通中文词组
    "GPT-3",        # 英文数字混合
    "编程",          # 常见中文词组
    "你好世界",      # 常见短语
    "OpenAI",       # 英文专有名词
    "中国",          # 国家名称
    "人工智能是未来", # 较长句子
]

for text in texts:
    analyze_text(text)
