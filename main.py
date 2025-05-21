import logging
from flow import create_flow

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    # 获取用户输入问题
    question = input("请输入你的问题：")
    if not question:
        logging.warning("问题不能为空")
        return
    shared = {
        "question": question,
        "search_result": None,
        "answer": None
    }
    flow = create_flow()
    flow.run(shared)
    logging.info("\n【搜索结果】\n%s", shared["search_result"])
    logging.info("\n【答案】\n%s", shared["answer"])

if __name__ == "__main__":
    main() 