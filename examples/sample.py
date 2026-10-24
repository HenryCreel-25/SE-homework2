"""示例代码：用于演示代码解释 Agent 的功能。"""


def calculate_total(prices: list[float], discount: float = 0.0) -> float:
    """计算总价，可叠加折扣（折扣为 0~1 之间的小数）。"""
    if discount < 0 or discount > 1:
        raise ValueError("折扣必须在 0 到 1 之间")
    subtotal = sum(prices)
    return round(subtotal * (1 - discount), 2)


if __name__ == "__main__":
    items = [12.5, 30.0, 8.75]
    print("总价：", calculate_total(items, discount=0.1))
